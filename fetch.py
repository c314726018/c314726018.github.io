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
import re
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
                        "date": last.get("date", ""), "prev_close": prev,
                        # 近 30 日收盘线(供前端画走势图)
                        "hist": [float(x["close"]) for x in arr[-30:]]}
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


# ---------------- 新浪批量行情(股指/国内期货/国际贵金属/美元指数) ----------------
# 实测格式(2026-11-11):
#   sh000001:  f0名称 f1开 f2昨收 f3最新 f4高 f5低 f30日期 f31时间
#   int_*:     f0名称 f1最新 f2涨跌额 f3涨跌幅%
#   nf_AU0:    f0名称 f2开 f3高 f4低 f8最新 f10昨结 f16品种 f17日期
#   hf_XAU:    f0现价 f4高 f5低 f6时间 f7昨收 f8开 f13名称
#   DINIW:     f1现价 f3昨收 f5开 f6高 f7低 f9名称 f10日期
#   fx_susdcny: f3昨收 f8现价 f9名称 f10涨跌额
SINA_BATCH = ("https://hq.sinajs.cn/list="
              "sh000001,sz399001,sz399006,int_hangseng,int_dji,int_nasdaq,int_sp500,"
              "nf_AU0,nf_AG0,nf_CU0,nf_RB0,nf_SC0,nf_AL0,nf_ZN0,nf_NI0,nf_SN0,"
              "nf_M0,nf_I0,nf_C0,nf_CF0,"
              "hf_XAU,hf_XAG,hf_GC,hf_SI,hf_OIL,hf_CL,DINIW")


