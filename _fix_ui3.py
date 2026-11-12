#!/usr/bin/env python3
# 终极修复 v3:分步写盘、宽松匹配
import os, re
B = "/Users/cuisiqi/WorkBuddy/2026-11-10-16-34-12/gold-site/"
p = B + "build.py"

def save(src):
    open(p, "w").write(src)

# ===== 1) canvas 强制尺寸修复 =====
src = open(p).read()
n1 = src.count(".tq-chart canvas{width:100%!important;height:100%!important}")
src = src.replace(".tq-chart canvas{width:100%!important;height:100%!important}",
                  ".tq-chart canvas{display:block}")
src = src.replace(".tq-subchart canvas{width:100%!important;height:100%!important}",
                  ".tq-subchart canvas{display:block}")
src = src.replace("#fsOverlay canvas{width:100%!important;height:100%!important}",
                  "#fsOverlay canvas{display:block}")
save(src)
print("步骤1 canvas 修复 OK", n1)

# ===== 2) 覆盖块正确包裹 =====
src = open(p).read()
old_head = """/* ============ 移动端适配覆盖(置于所有主定义之后,确保生效) ============ */
  .portal-main table,.portal table{min-width:0}"""
if src.count(old_head) == 1:
    src = src.replace(old_head, old_head.replace(
        "确保生效) ============ */\n",
        "确保生效) ============ */\n@media(max-width:720px){\n"), 1)
    old_tail = "  .tq-body{padding:12px 12px}\n@media(max-width:900px) and (min-width:721px){"
    assert src.count(old_tail) == 1
    src = src.replace(old_tail, "  .tq-body{padding:12px 12px}\n}\n@media(max-width:900px) and (min-width:721px){", 1)
    save(src)
    print("步骤2 覆盖块包裹 OK")
else:
    print("步骤2 跳过(已包裹或结构不同):", src.count(old_head))

# ===== 3) 热力图 + 快讯 CSS =====
src = open(p).read()
if ".heat-grid{" not in src:
    anchor = "/* ============ 移动端适配覆盖"
    NEWCSS = '''/* ============ 全品种涨跌热力图 ============ */
.heat-grid{display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:8px}
.heat{display:flex;flex-direction:column;gap:3px;padding:10px 12px;border-radius:8px;text-decoration:none;
  border:1px solid var(--line);background:var(--surface);transition:.12s;line-height:1.3}
.heat:hover{transform:translateY(-2px);box-shadow:var(--shadow)}
.heat .h-n{font-size:11.5px;color:var(--ink-2);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.heat .h-v{font-size:13.5px;font-weight:750;font-variant-numeric:tabular-nums}
.heat.up .h-v{color:var(--up)}
.heat.down .h-v{color:var(--down)}
.heat.flat .h-v{color:var(--sub)}
.heat.up{background:color-mix(in srgb,var(--up) calc(var(--lv,1)*6%),var(--surface));border-color:color-mix(in srgb,var(--up) calc(var(--lv,1)*18%),var(--line))}
.heat.down{background:color-mix(in srgb,var(--down) calc(var(--lv,1)*6%),var(--surface));border-color:color-mix(in srgb,var(--down) calc(var(--lv,1)*18%),var(--line))}
.heat.lv1{--lv:1}.heat.lv2{--lv:2}.heat.lv3{--lv:3}.heat.lv4{--lv:4}
.heat.up.lv4{background:color-mix(in srgb,var(--up) 22%,var(--surface))}
.heat.down.lv4{background:color-mix(in srgb,var(--down) 22%,var(--surface))}

/* ============ 快讯页:头条卡/时间轴/过滤 ============ */
.news-hero{border:1px solid var(--line);border-left:3px solid var(--gold);border-radius:var(--r-sm);
  background:var(--surface);padding:16px 18px;margin-bottom:16px}
.news-hero .nh-top{display:flex;align-items:center;gap:10px;margin-bottom:8px;flex-wrap:wrap}
.news-hero .nh-time{font-size:11.5px;color:var(--sub)}
.news-hero .nh-title{font-size:17px;font-weight:750;color:var(--ink);margin-bottom:8px;line-height:1.5}
.news-hero .nh-text{font-size:13.5px;color:var(--ink-2);line-height:1.85}
.news-hero .nh-foot{margin-top:10px;padding-top:10px;border-top:1px dashed var(--line-2);font-size:11px;color:var(--sub)}
.news-filter{display:flex;gap:6px;flex-wrap:wrap}
.fbtn{font-size:11.5px;color:var(--sub);padding:4px 12px;border-radius:14px;border:1px solid var(--line);
  background:var(--surface);cursor:pointer;transition:.12s}
.fbtn:hover{color:var(--gold);border-color:var(--gold-2)}
.fbtn.on{color:#fff;background:var(--gold);border-color:var(--gold);font-weight:650}
.news-timeline{position:relative;padding-left:18px}
.news-timeline::before{content:"";position:absolute;left:5px;top:6px;bottom:6px;width:2px;background:var(--line)}
.nl-item{position:relative;padding:10px 0 12px;border-bottom:1px dashed var(--line-2)}
.nl-item:last-child{border-bottom:none}
.nl-dot{position:absolute;left:-18px;top:16px;width:10px;height:10px;border-radius:50%;
  background:var(--surface);border:2px solid var(--gold-2)}
.nl-time{font-size:11px;color:var(--sub);font-variant-numeric:tabular-nums;margin-bottom:4px}
.nl-head{display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin-bottom:5px}
.nl-tag{font-size:10.5px;padding:2px 8px;border-radius:10px;font-weight:650;white-space:nowrap;flex:0 0 auto}
.nl-tag.t-贵金属{background:var(--gold-soft);color:var(--gold-ink)}
.nl-tag.t-宏观央行{background:color-mix(in srgb,#4a90e2 14%,transparent);color:#2f6fd0}
.nl-tag.t-能源{background:color-mix(in srgb,#e67e22 14%,transparent);color:#c9661a}
.nl-tag.t-外汇{background:color-mix(in srgb,#16a085 14%,transparent);color:#118a6f}
.nl-tag.t-股市{background:color-mix(in srgb,#8e44ad 13%,transparent);color:#7d3ca8}
.nl-tag.t-综合{background:var(--surface-2);color:var(--sub)}
.nl-title{font-size:14px;font-weight:700;color:var(--ink);line-height:1.5}
.nl-text{font-size:12.5px;color:var(--ink-2);line-height:1.8;margin-bottom:6px}
.nl-meta{font-size:10.5px;color:var(--sub)}
.news-empty{padding:20px;text-align:center;color:var(--sub);font-size:12.5px}
@media(max-width:720px){
  .heat-grid{grid-template-columns:repeat(3,minmax(0,1fr))}
  .news-hero{padding:13px 14px}
  .news-hero .nh-title{font-size:15px}
}

/* ============ 移动端适配覆盖'''
    assert src.count(anchor) == 1
    src = src.replace(anchor, NEWCSS, 1)
    save(src)
    print("步骤3 热力图+快讯 CSS OK")
