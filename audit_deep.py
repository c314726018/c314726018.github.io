#!/usr/bin/env python3
"""金衡网深度审计:JS 运行时错误 / 死链(含锚点) / 导航重复入口 / 性能 / SEO / 交互元素。输出 JSON 报告。"""
import json
import re
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timezone, timedelta

BASE = "http://82.156.213.143:8080"
# 项目唯一权威路径(旧 WorkBuddy/<日期>/gold-site 已废弃,勿再引用)
DOCS = "/Users/cuisiqi/Documents/workbuddy项目/金衡网/gold-site/docs"
CHROME = ("/Users/cuisiqi/.agent-browser/browsers/chrome-152.0.7977.64/"
          "Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing")
CST = timezone(timedelta(hours=8))
PAGES = ["index.html", "data.html", "calendar.html", "news.html", "academy.html", "feedback.html",
         "about.html", "privacy.html", "history.html"]
results = {"time": datetime.now(CST).strftime("%Y-%m-%d %H:%M:%S"), "js_errors": [], "broken_links": [],
           "anchor_issues": [], "dup_nav_links": [], "perf": [], "seo": [], "interactions": []}


def http(url, timeout=20):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0",
                                               "Accept-Encoding": "gzip"})
    t0 = time.time()
    resp = urllib.request.urlopen(req, timeout=timeout)
    raw = resp.read()  # gzip 开启时 raw = 压缩传输体积(真实带宽)
    if resp.headers.get("Content-Encoding") == "gzip":
        import gzip as _g
        body = _g.decompress(raw)
    else:
        body = raw
    return body, (time.time() - t0) * 1000, len(raw)  # body=解压后, raw=传输体积


# ===== 1) JS 运行时错误扫描(headless 逐页收集 console error / uncaught) =====
for page in PAGES:
    try:
        r = subprocess.run(
            [CHROME, "--headless", "--disable-gpu", "--no-sandbox", "--enable-logging=stderr", "--v=0",
             "--host-resolver-rules=MAP pagead2.googlesyndication.com 127.0.0.1",
             "--virtual-time-budget=6000", "--dump-dom", f"{BASE}/{page}"],
            capture_output=True, text=True, timeout=90)
        errs = []
        for line in (r.stderr or "").splitlines():
            if "CONSOLE" not in line:
                continue
            low = line.lower()
            if "cors" in low and ("manifest" in low or "fetch" in low):
                continue  # file:// 之外的已知噪音(线上为 https,无此问题)
            if re.search(r'"(Uncaught|error|failed|refused)', line, re.I) or "ERROR:" in line:
                errs.append(re.sub(r".*CONSOLE:\d+\] ", "", line).strip()[:150])
        if errs:
            results["js_errors"].append({"page": page, "count": len(errs), "samples": errs[:3]})
    except subprocess.TimeoutExpired:
        results["js_errors"].append({"page": page, "count": 1, "samples": ["页面加载超时(90s)"]})
    except Exception as e:
        results["js_errors"].append({"page": page, "count": 1, "samples": [f"扫描器异常: {str(e)[:80]}"]})

# ===== 2) 死链检测(全部站内 href/src,含 #锚点) =====
# 历史教训:旧正则 href="(\./[^"#]+)" 主动排除了带 # 的链接,而导航子栏目全是
# xxx.html#锚点 形式,导致"空壳入口/锚点失效/重复指向"长期成盲区,靠人工才发现。
# 现改为:①普通链接验 HTTP ②锚点链接同时验目标页可达 + 目标页存在该 id。
page_cache = {}


def get_page(pg):
    """抓取并缓存页面 HTML,避免同一页重复请求。"""
    if pg not in page_cache:
        page_cache[pg] = http(f"{BASE}/{pg}", timeout=15)[0].decode("utf-8", "ignore")
    return page_cache[pg]


try:
    # 扫描全部页面,不只 index —— 导航条/侧栏在每个页面都存在
    all_links = {}       # 全站 URL 集合,用于死链/锚点校验(含新闻列表等所有 <a>)
    nav_links = {}       # (区域, URL) -> set(链接文字),用于重复入口检测
    for pg in PAGES:
        html = get_page(pg)
        # 全部站内链接 + 静态资源:验 HTTP 可达与锚点真实存在
        for href in re.findall(r'<a[^>]*href="(\./[^"]+)"', html):
            all_links.setdefault(href, set())
        for src in re.findall(r'src="(\./[^"]+)"', html):
            all_links.setdefault(src, set())
        # 只取导航区(二级导航/左侧栏/页脚栏目),避免新闻列表标题各异被误判为重复入口。
        # 按(区域,URL)分组:一级导航/二级子栏目/页脚本就是不同层,跨层同名不算重复;
        # 只有同一区域内两个不同文案指向同一 URL(如 7×24快讯 与 资讯来源)才算。
        for zone in ("subnav-links", "side-nav", "foot-col"):
            blocks = re.findall(r'<[^>]*class="[^"]*\b' + zone + r'\b[^"]*"[^>]*>(.*?)</(?:nav|ul|div)>', html, re.S)
            for idx, block in enumerate(blocks):
                # 页脚每一列是独立栏目,必须按块序号区分,否则不同列的同名链接被误判重复
                zone_key = f"{zone}#{idx}" if zone == "foot-col" else zone
                for href, text in re.findall(r'<a[^>]*href="(\./[^"]+)"[^>]*>(.*?)</a>', block, re.S):
                    clean = re.sub(r"<[^>]+>", "", text).strip()[:20]
                    if clean:
                        nav_links.setdefault((zone_key, href), set()).add(clean)

    for link in sorted(all_links):
        parts = link[2:].split("#", 1)  # link 形如 index.html#overview
        target = parts[0] or "index.html"
        anchor = parts[1] if len(parts) > 1 else None
        try:
            body = get_page(target)
        except urllib.error.HTTPError as e:
            results["broken_links"].append({"link": link, "status": e.code})
            continue
        except Exception as e:
            results["broken_links"].append({"link": link, "status": str(e)[:60]})
            continue
        # 锚点必须真实存在于目标页
        if anchor and f'id="{anchor}"' not in body:
            results["anchor_issues"].append({"link": link, "reason": f"目标页无 id={anchor}"})

    # 同一导航区内,同 URL 被多个不同文案指向 = 重复入口(历史案例:7×24快讯/资讯来源 都指 #live)
    for (zone, link), texts in sorted(nav_links.items()):
        meaningful = {t for t in texts if t}
        if len(meaningful) > 1:
            results["dup_nav_links"].append({"zone": zone, "link": link, "texts": sorted(meaningful)})
