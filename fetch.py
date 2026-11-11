#!/usr/bin/env python3
"""
SGE (上海黄金交易所) + 国际贵金属 + 汇率 抓取器 —— 零依赖（仅 Python 标准库）。

数据源：
  - 上海黄金交易所官方行情：GET https://www.sge.com.cn/graph/quotations?instid=<合约>
  - 国际现货报价（gold-api.com）：XAU 黄金 / XAG 白银 / XPT 铂金
  - 美元兑人民币 USD/CNY：GET https://open.er-api.com/v6/latest/USD

产出 data.json，包含：
  - items[]      SGE 各合约（现货 + 延期 + 100g，最新/今开/最高/最低/单位/分时序列）
  - primary      主力合约（Au99.99）分时
  - intl{}       汇率 + 黄金/白银/铂金各自的国际报价、人民币折算价与国内溢价
                 （顶层 xau_usd / usd_cny / intl_cny_per_g / premium_pct 为黄金兼容字段）

特性：
  - 请求间退避，避免触发反爬 403
  - 各上游独立容错：任一失败回退到种子/上次缓存，保证整站不空白
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

# (中文品种, 合约代码, 计价单位) —— 现货 → 100g/延期 → 白银 → 铂钯
SYMBOLS = [
    ("黄金",       "Au99.99",  "元/克"),
    ("黄金",       "Au99.95",  "元/克"),
    ("黄金100g",   "Au100g",   "元/克"),
    ("国际板金",   "iAu99.99", "元/克"),
    ("黄金延期",   "Au(T+D)",  "元/克"),
    ("迷你金延期", "mAu(T+D)", "元/克"),
    ("白银",       "Ag99.99",  "元/千克"),
    ("白银延期",   "Ag(T+D)",  "元/千克"),
    ("铂金",       "Pt99.95",  "元/克"),
    ("钯金",       "Pd99.95",  "元/克"),
]
PRIMARY = "Au99.99"

# 国际贵金属上游（gold-api.com）
METAL_API = "https://api.gold-api.com/price/{sym}"
FX_URL = "https://open.er-api.com/v6/latest/USD"

# 能源上游（新浪财经，国内可达）
SINA_DAILY = ("https://stock2.finance.sina.com.cn/futures/api/jsonp.php/var%20_S="
              "/GlobalFuturesService.getGlobalFuturesDailyKLine?symbol={sym}")
SINA_HQ = "https://hq.sinajs.cn/list=nf_{code}"
SINA_HEADERS = {
    "User-Agent": HEADERS["User-Agent"],
    "Referer": "https://finance.sina.com.cn/",
    "Accept": "*/*",
}

# 汇率表币种（code, 名称, 展示单位倍数）
FX_SYMBOLS = [
    ("USD", "美元", 1), ("EUR", "欧元", 1), ("JPY", "日元", 100), ("GBP", "英镑", 1),
    ("HKD", "港币", 1), ("KRW", "韩元", 100), ("AUD", "澳元", 1), ("SGD", "新加坡元", 1),
    ("CHF", "瑞士法郎", 1), ("CAD", "加元", 1), ("THB", "泰铢", 100),
]

# 能源种子兜底（2026-11-11 实测）
OIL_SEED = {
    "brent": {"close": 92.47, "prev": 91.96},
    "wti": {"close": 86.66, "prev": 86.43},
    "sc": {"last": 594.3, "prev_settle": 599.3},
}

# 种子兜底（真实采集参考值，仅展示占位；2026-11-11 实测）
SEED = {
    "xau_usd": 4048.0, "xag_usd": 51.67, "xpt_usd": 1559.0, "xpd_usd": 1056.0, "usd_cny": 6.6878,
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


def _fetch_metal(sym):
    """gold-api.com 单金属报价（美元/金衡盎司）。失败返回 None。"""
    try:
        j = _get_json(METAL_API.format(sym=sym), timeout=15,
                      headers={"User-Agent": HEADERS["User-Agent"]})
        if isinstance(j, dict) and j.get("price"):
            return float(j["price"])
    except Exception as e:
        print(f"[warn] 国际 {sym} 抓取失败: {e}", file=sys.stderr)
    return None


def _fetch_fx():
    """返回 (usd_cny, 全币种 rates)；失败回退种子。"""
    try:
        j = _get_json(FX_URL, timeout=15)
        if isinstance(j, dict) and j.get("result") == "success":
            return float(j["rates"]["CNY"]), j.get("rates") or {}
    except Exception as e:
        print(f"[warn] USD/CNY 抓取失败: {e}", file=sys.stderr)
    return SEED["usd_cny"], {}


def _get_text(url, timeout=15, headers=None, encoding="utf-8"):
    req = urllib.request.Request(url, headers=headers or HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode(encoding, errors="replace")


def _sina_daily(sym):
    raw = _get_text(SINA_DAILY.format(sym=sym), headers=SINA_HEADERS)
    i, j = raw.find("("), raw.rfind(")")
    arr = json.loads(raw[i + 1:j])
    if not isinstance(arr, list) or not arr:
        raise RuntimeError("空K线")
    return arr


def fetch_oil():
    """布伦特 / WTI（新浪全球期货日线收盘）+ 上海原油 SC（INE 主力连续实时）。"""
    out = {}
    for key, sym, name in (("brent", "OIL", "布伦特原油"), ("wti", "CL", "WTI原油")):
        try:
            arr = _sina_daily(sym)
            last = arr[-1]
            prev = float(arr[-2]["close"]) if len(arr) > 1 else None
            out[key] = {"name": name, "symbol": sym, "unit": "美元/桶",
                        "last": float(last["close"]), "open": float(last["open"]),
                        "high": float(last["high"]), "low": float(last["low"]),
                        "date": last.get("date", ""), "prev_close": prev}
        except Exception as e:
            print(f"[warn] 油价 {key} 抓取失败: {e}", file=sys.stderr)
            s = OIL_SEED.get(key, {})
            out[key] = {"name": name, "symbol": sym, "unit": "美元/桶",
                        "last": s.get("close"), "prev_close": s.get("prev")}
    try:
        raw = _get_text(SINA_HQ.format(code="SC0"), headers=SINA_HEADERS, encoding="gbk")
        f = raw[raw.index('"') + 1:raw.rindex('"')].split(",")
        out["sc"] = {"name": "上海原油", "symbol": "SC", "unit": "元/桶",
                     "last": float(f[8]), "open": float(f[2]), "high": float(f[3]),
                     "low": float(f[4]), "prev_settle": float(f[10]), "date": f[17]}
    except Exception as e:
        print(f"[warn] 油价 sc 抓取失败: {e}", file=sys.stderr)
        s = OIL_SEED["sc"]
        out["sc"] = {"name": "上海原油", "symbol": "SC", "unit": "元/桶",
                     "last": s["last"], "prev_settle": s["prev_settle"]}
    return out


def build_fx_table(usd_cny, rates):
    """主流币种兑人民币（rates 为 1 美元兑各币种）。"""
    out = []
    for code, name, mult in FX_SYMBOLS:
        r = rates.get(code)
        if not r:
            continue
        r = float(r)
        out.append({
            "code": code, "name": name, "unit": mult,
            "cny": round(usd_cny / r * mult, 4),          # 1（或 100）外币 = X 人民币
            "per_cny": round(r / usd_cny, 6 if mult == 1 else 4),  # 1 人民币 = Y 外币
        })
    return out


def _premium(sge, intl_cny):
    if sge and intl_cny:
        return round((float(sge) - float(intl_cny)) / float(intl_cny) * 100, 2)
    return None


def fetch_intl(by_symbol):
    """国际贵金属（金/银/铂）+ 汇率 + 各品种国内溢价。各上游独立回退到种子。"""
    xau = _fetch_metal("XAU")
    xag = _fetch_metal("XAG")
    xpt = _fetch_metal("XPT")
    xpd = _fetch_metal("XPD")
    fx, fx_rates = _fetch_fx()

    if xau is None: xau = SEED["xau_usd"]
    if xag is None: xag = SEED["xag_usd"]
    if xpt is None: xpt = SEED["xpt_usd"]
    if xpd is None: xpd = SEED["xpd_usd"]
    if fx is None: fx = SEED["usd_cny"]

    g = GRAMS_PER_OZ
    gold_sge = by_symbol.get("Au99.99", {}).get("last")
    silver_sge = by_symbol.get("Ag99.99", {}).get("last")   # 元/千克
    plat_sge = by_symbol.get("Pt99.95", {}).get("last")
    pall_sge = by_symbol.get("Pd99.95", {}).get("last")

    gold_cny = round(xau * fx / g, 2)                 # 元/克
    silver_cny_kg = round(xag * fx / g * 1000, 2)     # 元/千克
    plat_cny = round(xpt * fx / g, 2)                 # 元/克
    pall_cny = round(xpd * fx / g, 2)                 # 元/克

    metals = {
        "gold": {
            "name": "黄金", "sge_symbol": "Au99.99", "intl_symbol": "XAU/USD",
            "unit": "元/克", "intl_usd": round(xau, 2), "intl_cny": gold_cny,
            "sge": round(float(gold_sge), 2) if gold_sge else None,
            "premium_pct": _premium(gold_sge, gold_cny),
        },
        "silver": {
            "name": "白银", "sge_symbol": "Ag99.99", "intl_symbol": "XAG/USD",
            "unit": "元/千克", "intl_usd": round(xag, 2), "intl_cny": silver_cny_kg,
            "sge": round(float(silver_sge), 2) if silver_sge else None,
            "premium_pct": _premium(silver_sge, silver_cny_kg),
        },
        "platinum": {
            "name": "铂金", "sge_symbol": "Pt99.95", "intl_symbol": "XPT/USD",
            "unit": "元/克", "intl_usd": round(xpt, 2), "intl_cny": plat_cny,
            "sge": round(float(plat_sge), 2) if plat_sge else None,
            "premium_pct": _premium(plat_sge, plat_cny),
        },
        "palladium": {
            "name": "钯金", "sge_symbol": "Pd99.95", "intl_symbol": "XPD/USD",
            "unit": "元/克", "intl_usd": round(xpd, 2), "intl_cny": pall_cny,
            "sge": round(float(pall_sge), 2) if pall_sge else None,
            "premium_pct": _premium(pall_sge, pall_cny),
        },
    }

    return {
        # 黄金兼容字段（首页 Hero / 概览直接使用）
        "xau_usd": round(xau, 2),
        "usd_cny": round(fx, 4),
        "intl_cny_per_g": gold_cny,
        "sge_cny_per_g": round(float(gold_sge), 2) if gold_sge else None,
        "premium_pct": metals["gold"]["premium_pct"],
        # 多品种明细
        "metals": metals,
    }, fx_rates


def main():
    items, primary, by_symbol = fetch_sge_all()
    intl, fx_rates = fetch_intl(by_symbol)
    oil = fetch_oil()
    fx_table = build_fx_table(float(intl["usd_cny"]), fx_rates)

    if not items:
        print("[error] SGE 全部抓取失败，保留原缓存。", file=sys.stderr)
        sys.exit(0)

    payload = {
        "generated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "source": "上海黄金交易所 (SGE) · 国际现货贵金属 · 美元兑人民币 · 新浪财经",
        "live": len([1 for _ in items]),
        "items": items,
        "primary": primary,
        "intl": intl,
        "oil": oil,
        "fx": fx_table,
    }
    with open(CACHE, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    gold = intl["metals"]["gold"]
    print(f"[ok] 已更新 {len(items)} 个合约 | 国际XAU={intl['xau_usd']} XAG={intl['metals']['silver']['intl_usd']} "
          f"XPT={intl['metals']['platinum']['intl_usd']} | USD/CNY={intl['usd_cny']} | "
          f"溢价 金={gold['premium_pct']}% 银={intl['metals']['silver']['premium_pct']}% "
          f"铂={intl['metals']['platinum']['premium_pct']}% | "
          f"油价 布伦特={oil.get('brent', {}).get('last')} WTI={oil.get('wti', {}).get('last')} "
          f"SC={oil.get('sc', {}).get('last')} | 汇率 {len(fx_table)} 币种")


if __name__ == "__main__":
    main()
