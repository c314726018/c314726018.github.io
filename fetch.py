#!/usr/bin/env python3
"""
SGE (上海黄金交易所) 实时行情抓取器 —— 零依赖（仅 Python 标准库）。

数据源：上海黄金交易所官方行情接口
  GET https://www.sge.com.cn/graph/quotations?instid=<合约代码>
返回 JSON：{ times:[...], data:["883.0",...], min, max, heyue, now, delaystr }

特性：
  - 请求间退避，避免触发反爬 403
  - 命中 403/网络异常时回退到本地 data.json 缓存，保证整站不空白
  - 对返回 -2.0（无报价/非交易日）的合约自动跳过

仅做「行情展示」，不提供任何投资建议。
"""
import urllib.request
import urllib.parse
import json
import time
import os
import sys
import datetime

BASE = "https://www.sge.com.cn/graph/quotations"
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
PRIMARY = "Au99.99"  # 用于走势图的主力合约

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "data.json")


def _fetch_one(symbol, timeout=15):
    url = f"{BASE}?instid={urllib.parse.quote(symbol)}"
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        if r.status != 200:
            raise RuntimeError(f"HTTP {r.status}")
        return json.loads(r.read().decode("utf-8"))


def _clean_floats(seq):
    """把 data 字符串列表转成浮点，过滤掉空值与 -2.0 占位符。"""
    out = []
    for x in seq or []:
        if x in (None, "", "-2.0", -2.0):
            continue
        try:
            out.append(float(x))
        except (TypeError, ValueError):
            continue
    return out


def fetch_all():
    results = []
    by_symbol = {}
    primary = None

    # 载入历史缓存作为兜底
    cached = {}
    if os.path.exists(CACHE):
        try:
            cached = {e["symbol"]: e for e in json.load(open(CACHE, encoding="utf-8")).get("items", [])}
        except Exception:
            cached = {}

    for label, sym, unit in SYMBOLS:
        try:
            d = _fetch_one(sym)
            series = _clean_floats(d.get("data"))
            if not series:
                # 无报价（非交易时段/合约休市）—— 用缓存兜底
                if sym in cached:
                    results.append(cached[sym]); by_symbol[sym] = cached[sym]
                continue
            entry = {
                "label": label,
                "symbol": sym,
                "unit": unit,
                "last": series[-1],
                "open": series[0],
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
            print(f"[warn] {sym} 抓取失败: {e}", file=sys.stderr)
            if sym in cached:
                results.append(cached[sym]); by_symbol[sym] = cached[sym]
        time.sleep(1.2)  # 礼貌退避

    return results, primary


def main():
    items, primary = fetch_all()
    if not items:
        print("[error] 本次全部抓取失败，保留原缓存。", file=sys.stderr)
        sys.exit(0)
    payload = {
        "generated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "source": "上海黄金交易所 (SGE)",
        "items": items,
        "primary": primary,
    }
    with open(CACHE, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"[ok] 已更新 {len(items)} 个合约，主图={primary['symbol'] if primary else '无'}")


if __name__ == "__main__":
    main()