except Exception as e:
    results["broken_links"].append({"link": "(扫描失败)", "status": str(e)[:80]})

# ===== 3) 性能(每页加载耗时 + 体积) =====
for page in PAGES:
    try:
        body, ms, raw_len = http(f"{BASE}/{page}", timeout=25)
        results["perf"].append({"page": page, "ms": round(ms), "kb": round(raw_len / 1024, 1),
                                "ok": ms < 3000 and raw_len < 500 * 1024})
    except Exception as e:
        results["perf"].append({"page": page, "ms": -1, "kb": 0, "ok": False, "err": str(e)[:60]})

# ===== 4) SEO 抽查(index/data/calendar 三页) =====
seo_checks = [
    ("index.html", "金衡网 - 今日黄金价格"),
    ("data.html", "数据中心"),
    ("calendar.html", "财经日历"),
]
for page, expect_title in seo_checks:
    try:
        html = http(f"{BASE}/{page}")[0].decode("utf-8", "ignore")
        title = re.search(r"<title>([^<]+)</title>", html)
        desc = re.search(r'<meta name="description" content="([^"]*)"', html)
        canonical = 'rel="canonical"' in html
        og = 'property="og:' in html
        h1 = len(re.findall(r"<h1[ >]", html))
        results["seo"].append({
            "page": page,
            "title_ok": bool(title and expect_title.split(" - ")[0] in (title.group(1) or "")),
            "desc_len": len(desc.group(1)) if desc else 0,
            "canonical": canonical, "og": og, "h1_count": h1,
            "issues": [i for i, ok in {
                "title 缺失/不符": not (title and expect_title.split(" - ")[0] in (title.group(1) or "")),
                "description 缺失": not desc, "canonical 缺失": not canonical,
                "og 标签缺失": not og, "h1 数量≠1": h1 != 1}.items() if ok],
        })
    except Exception as e:
        results["seo"].append({"page": page, "issues": [f"抓取失败 {str(e)[:60]}"]})

# ===== 5) 交互元素存在性(index 关键控件) =====
try:
    idx = http(f"{BASE}/index.html")[0].decode("utf-8", "ignore")
    # 注:备案合规模式下价格提醒/订阅已隐藏,mailSubmit/alertTypeBox 不再检查,避免误报缺失
    checks = [
        ("全屏按钮", 'data-act="fs"'), ("周期切换", 'data-p="d"'), ("指标切换", 'data-ind="ma"'),
        ("副图切换", 'data-sub="macd"'), ("品种tab", 'data-i="0"'), ("收藏按钮", "fav"),
        ("换算器", "ocOut"), ("交叉汇率", "fcCur2"), ("骨架屏", "skel-box"),
    ]
    for name, marker in checks:
        results["interactions"].append({"feature": name, "present": marker in idx})
except Exception as e:
    results["interactions"].append({"feature": "扫描失败", "present": False, "err": str(e)[:60]})

# 汇总结论
issues = (sum(x["count"] for x in results["js_errors"]) + len(results["broken_links"]) +
          len(results["anchor_issues"]) + len(results["dup_nav_links"]) +
          sum(1 for x in results["perf"] if not x["ok"]) +
          sum(len(x.get("issues", [])) for x in results["seo"]) +
          sum(1 for x in results["interactions"] if not x["present"]))
results["summary"] = {
    "verdict": "无错误" if issues == 0 else f"{issues} 个待处理",
    "js_errors": sum(x["count"] for x in results["js_errors"]),
    "broken_links": len(results["broken_links"]),
    "anchor_issues": len(results["anchor_issues"]),
    "dup_nav_links": len(results["dup_nav_links"]),
    "perf_issues": sum(1 for x in results["perf"] if not x["ok"]),
    "seo_issues": sum(len(x.get("issues", [])) for x in results["seo"]),
    "interaction_missing": sum(1 for x in results["interactions"] if not x["present"]),
}
print(json.dumps(results, ensure_ascii=False, indent=1))
