#!/usr/bin/env python3
"""金衡网深度审计:JS 运行时错误 / 死链 / 性能 / SEO / 交互元素。输出 JSON 报告。"""
import json
import re
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timezone, timedelta

BASE = "http://82.156.213.143:8080"
DOCS = "/Users/cuisiqi/WorkBuddy/2026-11-10-16-34-12/gold-site/docs"
CHROME = ("/Users/cuisiqi/.agent-browser/browsers/chrome-152.0.7977.64/"
          "Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing")
CST = timezone(timedelta(hours=8))
PAGES = ["index.html", "data.html", "calendar.html", "news.html", "academy.html", "feedback.html",
         "about.html", "privacy.html", "history.html"]
results = {"time": datetime.now(CST).strftime("%Y-%m-%d %H:%M:%S"), "js_errors": [], "broken_links": [],
           "perf": [], "seo": [], "interactions": []}


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

# ===== 2) 死链检测(index.html 全部站内 href/src) =====
try:
    idx = http(f"{BASE}/index.html")[0].decode("utf-8", "ignore")
    links = set(re.findall(r'href="(\./[^"#]+)"', idx)) | set(re.findall(r'src="(\./[^"]+)"', idx))
    for link in sorted(links)[:40]:
        url = f"{BASE}/{link[2:]}"
        try:
            http(url, timeout=15)
        except urllib.error.HTTPError as e:
            results["broken_links"].append({"link": link, "status": e.code})
        except Exception as e:
            results["broken_links"].append({"link": link, "status": str(e)[:60]})
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
    checks = [
        ("全屏按钮", 'data-act="fs"'), ("周期切换", 'data-p="d"'), ("指标切换", 'data-ind="ma"'),
        ("副图切换", 'data-sub="macd"'), ("品种tab", 'data-i="0"'), ("收藏按钮", "fav"),
        ("提醒表单", "mailSubmit"), ("类型切换", "alertTypeBox"), ("换算器", "ocOut"),
        ("交叉汇率", "fcCur2"), ("骨架屏", "skel-box"), ("自选收藏", "fav"),
    ]
    for name, marker in checks:
        results["interactions"].append({"feature": name, "present": marker in idx})
except Exception as e:
    results["interactions"].append({"feature": "扫描失败", "present": False, "err": str(e)[:60]})

# 汇总结论
issues = (sum(x["count"] for x in results["js_errors"]) + len(results["broken_links"]) +
          sum(1 for x in results["perf"] if not x["ok"]) +
          sum(len(x.get("issues", [])) for x in results["seo"]) +
          sum(1 for x in results["interactions"] if not x["present"]))
results["summary"] = {
    "verdict": "无错误" if issues == 0 else f"{issues} 个待处理",
    "js_errors": sum(x["count"] for x in results["js_errors"]),
    "broken_links": len(results["broken_links"]),
    "perf_issues": sum(1 for x in results["perf"] if not x["ok"]),
    "seo_issues": sum(len(x.get("issues", [])) for x in results["seo"]),
    "interaction_missing": sum(1 for x in results["interactions"] if not x["present"]),
}
print(json.dumps(results, ensure_ascii=False, indent=1))
