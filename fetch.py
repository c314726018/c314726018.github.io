#!/usr/bin/env python3
"""
SGE (上海黄金交易所) + 国际金价 + 汇率 抓取器 —— 零依赖（仅 Python 标准库）。

数据源：
  - 上海黄金交易所官方行情：GET https://www.sge.com.cn/graph/quotations?instid=<合约>
  - 国际现货黄金 XAU/USD：GET https://api.gold-api.com/price/XAU
  - 美元兑人民币 USD/CNY：GET https://open.er-api.com/v6/latest/USD

产出 data.json，包含：
  - items[]      SGE 各合约（最新/今开/最高/最低/单位/分时序列）
  - primary      主力合约（Au99.99）分时
  - intl{}       国际金价、汇率、国内溢价（SGE 与 国际折算 的价差%）

特性：
  - 请求间退避，避免触发反爬 403
  - 任一上游失败自动回退到种子/上次缓存，保证整站不空白
  - 对返回 -2.0（无报价/非交易日）的合约自动跳过

仅做「行情展示」，不提供任何投资建议。
"""
import urllib.request
import urllib.parse
import urllib.error
import json
import time
import os
import sys
import datetime

SGE_BASE = "https://www.sge.com.cn/graph/quotations"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0 Safari/537.36",
    "Referer": "https://www.sge.com.cn/sjzx/mrhq",
    "Accept": "application/json, text/plain, */*",
}

# (中文品种, 合约代码, 计价单位)
SYMBOLS = [
    ("黄金",   "Au99.99",  "元/克"),
    ("黄金",   "Au99.95",  "元/克"),
    ("国际板金", "iAu99.99", "元/克"),
    ("白银",   "Ag99.99",  "元/千克"),
    ("铂金",   "Pt99.95",  "元/克"),
    ("钯金",   "Pd99.95",  "元/克"),
]
PRIMARY = "Au99.99"

# 国际金价 / 汇率 上游
XAU_URL = "https://api.gold-api.com/price/XAU"
FX_URL = "https://open.er-api.com/v6/latest/USD"

# 种子兜底（真实采集参考值，仅展示占位）
SEED = {
    "xau_usd": 2650.0,
    "usd_cny": 7.18,
    "items": {
        "Au99.99": 883.0, "Au99.95": 881.0, "iAu99.99": 884.01,
        "Ag99.99": 12760.0, "Pt99.95": 389.59, "Pd99.95": 280.0,
    },
}

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "data.json")
GRAMS_PER_OZ = 31.1034768  # 1 金衡盎司 = 31.1034768 克


def _get_json(url, timeout=15, headers=None):
    req = urllib.request.Request(url, headers=headers or HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        if r.status != 200:
            raise RuntimeError(f"HTTP {r.status}")
        return json.loads(r.read().decode("utf-8"))


def _fetch_sge(symbol, timeout=15):
    url = f"{SGE_BASE}?instid={urllib.parse.quote(symbol)}"
    return _get_json(url, timeout=timeout)


def _clean_floats(seq):
    out = []
    for x in seq or []:
        if x in (None, "", "-2.0", -2.0):
            continue
        try:
            out.append(float(x))
        except (TypeError, ValueError):
            continue
    return out


def fetch_sge_all():
    results = []
    by_symbol = {}
    primary = None
    for label, sym, unit in SYMBOLS:
        try:
            d = _fetch_sge(sym)
            series = _clean_floats(d.get("data"))
            if not series:
                continue
            entry = {
                "label": label, "symbol": sym, "unit": unit,
                "last": series[-1], "open": series[0],
                "min": float(d["min"]) if d.get("min") not in (None, "") else min(series),
                "max": float(d["max"]) if d.get("max") not in (None, "") else max(series),
                "update": d.get("delaystr") or d.get("now") or "",
                "time": d.get("times") or [],
                "series": series,
            }
            results.append(entry)
            by_symbol[sym] = entry
            if sym == PRIMARY:
                primary = {"times": d.get("times") or [], "series": series,
                           "update": entry["update"], "symbol": sym}
        except Exception as e:
            print(f"[warn] SGE {sym} 抓取失败: {e}", file=sys.stderr)
        time.sleep(1.2)
    return results, primary, by_symbol


def fetch_intl():
    """国际金价 + 汇率 + 国内溢价。失败则用种子。"""
    xau = None
    fx = None
    try:
        j = _get_json(XAU_URL, timeout=15, headers={"User-Agent": HEADERS["User-Agent"]})
        if isinstance(j, dict) and j.get("price"):
            xau = float(j["price"])
    except Exception as e:
        print(f"[warn] XAU/USD 抓取失败: {e}", file=sys.stderr)
    try:
        j = _get_json(FX_URL, timeout=15)
        if isinstance(j, dict) and j.get("result") == "success":
            fx = float(j.get("rates", {}).get("CNY"))
    except Exception as e:
        print(f"[warn] USD/CNY 抓取失败: {e}", file=sys.stderr)

    if xau is None:
        xau = SEED["xau_usd"]
    if fx is None:
        fx = SEED["usd_cny"]

    intl_cny_per_g = xau * fx / GRAMS_PER_OZ
    return {
        "xau_usd": round(xau, 2),
        "usd_cny": round(fx, 4),
        "intl_cny_per_g": round(intl_cny_per_g, 2),
        "sge_cny_per_g": None,   # 下方填充
        "premium_pct": None,     # 下方填充
    }


def compute_premium(intl, by_symbol):
    sge = by_symbol.get(PRIMARY, {}).get("last")
    if sge and intl.get("intl_cny_per_g"):
        intl["sge_cny_per_g"] = round(float(sge), 2)
        prem = (float(sge) - intl["intl_cny_per_g"]) / intl["intl_cny_per_g"] * 100
        intl["premium_pct"] = round(prem, 2)
    return intl


def main():
    items, primary, by_symbol = fetch_sge_all()
    intl = fetch_intl()
    intl = compute_premium(intl, by_symbol)

    if not items:
        print("[error] SGE 全部抓取失败，保留原缓存。", file=sys.stderr)
        sys.exit(0)

    payload = {
        "generated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "source": "上海黄金交易所 (SGE) · 国际现货黄金 · 美元兑人民币",
        "live": len([1 for _ in items]),
        "items": items,
        "primary": primary,
        "intl": intl,
    }
    with open(CACHE, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"[ok] 已更新 {len(items)} 个合约 | 国际XAU={intl['xau_usd']} | "
          f"USD/CNY={intl['usd_cny']} | 国内溢价={intl['premium_pct']}%")


if __name__ == "__main__":
    main()
