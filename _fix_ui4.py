#!/usr/bin/env python3
# 步骤4+5 修正版
import os, re
B = "/Users/cuisiqi/WorkBuddy/2026-11-10-16-34-12/gold-site/"
p = B + "build.py"

# ===== 4) 头条 title/text 去重 =====
src = open(p).read()
pat = re.compile(r"'<div class=\"nh-text\">' \+ esc\(top\.get\(\"text\"\)\) \+ '</div>'")
def repl(m):
    js = ('\'<div class="nh-text">\' + esc(function(t, x){'
          'var s = x || "";'
          'if (t && s.indexOf(t) === 0) s = s.slice(t.length);'
          'return s.trim() || x;'
          '}(top.get("title"), top.get("text"))) + \'</div>\'')
    return js
src2, n = pat.subn(repl, src, 1)
if n:
    open(p, "w").write(src2)
    print("步骤4 头条去重 OK")
else:
    print("步骤4 跳过(未命中)")

# ===== 5) 右栏盒子加量 =====
src = open(p).read()
if ".mini-sub{" not in src:
    src = src.replace('news = (data.get("news") or [])[:6]', 'news = (data.get("news") or [])[:10]', 1)
    src = src.replace(
        "f'<a href=\"./news.html\">{esc(n.get(\"title\"))}</a></li>'",
        "f'<a href=\"./news.html\">{esc(n.get(\"title\"))}</a>'\n            f'<div class=\"mini-sub\">{esc((n.get(\"text\") or \"\")[:64])}…</div></li>'", 1)
    src = src.replace(
        "f'<li><span class=\"t\">{esc(d[0][5:10])}</span><a href=\"./calendar.html\">{esc(d[1])}</a></li>'",
        "f'<li><span class=\"t\">{esc(d[0][5:10])}</span><a href=\"./calendar.html\">{esc(d[1])}</a>'\n        f'<div class=\"mini-sub\">{esc(d[3])}</div></li>'", 1)
    src = src.replace("for d in ECON_EVENTS[:5])", "for d in ECON_EVENTS[:7])", 1)
    src = src.replace(
        "f'<li><a href=\"./academy.html#articles\">{esc(a[\"h\"])}</a></li>'",
        "f'<li><a href=\"./academy.html#articles\">{esc(a[\"h\"])}</a>'\n        f'<div class=\"mini-sub\">{esc(a[\"p\"][0][:56])}…</div></li>'", 1)
    src = src.replace("for a in ACAD_ARTICLES[:5])", "for a in ACAD_ARTICLES[:6])", 1)
    src = src.replace('esc(g["d"][:26])', 'esc(g["d"][:40])', 1)
    src = src.replace("for g in GLOSSARY[:5])", "for g in GLOSSARY[:8])", 1)
    src = src.replace(
        ".pmod-b .mini-list a{display:block}",
        ".pmod-b .mini-list a{display:block}\n.pmod-b .mini-list .mini-sub{font-size:10.5px;color:var(--sub);line-height:1.6;margin-top:2px}", 1)
    open(p, "w").write(src)
    print("步骤5 右栏加量 OK")
else:
    print("步骤5 跳过")
print("完成")
