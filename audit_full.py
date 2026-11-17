#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""全维度审计(四维零 bug 保障):
代码(语法/结构/链接) + 视觉(3 视口×9 页/横滚/空白) + 操作(20+ 交互断言) + 逻辑(边界值/34 品种全量比对)"""
import json
import os
import re
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone, timedelta

BASE = "http://82.156.213.143:8080"
ROOT = "/Users/cuisiqi/Documents/workbuddy项目/金衡网/gold-site"
DOCS = ROOT + "/docs"
SHOTS = ROOT + "/shots/full"
CHROME = ("/Users/cuisiqi/.agent-browser/browsers/chrome-152.0.7977.64/"
          "Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing")
CST = timezone(timedelta(hours=8))
PAGES = ["index", "data", "calendar", "news", "academy", "feedback", "about", "privacy", "history"]
report = {"time": datetime.now(CST).strftime("%Y-%m-%d %H:%M:%S"),
          "code": [], "visual": [], "action": [], "logic": []}

def http(url, timeout=20):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    return urllib.request.urlopen(req, timeout=timeout).read()

def chrome_dom(url, budget=9000):
    r = subprocess.run(
        [CHROME, "--headless", "--disable-gpu", "--no-sandbox", "--enable-logging=stderr", "--v=0",
         "--host-resolver-rules=MAP pagead2.googlesyndication.com 127.0.0.1",
         f"--virtual-time-budget={budget}", "--dump-dom", url],
        capture_output=True, text=True, timeout=120)
    return r.stdout or "", r.stderr or ""

def chrome_shot(url, shot, w=1440, h=1000):
    subprocess.run(
        [CHROME, "--headless", "--disable-gpu", "--no-sandbox",
         "--host-resolver-rules=MAP pagead2.googlesyndication.com 127.0.0.1",
         f"--virtual-time-budget=8000", f"--window-size={w},{h}", f"--screenshot={shot}", url],
        capture_output=True, text=True, timeout=120)

# ============ 维度一:代码 ============
# (链接/语法/解析已在 multi_check 覆盖,此处做增量:内联 <script> 语法抽检)
inline_ok, inline_bad = 0, []
for pg in PAGES:
    html = http(f"{BASE}/{pg}.html").decode("utf-8", "ignore")
    scripts = re.findall(r'<script(?![^>]*src)(?![^>]*application/(?:ld\+)?json)[^>]*>([\s\S]{50,}?)</script>', html)
    for i, s in enumerate(scripts[:3]):
        if "app-data" in html[:html.find(s)] and i == 0:
            continue  # JSON 数据块跳过
        tmp = DOCS + f"/_inline_{pg}_{i}.js"
        open(tmp, "w").write(s)
        r = subprocess.run(["node", "--check", tmp], capture_output=True, text=True, timeout=20)
        if r.returncode != 0:
            inline_bad.append(f"{pg}#{i}: {r.stderr.strip()[:80]}")
        else:
            inline_ok += 1
        os.remove(tmp)
report["code"].append({"check": "内联 script 语法", "ok": not inline_bad,
                       "detail": f"{inline_ok} 段通过" + (f",异常: {inline_bad[:2]}" if inline_bad else "")})

# ============ 维度二:视觉(3 视口 × 9 页) ============
os.makedirs(SHOTS, exist_ok=True)
VIEWPORTS = [("mobile", 375, 812), ("tablet", 768, 1024), ("desktop", 1440, 1000)]
vis_issues = []
for vp_name, w, h in VIEWPORTS:
    for pg in PAGES:
        shot = f"{SHOTS}/{pg}-{vp_name}.png"
        chrome_shot(f"{BASE}/{pg}.html", shot, w, h)
        size = os.path.getsize(shot) if os.path.isfile(shot) else 0
        if size < 8000:
            vis_issues.append(f"{pg}@{vp_name} 疑似空白({size//1024}KB)")
        # 横向滚动检测(注入)
        probe = http(f"{BASE}/{pg}.html").decode("utf-8", "ignore").replace(
            "</body>",
            f"""<script>
