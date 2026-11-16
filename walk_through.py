#!/usr/bin/env python3
"""浏览器级全站走查:9 页真实渲染+截图+console 错误+资源加载失败检测。发布前必跑。"""
import json, re, subprocess, sys, time, urllib.request
from datetime import datetime, timezone, timedelta

BASE = "http://82.156.213.143:8080"
DOCS = "/Users/cuisiqi/WorkBuddy/2026-11-10-16-34-12/gold-site/docs"
SHOTS = "/Users/cuisiqi/WorkBuddy/2026-11-10-16-34-12/gold-site/shots"
CHROME = ("/Users/cuisiqi/.agent-browser/browsers/chrome-152.0.7977.64/"
          "Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing")
CST = timezone(timedelta(hours=8))
PAGES = ["index.html", "data.html", "calendar.html", "news.html", "academy.html",
         "feedback.html", "about.html", "privacy.html", "history.html"]

def http(url, timeout=20):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    return urllib.request.urlopen(req, timeout=timeout).read()

report = {"time": datetime.now(CST).strftime("%Y-%m-%d %H:%M:%S"), "pages": [], "console_errors": [], "failed_resources": [], "screenshots": []}

for page in PAGES:
    name = page.replace(".html", "")
    shot = f"{SHOTS}/{name}.png"
    try:
        r = subprocess.run(
            [CHROME, "--headless", "--disable-gpu", "--no-sandbox", "--enable-logging=stderr", "--v=1",
             "--host-resolver-rules=MAP pagead2.googlesyndication.com 127.0.0.1",
             "--virtual-time-budget=8000", "--window-size=1440,1100",
             f"--screenshot={shot}", f"{BASE}/{page}"],
            capture_output=True, text=True, timeout=120)
        errs = []
        for line in (r.stderr or "").splitlines():
            low = line.lower()
            if "CONSOLE" not in line:
                continue
            if re.search(r'"(Uncaught|error|failed|refused|404)', line, re.I):
                errs.append(re.sub(r".*CONSOLE:\d+\] ", "", line).strip()[:150])
        shot_ok = len(r.stdout or "") >= 0
        import os
        png_size = os.path.getsize(shot) if os.path.isfile(shot) else 0
        # 空白页检测:PNG 过小(<15KB)多为纯色空白
        report["pages"].append({"page": page, "shot_kb": round(png_size / 1024, 1),
                                "blank_suspect": png_size < 15000,
                                "console_err_count": len(errs)})
        report["screenshots"].append(shot)
        if errs:
            report["console_errors"].append({"page": page, "samples": errs[:4]})
    except subprocess.TimeoutExpired:
        report["pages"].append({"page": page, "shot_kb": 0, "blank_suspect": True, "console_err_count": 0, "timeout": True})
    except Exception as e:
        report["pages"].append({"page": page, "err": str(e)[:80]})

# ===== 资源加载失败检测(每页引用的 css/js/json/images) =====
checked = set()
for page in PAGES:
    try:
        html = http(f"{BASE}/{page}").decode("utf-8", "ignore")
        refs = set(re.findall(r'(?:src|href)="(\./[^"\#]+)"', html))
        for ref in refs:
            if ref in checked:
                continue
            checked.add(ref)
            try:
                http(f"{BASE}/{ref}", timeout=15)
            except urllib.error.HTTPError as e:
                report["failed_resources"].append({"page": page, "ref": ref, "status": e.code})
            except Exception as e:
                report["failed_resources"].append({"page": page, "ref": ref, "status": str(e)[:50]})
    except Exception:
        pass

# ===== 交互冒烟:JS 注入点击关键控件(index) =====
smoke_html = http(f"{BASE}/index.html").decode("utf-8", "ignore")
smoke = smoke_html.replace("</body>", """
<script>
setTimeout(function(){
  var out = [];
  try { var t = document.querySelector('#qm1 .tq-mode [data-m="1"]'); t.click(); out.push("日K切换:" + (t.classList.contains("on") ? "OK" : "FAIL")); } catch(e) { out.push("日K切换:ERR"); }
  try { var f = document.querySelector('[data-act="fs"]'); f.click(); out.push("全屏:" + (document.getElementById("fsOverlay").classList.contains("open") ? "OK" : "FAIL")); document.getElementById("fsOverlay").classList.remove("open"); } catch(e) { out.push("全屏:ERR"); }
  try { var s = document.getElementById("siteSearch"); s.value = "沪铜"; s.dispatchEvent(new Event("input")); var sug = document.getElementById("searchSug"); out.push("搜索:" + (sug.style.display !== "none" ? "OK" : "FAIL")); } catch(e) { out.push("搜索:ERR"); }
  try { var e2 = document.querySelector('#qm1Tools [data-sub="rsi"]'); e2.click(); out.push("RSI副图:" + (e2.classList.contains("on") ? "OK" : "FAIL")); } catch(e) { out.push("RSI副图:ERR"); }
  document.title = "SMOKE|" + out.join(" | ");
}, 2000);
</script>
</body>""")
open(f"{DOCS}/_smoke.html", "w").write(smoke)
r = subprocess.run(
    [CHROME, "--headless", "--disable-gpu", "--no-sandbox", "--host-resolver-rules=MAP pagead2.googlesyndication.com 127.0.0.1",
     "--virtual-time-budget=8000", "--dump-dom", f"file://{DOCS}/_smoke.html"],
    capture_output=True, text=True, timeout=120)
m = re.search(r"<title>SMOKE\|([^<]*)</title>", r.stdout or "")
report["smoke"] = m.group(1) if m else "冒烟测试未返回"
import os
if os.path.isfile(f"{DOCS}/_smoke.html"):
    os.remove(f"{DOCS}/_smoke.html")

crit = [p for p in report["pages"] if p.get("blank_suspect") or p.get("err") or p.get("timeout")]
report["verdict"] = "全部通过" if (not crit and not report["console_errors"] and not report["failed_resources"] and "FAIL" not in report["smoke"] and "ERR" not in report["smoke"]) else f"{len(crit)} 页空白/超时, {len(report['console_errors'])} 页有 console 错误, {len(report['failed_resources'])} 资源失败"
print(json.dumps(report, ensure_ascii=False, indent=1))
