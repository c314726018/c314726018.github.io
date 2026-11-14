#!/usr/bin/env python3
"""金衡网每日健康检查:可用性/数据新鲜度/完整性/双轨同步/引擎状态。输出 JSON 报告。"""
import json
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timezone, timedelta

BASE = "http://82.156.213.143:8080"
GH = "https://c314726018.github.io"
REPO = "/Users/cuisiqi/WorkBuddy/2026-11-10-16-34-12/gold-site"
CST = timezone(timedelta(hours=8))
results = []


def check(name, ok, detail="", level="warn"):
    results.append({"item": name, "ok": bool(ok), "detail": str(detail)[:200], "level": "critical" if not ok and level == "critical" else "warn" if not ok else "info"})


def http(url, timeout=20):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    return urllib.request.urlopen(req, timeout=timeout).read()


# 1. 页面可用性 + 品牌关键词
for page, kw in [("index.html", "金衡网"), ("data.html", "关键指标"), ("calendar.html", "央行"),
                 ("news.html", "快讯"), ("academy.html", "术语"), ("feedback.html", "留言")]:
    try:
        html = http(f"{BASE}/{page}").decode("utf-8", "ignore")
        code_ok = len(html) > 5000
        kw_ok = kw in html
        check(f"页面 {page}", code_ok and kw_ok, f"{len(html)//1024}KB 关键词[{kw}]={'在' if kw_ok else '缺失'}", "critical")
    except Exception as e:
        check(f"页面 {page}", False, f"{type(e).__name__}: {str(e)[:80]}", "critical")

# 2. data.json 新鲜度与完整性
try:
    d = json.loads(http(f"{BASE}/data.json").decode("utf-8", "ignore"))
    gen = d.get("generated_at") or ""
    gen_dt = datetime.strptime(gen, "%Y-%m-%d %H:%M:%S").replace(tzinfo=CST)
    age_min = (datetime.now(CST) - gen_dt).total_seconds() / 60
    check("数据新鲜度", age_min < 45, f"generated_at={gen},距今 {age_min:.0f} 分钟(>45=自续链引擎疑似故障)", "critical")
    items = d.get("items") or []
    kl = d.get("klines") or {}
    check("SGE 合约数", len(items) == 9, f"items={len(items)}(应为 9)", "critical")
    check("K线品种", len(kl) >= 18 and all(len(v) >= 200 for v in kl.values()),
          f"品种 {len(kl)},最少根数 {min((len(v) for v in kl.values()), default=0)}")
    check("快讯量", len(d.get("news") or []) >= 100, f"news={len(d.get('news') or [])} 条(7 天累积中,>=100 为达标)")
    hm = d.get("heat_multi") or []
    check("热力图多周期", len(hm) == 16, f"heat_multi={len(hm)} 品种")
    au = next((x for x in items if x.get("symbol") == "Au99.99"), None) or {}
    p = au.get("last") or 0
    check("金价合理性", 300 < p < 2000, f"Au99.99={p} 元/克")
except Exception as e:
    check("data.json 加载", False, f"{type(e).__name__}: {str(e)[:100]}", "critical")

# 3. 功能抽查
try:
    idx = http(f"{BASE}/index.html").decode("utf-8", "ignore")
    for kw, name in [("金市异动提醒", "topbar 提醒按钮"), ("标准金条企业名录", "标准金条名录"),
                     ("ocOut", "原油换算器"), ("fcCur2", "交叉汇率"), ("heatTabs", "热力图周期切换")]:
        check(f"功能[{name}]", kw in idx, "存在" if kw in idx else "缺失")
except Exception as e:
    check("功能抽查", False, str(e)[:100])

# 4. GitHub Pages 双轨
try:
    gh_html = http(f"{GH}/index.html").decode("utf-8", "ignore")
    gh_data = json.loads(http(f"{GH}/data.json").decode("utf-8", "ignore"))
    gen_gh = gh_data.get("generated_at") or ""
    check("GitHub Pages 双轨", "金衡网" in gh_html, f"data generated_at={gen_gh}")
except Exception as e:
    check("GitHub Pages 双轨", False, f"{type(e).__name__}: {str(e)[:80]}", "warn")

# 5. git 同步(本地 vs 远程)
try:
    r = subprocess.run(["git", "-C", REPO, "fetch", "origin"], capture_output=True, timeout=60)
    if r.returncode == 0:
        c = subprocess.run(["git", "-C", REPO, "rev-list", "--left-right", "--count", "main...origin/main"],
                           capture_output=True, text=True, timeout=30)
        ahead, behind = (c.stdout.strip().split() or ["0", "0"])
        # behind>0 = 自续链数据 commit 正常流入;仅 ahead>0 需要推送功能修改
        check("git 同步", ahead == "0",
              f"本地领先 {ahead}{'(有未推送的功能修改)' if ahead != '0' else ''} / 落后 {behind}(自续链数据流,正常)")
    else:
        check("git fetch", False, "网络不可达(不影响线上,仅本地推送通道)")
except subprocess.TimeoutExpired:
    check("git fetch", False, "超时", "warn")

# 6. 服务器磁盘
try:
    r = subprocess.run(["ssh", "-i", f"{REPO}/../.ssh/jinchao_deploy".replace("/../.ssh", "/.ssh").replace(REPO, "/Users/cuisiqi"),
                        "-o", "ConnectTimeout=15", "-o", "StrictHostKeyChecking=no",
                        "ubuntu@82.156.213.143", "df -h / | tail -1 | awk '{print $5}'"],
                       capture_output=True, text=True, timeout=30)
    if r.returncode == 0:
        usage = r.stdout.strip().rstrip("%")
        check("服务器磁盘", int(usage or 0) < 85, f"使用率 {usage}%")
    else:
        check("服务器磁盘", False, r.stderr[:80], "warn")
except Exception as e:
    check("服务器磁盘", False, f"{type(e).__name__}: {str(e)[:60]}", "warn")

# 汇总
crit = [r for r in results if r["level"] == "critical"]
warn = [r for r in results if r["level"] == "warn"]
report = {
    "time": datetime.now(CST).strftime("%Y-%m-%d %H:%M:%S"),
    "verdict": "健康" if not crit else ("严重" if any(r["item"] in ("页面 index.html", "数据新鲜度") for r in crit) else "需关注"),
    "passed": len(results) - len(crit) - len(warn),
    "critical": crit,
    "warn": warn,
    "results": results,
}
print(json.dumps(report, ensure_ascii=False, indent=1))
sys.exit(1 if crit else 0)