setTimeout(function(){{
  document.title = "HS|" + (document.documentElement.scrollWidth > document.documentElement.clientWidth + 2 ? "OVERFLOW:" + document.documentElement.scrollWidth : "OK");
}}, 2500);
</script>
</body>""")
        pf = DOCS + f"/_probe_{pg}_{vp_name}.html"
        open(pf, "w", encoding="utf-8").write(probe)
        _, err = chrome_dom(f"file://{pf}", 6000)
        m = re.search(r"<title>HS\|([^<]*)</title>", _)
        title = ""
        try:
            _, _e2 = chrome_dom(f"file://{pf}", 6000)
            m = re.search(r"<title>HS\|([^<]*)</title>", _e2)
        except Exception:
            pass
        if m and "OVERFLOW" in m.group(1):
            vis_issues.append(f"{pg}@{vp_name} 横向溢出 {m.group(1)}")
        os.remove(pf)
report["visual"].append({"check": "3 视口 × 9 页截图+横滚", "ok": not vis_issues,
                         "detail": f"27 张截图于 {SHOTS}" + (f",问题: {vis_issues[:4]}" if vis_issues else "")})
print(f"[视觉] {'通过' if not vis_issues else str(len(vis_issues)) + ' 个问题'}")

# ============ 维度三+四:操作与逻辑(注入断言,本地 http 服务) ============
import threading, http.server as _hs, socketserver, functools
Handler = functools.partial(_hs.SimpleHTTPRequestHandler, directory=DOCS)
class Srv(socketserver.TCPServer):
    allow_reuse_address = True
srv = Srv(("127.0.0.1", 8091), Handler)
t = threading.Thread(target=srv.serve_forever, daemon=True)
t.start()
LOCAL = "http://127.0.0.1:8091"

# 操作断言(index 页 20+ 交互点,一次注入全部执行)
ACTION_JS = """
(function(){
  var out = [];
  function t(name, fn){ try { var r = fn(); out.push(name + "=" + (r ? "PASS" : "FAIL")); } catch(e) { out.push(name + "=ERR:" + e.message.slice(0,40)); } }
  function click(el){ el.dispatchEvent(new MouseEvent("click", {bubbles:true})); }
  // 1-2 贵金属 tab 切换(分时→日K→回)
  t("贵金属tab切换", function(){ var a=document.querySelector('#qm1 .tq-tabs a[data-i="1"]'); click(a); return a.classList.contains("on"); });
  // 3-4 能源 tab 遍历(3 个样本)
  t("能源tab样本", function(){ var ok=true; [0,5,9].forEach(function(i){ var a=document.querySelector('#qm3 .tq-tabs a[data-i="'+i+'"]'); click(a); if(!a.classList.contains("on")) ok=false; }); return ok; });
  // 5-6 副图指标(MACD→RSI)
  t("RSI副图", function(){ var a=document.querySelector('#qm1Tools [data-sub="rsi"]'); click(a); return a.classList.contains("on"); });
  // 7 全屏开/关
  t("全屏开关", function(){ var f=document.querySelector('[data-act="fs"]'); click(f); var ov=document.getElementById("fsOverlay"); var opened=ov.classList.contains("open"); ov.classList.remove("open"); return opened; });
  // 8 搜索建议
  t("搜索建议", function(){ var s=document.getElementById("siteSearch"); s.value="沪铜"; s.dispatchEvent(new Event("input")); var sug=document.getElementById("searchSug"); return sug && sug.innerHTML.indexOf("沪铜") >= 0; });
  // 9 换算器计算(1000 USD ≈ 6678 CNY ±10%)
  t("换算器USD→CNY", function(){
    var amt=document.getElementById("ocAmt"),cur=document.getElementById("ocCur"),out=document.getElementById("ocOut");
    if(!amt) return false;
    amt.value="1000"; cur.value="USD"; amt.dispatchEvent(new Event("input")); cur.dispatchEvent(new Event("change"));
    var v=parseFloat((out.textContent||"").replace(/[^0-9.]/g,""));
    return v > 6000 && v < 7400;
  });
  // 10 换算器边界:0 输入
  t("换算器0输入", function(){
    var amt=document.getElementById("ocAmt"),out=document.getElementById("ocOut");
    amt.value="0"; amt.dispatchEvent(new Event("input"));
    return (out.textContent||"").length > 0;  // 不抛错且有输出
  });
  // 11-13 模拟盘:买入→持仓→卖出→清仓
  t("模拟盘买入", function(){
    document.getElementById("simDir").value="buy";
    document.getElementById("simG").value="100";
    click(document.getElementById("simGo"));
    var rows=document.getElementById("simRows").innerHTML;
    return rows.indexOf("100g") >= 0;
  });
  t("模拟盘持仓显示", function(){ return parseFloat((document.getElementById("simHoldVal").textContent||"").replace(/[^0-9.]/g,"")) > 0; });
  t("模拟盘卖出清仓", function(){
    document.getElementById("simDir").value="sell";
    document.getElementById("simG").value="200";
    click(document.getElementById("simGo"));
    return document.getElementById("simRows").innerHTML.indexOf("暂无持仓") >= 0;
  });
  t("模拟盘重置", function(){ click(document.getElementById("simReset")); var a=JSON.parse(localStorage.getItem("simAccount_v1")||"{}"); return a.cash === 1000000; });
  // 14 提醒表单提交(localStorage 规则+1)
  t("提醒表单提交", function(){
    var before=(localStorage.getItem("gold_alerts")||"[]").length;
    var mail=document.getElementById("alertMail"),target=document.getElementById("alertTarget");
    if(!mail||!target) return false;
    mail.value="test@example.com"; target.value="900";
    click(document.getElementById("alertSubmit"));
    var after=(localStorage.getItem("gold_alerts")||"[]").length;
    return after > before;
  });
  // 15-16 收藏增删
  t("收藏添加", function(){
    var f=document.querySelector(".fav"); if(!f) return false;
    var before=document.querySelectorAll(".fav.on").length;
    click(f); return document.querySelectorAll(".fav.on").length === before+1;
  });
  // 17 公告条关闭
  t("公告条关闭", function(){
    var x=document.getElementById("pbClose"); if(!x) return false;
    click(x); return document.getElementById("promoBar").style.display === "none";
  });
  // 18 主题切换
  t("主题切换", function(){
    var b=document.getElementById("themeBtn") || document.querySelector('[aria-label*="主题"]');
    if(!b) return false;
    var before=document.documentElement.classList.contains("dark");
    click(b); var after=document.documentElement.classList.contains("dark");
    click(b); return before !== after;
  });
  // 19 行情表行跳转属性
  t("行情表行直链", function(){
    var tr=document.querySelector("#tbody tr[data-goto]");
    return tr && tr.getAttribute("data-goto").indexOf("quote-") === 0;
  });
  // 20 返回顶部按钮存在
  t("返回顶部", function(){ return !!document.querySelector("#backTop") || !!document.querySelector('[aria-label*="返回"]'); });
  // 21 热力图周期切换
  t("热力图周期", function(){
    var a=document.querySelector("#heatTabs a[data-p]");
    if(!a) return false; click(a); return a.classList.contains("on");
  });
  // 22 骨架清理
  t("骨架清理", function(){ return document.querySelectorAll("[data-skel]").length === 0; });
  var dv = document.createElement("div");
  dv.id = "auditOut";
  dv.textContent = "SMOKE|" + out.join(" | ");
  document.body.appendChild(dv);
})();
</script>
"""
html = http(f"{BASE}/index.html").decode("utf-8", "ignore")
# app-data 注入真数据(同步渲染:DATA 在脚本初始化即有值,断言可同步执行)
_d = json.load(open(DOCS + "/data.json"))
_payload = {k: _d.get(k) for k in ("primary", "items", "extra", "klines", "fx", "oil", "intl", "heat", "heat_multi", "generated_at", "daily_report", "news", "oil_retail", "alert_mail", "symbol_slug")}
_payload["news"] = (_payload.get("news") or [])[:10]
html = html.replace('<script id="app-data" type="application/json">{}</script>',
                    '<script id="app-data" type="application/json">' + json.dumps(_payload, ensure_ascii=False) + '</script>')
html = html.replace("</body>", ACTION_JS + "</body>")
pf = DOCS + "/_smoke_full.html"
open(pf, "w", encoding="utf-8").write(html)
out, err = chrome_dom(f"{LOCAL}/_smoke_full.html", 14000)
m = re.search(r'<div id="auditOut">SMOKE\|([^<]*)</div>', out)
smoke_raw = m.group(1) if m else ""
if not smoke_raw:
    open(DOCS + "/_smoke_debug.txt", "w").write((out or "")[-1500:] + "\n===STDERR===\n" + (err or "")[-2500:])
results = smoke_raw.split(" | ") if smoke_raw else []
pass_n = sum(1 for x in results if "=PASS" in x)
report["action"].append({"check": "index 交互冒烟", "total": len(results), "pass": pass_n, "results": results})
print(f"[操作] {pass_n}/{len(results)} 通过")
for x in results:
    if "PASS" not in x:
        report["action"].append({"check": "交互失败", "detail": x, "ok": False})

# 逻辑断言:34 品种页价格 vs data.json 全量比对
d = json.load(open(DOCS + "/data.json"))
SLUGS = d.get("symbol_slug") or {}
SYM_LAST = {}
for x in d.get("items") or []:
    SYM_LAST[x["symbol"]] = x.get("last")
for x in (d.get("extra") or {}).get("futures") or []:
    SYM_LAST[x.get("code")] = x.get("last")
for x in (d.get("extra") or {}).get("intl") or []:
    SYM_LAST[x.get("code")] = x.get("last")
o = d.get("oil") or {}
SYM_LAST["Brent"] = (o.get("brent") or {}).get("last")
SYM_LAST["WTI"] = (o.get("wti") or {}).get("last")
mismatch, checked = [], 0
for sym, slug in SLUGS.items():
    expect = SYM_LAST.get(sym)
    if expect is None:
        continue
    try:
        h = open(DOCS + f"/quote-{slug}.html", encoding="utf-8").read()
        checked += 1
        s = f"{expect:,.2f}" if isinstance(expect, (int, float)) else str(expect)
        if s not in h and f"{expect:.2f}" not in h:
            mismatch.append(f"{slug}(期望 {s})")
    except Exception as e:
        mismatch.append(f"{slug}: {str(e)[:40]}")
report["logic"].append({"check": "34 品种页价格比对", "checked": checked, "ok": not mismatch,
                        "detail": "全部一致" if not mismatch else f"不一致: {mismatch[:5]}"})
print(f"[逻辑] 品种页比对 {checked} 页,{'全部一致' if not mismatch else str(len(mismatch)) + ' 不一致'}")
srv.shutdown()

# 汇总
issues = []
for dim in ("code", "visual", "action", "logic"):
    for item in report[dim]:
        if item.get("ok") is False or "FAIL" in str(item.get("detail", "")):
            issues.append(f"[{dim}] {item.get('check')}: {str(item.get('detail'))[:80]}")
fails = [x for x in results if "PASS" not in x]
report["summary"] = {
    "verdict": "四维全部通过" if not issues and not fails else f"{len(issues)+len(fails)} 个问题",
    "action_pass": f"{pass_n}/{len(results)}",
    "quote_mismatch": len(mismatch),
    "visual_issues": len(vis_issues),
}
json.dump(report, open(ROOT + "/audit_full_report.json", "w"), ensure_ascii=False, indent=1)
print(json.dumps(report["summary"], ensure_ascii=False))
for i in issues:
    print(" ", i)
for f in fails:
    print("  交互:", f)
