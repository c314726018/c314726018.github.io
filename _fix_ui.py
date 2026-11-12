#!/usr/bin/env python3
# 大修复:图表尺寸反模式 / 热力图+快讯CSS / max-content泄漏 / 头条去重 / 右栏加量 / 对齐
import os
B = "/Users/cuisiqi/WorkBuddy/2026-11-10-16-34-12/gold-site/"
p = B + "build.py"
src = open(p).read()

# ===== 1) 删除破坏 Chart.js responsive 的 canvas 强制尺寸 =====
old = ".tq-chart canvas{width:100%!important;height:100%!important}"
assert src.count(old) == 1
src = src.replace(old, ".tq-chart canvas{display:block}", 1)
old2 = ".tq-subchart canvas{width:100%!important;height:100%!important}"
assert src.count(old2) == 1
src = src.replace(old2, ".tq-subchart canvas{display:block}", 1)
# fsOverlay canvas 同理
src = src.replace("#fsOverlay canvas{width:100%!important;height:100%!important}",
                  "#fsOverlay canvas{display:block}", 1)
print("canvas 强制尺寸修复 OK")

# ===== 2) max-content 泄漏修复:覆盖块里泄漏的 table-scroll 系列重新包进 media =====
# 找到泄漏段(顶层 .table-scroll 系列),整段包进 @media(max-width:720px)
leak_start = src.find("  /* 大行情表(无 data-label)在手机上保持表格模式 + 横向滚动(金融门户惯例) */")
if leak_start == -1:
    leak_start = src.find("/* 大行情表(无 data-label)")
assert leak_start != -1, "找不到泄漏段"
leak_end = src.find("@media(max-width:420px)", leak_start)
# 泄漏段范围:从注释到下一个顶层块(420px 媒体)之间的 } 平衡点
# 简化:该段最后一条是 .tq-body{padding:12px 12px}(后跟 })
tail_marker = ".tq-body{padding:12px 12px}"
tail_i = src.find(tail_marker, leak_start)
assert tail_i != -1
seg_end = src.index("}", tail_i) + 1
leaked = src[leak_start:seg_end]
# 泄漏段包进 media(替换其中的外层结构问题)
wrapped = ("@media(max-width:720px){\n" + leaked.replace("\n\n@media", "\n") + "\n}\n")
src = src[:leak_start] + wrapped + src[seg_end:]
print("max-content 泄漏修复 OK(已包进 720px)")

open(p, "w").write(src)

# ===== 3) 热力图 + 快讯 CSS(插在移动覆盖块注释前) =====
src = open(p).read()
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
.nl-tag{font-size:10.5px;padding:2px 8px;border-radius:10px;font-weight:650;white-space:nowrap}
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

/* ============ 右栏加量/快讯列表更饱满 ============ */
.pmod-b .mini-list li{padding:7px 2px;line-height:1.65}
.pmod-b .mini-list .t{margin-right:8px}
.pmod-b .mini-list a{display:block}

/* ============ 移动端适配覆盖'''
assert src.count(anchor) == 1
src = src.replace(anchor, NEWCSS, 1)
open(p, "w").write(src)
print("热力图+快讯 CSS OK")