else:
    print("步骤3 跳过(已存在)")

# ===== 4) 头条 title/text 去重(JS) =====
src = open(p).read()
pat = re.compile(r"'<div class=\"nh-text\">' \+ esc\(top\.get\(\"text\"\)\) \+ '</div>'")
m = pat.findall(src)
if m:
    src = pat.sub(
        "'<div class=\"nh-text\">' + esc((top.get(\"text\") or \"\").split(top.get(\"title\") or \"\\u0000\")[0].replace(top.get(\"title\") or \"\", \"\").trim() || top.get(\"text\")) + '</div>'",
        src, 1)
    save(src)
    print("步骤4 头条去重 OK")
else:
    print("步骤4 跳过(模式不匹配):", len(m))

# ===== 5) 右栏盒子加量 =====
src = open(p).read()
if ".mini-sub{" not in src:
    # 5a 快讯 6→10 + 简介
    src = src.replace('news = (data.get("news") or [])[:6]', 'news = (data.get("news") or [])[:10]', 1)
    src = src.replace(
        "f'<a href=\"./news.html\">{esc(n.get(\"title\"))}</a></li>'",
        "f'<a href=\"./news.html\">{esc(n.get(\"title\"))}</a>'\n            f'<div class=\"mini-sub\">{esc((n.get(\"text\") or \"\")[:64])}…</div></li>'", 1)
    # 5b 日历 5→7 + 说明
    src = src.replace(
        "f'<li><span class=\"t\">{esc(d[0][5:10])}</span><a href=\"./calendar.html\">{esc(d[1])}</a></li>'",
        "f'<li><span class=\"t\">{esc(d[0][5:10])}</span><a href=\"./calendar.html\">{esc(d[1])}</a>'\n        f'<div class=\"mini-sub\">{esc(d[3])}</div></li>'", 1)
    src = src.replace("for d in ECON_EVENTS[:5])", "for d in ECON_EVENTS[:7])", 1)
    # 5c 学院 5→6 + 首段简介
    src = src.replace(
        "f'<li><a href=\"./academy.html#articles\">{esc(a[\"h\"])}</a></li>'",
        "f'<li><a href=\"./academy.html#articles\">{esc(a[\"h\"])}</a>'\n        f'<div class=\"mini-sub\">{esc(a[\"p\"][0][:56])}…</div></li>'", 1)
    src = src.replace("for a in ACAD_ARTICLES[:5])", "for a in ACAD_ARTICLES[:6])", 1)
    # 5d 术语 5→8 + 释义加长
    src = src.replace('esc(g["d"][:26])', 'esc(g["d"][:40])', 1)
    src = src.replace("for g in GLOSSARY[:5])", "for g in GLOSSARY[:8])", 1)
    # 5e mini-sub 样式
    src = src.replace(
        ".pmod-b .mini-list a{display:block}",
        ".pmod-b .mini-list a{display:block}\n.pmod-b .mini-list .mini-sub{font-size:10.5px;color:var(--sub);line-height:1.6;margin-top:2px}", 1)
    save(src)
    print("步骤5 右栏加量 OK")
else:
    print("步骤5 跳过(已存在)")
print("全部完成")