def _f(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def fetch_extra():
    """新浪批量接口 → {indices, futures, intl, dxy}。失败返回空 dict(页面降级)。"""
    out = {"indices": [], "futures": [], "intl": [], "dxy": None}
    try:
        raw = _get_text(SINA_BATCH, headers=SINA_HEADERS, encoding="gbk")
    except Exception as e:
        print(f"[warn] 新浪批量行情失败: {e}", file=sys.stderr)
        return out
    data = {}
    for m in re.finditer(r'hq_str_(\w+)="([^"]*)"', raw):
        data[m.group(1)] = m.group(2).split(",")

    # 股指(A股:完整字段)
    for code in ("sh000001", "sz399001", "sz399006"):
        f = data.get(code) or []
        if len(f) < 6 or not f[0]:
            continue
        out["indices"].append({
            "code": code, "name": f[0], "last": _f(f[3]), "prev": _f(f[2]),
            "open": _f(f[1]), "high": _f(f[4]), "low": _f(f[5]),
            "date": (f[30] if len(f) > 30 else ""), "unit": "点"})
    # 全球指数(int_ 极简:名称,最新,涨跌额,涨跌幅)
    for code, unit in (("int_hangseng", "点"), ("int_dji", "点"),
                       ("int_nasdaq", "点"), ("int_sp500", "点")):
        f = data.get(code) or []
        if len(f) < 4 or not f[0]:
            continue
        out["indices"].append({
            "code": code, "name": f[0], "last": _f(f[1]), "chg": _f(f[2]),
            "pct": _f(f[3]), "unit": unit})

    # 国内期货主力(nf_ 大写+0)
    for code, name, unit in (("nf_AU0", "沪金主力", "元/克"), ("nf_AG0", "沪银主力", "元/千克"),
                             ("nf_CU0", "沪铜主力", "元/吨"), ("nf_AL0", "沪铝主力", "元/吨"),
                             ("nf_ZN0", "沪锌主力", "元/吨"), ("nf_NI0", "沪镍主力", "元/吨"),
                             ("nf_SN0", "沪锡主力", "元/吨"), ("nf_RB0", "螺纹钢主力", "元/吨"),
                             ("nf_SC0", "上海原油", "元/桶"), ("nf_M0", "豆粕主力", "元/吨"),
                             ("nf_I0", "铁矿石主力", "元/吨"), ("nf_C0", "玉米主力", "元/吨"),
                             ("nf_CF0", "棉花主力", "元/吨")):
        f = data.get(code) or []
        if len(f) < 11 or not f[0]:
            continue
        out["futures"].append({
            "code": code, "name": name, "last": _f(f[8]), "prev": _f(f[10]),
            "open": _f(f[2]), "high": _f(f[3]), "low": _f(f[4]),
            "unit": unit, "date": (f[17] if len(f) > 17 else "")})

    # 国际现货/期货(hf_ 格式)
    for code, name, unit in (("hf_XAU", "伦敦金", "美元/盎司"), ("hf_XAG", "伦敦银", "美元/盎司"),
                             ("hf_GC", "COMEX黄金", "美元/盎司"), ("hf_SI", "COMEX白银", "美元/盎司"),
                             ("hf_OIL", "布伦特原油", "美元/桶"), ("hf_CL", "WTI原油", "美元/桶")):
        f = data.get(code) or []
        if len(f) < 9 or not f[0]:
            continue
        out["intl"].append({
            "code": code, "name": name, "last": _f(f[0]), "prev": _f(f[7]),
            "open": _f(f[8]), "high": _f(f[4]), "low": _f(f[5]),
            "unit": unit, "date": (f[13] if len(f) > 13 and not f[13].isdigit() else (f[12] if len(f) > 12 else ""))})

    # 美元指数
    f = data.get("DINIW") or []
    if len(f) > 9 and f[9]:
        out["dxy"] = {"code": "DINIW", "name": "美元指数", "last": _f(f[1]), "prev": _f(f[3]),
                      "open": _f(f[5]), "high": _f(f[6]), "low": _f(f[7]),
                      "unit": "点", "date": (f[10] if len(f) > 10 else "")}
    return out


SINA_INNER = ("https://stock2.finance.sina.com.cn/futures/api/jsonp.php/var%20_I="
              "/InnerFuturesNewService.getDailyKLine?symbol={sym}")


def fetch_klines():
    """日 K OHLC(最近 60 根,真实历史):
    AU0 沪金主力 / AG0 沪银主力 / SC0 上海原油(InnerFutures,d/o/h/l/c)
    XAU 伦敦金 / GC COMEX金 / SI COMEX银 / OIL 布伦特 / CL WTI(GlobalFutures)各 120 根"""
    out = {}

    def norm(x):
        if "o" in x:
            r = {"d": x.get("d"), "o": float(x["o"]), "h": float(x["h"]),
                 "l": float(x["l"]), "c": float(x["c"])}
        else:
            r = {"d": x.get("date"), "o": float(x["open"]), "h": float(x["high"]),
                 "l": float(x["low"]), "c": float(x["close"])}
        try:
            if x.get("v"):
                r["v"] = float(x["v"])
        except (TypeError, ValueError):
            pass
        return r

    for key, sym, tpl in (("AU0", "AU0", SINA_INNER), ("AG0", "AG0", SINA_INNER),
                          ("SC0", "SC0", SINA_INNER), ("CU0", "CU0", SINA_INNER),
                          ("AL0", "AL0", SINA_INNER), ("ZN0", "ZN0", SINA_INNER),
                          ("NI0", "NI0", SINA_INNER), ("SN0", "SN0", SINA_INNER),
                          ("RB0", "RB0", SINA_INNER), ("M0", "M0", SINA_INNER),
                          ("I0", "I0", SINA_INNER), ("C0", "C0", SINA_INNER),
                          ("CF0", "CF0", SINA_INNER), ("XAU", "XAU", SINA_DAILY),
                          ("GC", "GC", SINA_DAILY), ("SI", "SI", SINA_DAILY),
                          ("OIL", "OIL", SINA_DAILY), ("CL", "CL", SINA_DAILY)):
        try:
            raw = _get_text(tpl.format(sym=sym), headers=SINA_HEADERS)
            i, j = raw.find("("), raw.rfind(")")
            arr = json.loads(raw[i + 1:j])
            if not isinstance(arr, list) or not arr:
                raise RuntimeError("空K线")
            out[key] = [norm(x) for x in arr[-250:]]
        except Exception as e:
            print(f"[warn] 日K {sym} 抓取失败: {e}", file=sys.stderr)
    return out


# ---------------- 实时财经快讯（华尔街见闻 lives） ----------------
NEWS_API = "https://api-one.wallstcn.com/apiv1/content/lives?channel=global-channel&limit=30"


def _strip_html(s):
    """去掉 HTML 标签，保留纯文本。"""
    if not s:
        return ""
    import re
    s = re.sub(r"<[^>]+>", "", s)
    return s.replace("&nbsp;", " ").replace("&amp;", "&").replace("&quot;", '"').strip()


def fetch_news():
    """华尔街见闻 7×24 快讯流 → [{title, text, time, source}]。失败返回 []（站内降级显示占位）。"""
    try:
        j = _get_json(NEWS_API, timeout=15,
                      headers={"User-Agent": HEADERS["User-Agent"],
                               "Accept": "application/json, text/plain, */*"})
        items = (j.get("data") or {}).get("items") or []
        out = []
        for it in items[:18]:
            ts = it.get("display_time")
            tstr = ""
            if ts:
                tstr = datetime.datetime.fromtimestamp(int(ts)).strftime("%Y-%m-%d %H:%M")
            text = _strip_html(it.get("content_text") or it.get("content") or "")
            title = _strip_html(it.get("title") or "")
            if not title:
                # 快讯多为纯内容，无标题时取首句
                title = (text.split("。")[0] if text else "快讯")[:40]
            out.append({"title": title, "text": text[:500], "time": tstr,
                        "source": "华尔街见闻", "uri": it.get("uri") or ""})
        return out
    except Exception as e:
        print(f"[warn] 快讯抓取失败: {e}", file=sys.stderr)
        return []


def main():
    items, primary, by_symbol = fetch_sge_all()
    intl, fx_rates = fetch_intl(by_symbol)
    oil = fetch_oil()
    fx_table = build_fx_table(float(intl["usd_cny"]), fx_rates)
    news = fetch_news()
    # 快讯累积:合并历史归档(去重,保留 300 条),避免每日只有当天快讯
    _ARCH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "docs", "news_archive.json")
    try:
        with open(_ARCH, encoding="utf-8") as _f:
            _arch = json.load(_f)
    except Exception:
        _arch = []
    _seen = set()
    _merged = []
    for _n in (news + _arch):
        _k = (_n.get("title") or "") + "|" + (_n.get("time") or "")
        if _k in _seen or not _n.get("title"):
            continue
        _seen.add(_k)
        _merged.append(_n)
    _merged.sort(key=lambda x: x.get("time") or "", reverse=True)
    news_merged = _merged[:300]
    try:
        with open(_ARCH, "w", encoding="utf-8") as _f:
            json.dump(news_merged, _f, ensure_ascii=False, indent=1)
    except Exception:
        pass
    extra = fetch_extra()
    klines = fetch_klines()

    # 布伦特/WTI 升级为 hf_ 实时价(新浪外盘),保留 30 日收盘线供画图
    intl_by_code = {x["code"]: x for x in extra.get("intl") or []}
    for key, code in (("brent", "hf_OIL"), ("wti", "hf_CL")):
        h = intl_by_code.get(code)
        if h and h.get("last"):
            oil[key]["last"] = h["last"]
            oil[key]["prev_close"] = h.get("prev")
            oil[key]["open"] = h.get("open")
            oil[key]["high"] = h.get("high")
            oil[key]["low"] = h.get("low")
            oil[key]["date"] = h.get("date") or oil[key].get("date", "")

    if not items:
        print("[error] SGE 全部抓取失败，保留原缓存。", file=sys.stderr)
        sys.exit(0)

    payload = {
        "generated_at": datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).strftime("%Y-%m-%d %H:%M:%S"),
        "source": "上海黄金交易所 (SGE) · 国际现货贵金属 · 美元兑人民币 · 新浪财经 · 华尔街见闻",
        "live": len([1 for _ in items]),
        "items": items,
        "primary": primary,
        "intl": intl,
        "oil": oil,
        "fx": fx_table,
        "news": news_merged,
        "extra": extra,
        "klines": klines,
    }
    with open(CACHE, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    gold = intl["metals"]["gold"]
    print(f"[ok] 已更新 {len(items)} 个合约 | 国际XAU={intl['xau_usd']} XAG={intl['metals']['silver']['intl_usd']} "
          f"XPT={intl['metals']['platinum']['intl_usd']} | USD/CNY={intl['usd_cny']} | "
          f"溢价 金={gold['premium_pct']}% 银={intl['metals']['silver']['premium_pct']}% "
          f"铂={intl['metals']['platinum']['premium_pct']}% | "
          f"油价 布伦特={oil.get('brent', {}).get('last')} WTI={oil.get('wti', {}).get('last')} "
          f"SC={oil.get('sc', {}).get('last')} | 汇率 {len(fx_table)} 币种 | 快讯 {len(news)} 条")


if __name__ == "__main__":
    main()
