#!/usr/bin/env python3
# 三模块对齐:labels null→索引数组(图表无线真因) / 外汇模块信息面板填满高度 / 工具行单行压缩
import os
B = "/Users/cuisiqi/WorkBuddy/2026-11-10-16-34-12/gold-site/"

# ===== 1) app.js:drawQChart labels null → 索引数组(lineChart 有 labels 正常,统一) =====
p = B + "docs/app.js"
js = open(p).read()
old = '      ok1 = drawQChart("qm1Chart", null, x.it.series, cls1, true);'
new = '      ok1 = drawQChart("qm1Chart", x.it.series.map(function (_, i) { return i + 1; }), x.it.series, cls1, true);'
assert js.count(old) == 1, "m1 labels"
js = js.replace(old, new, 1)
# 模块3 走势线同理
old3 = '      ok3 = drawQChart("qm3Chart", null, kl3.map(function (x) { return x.c; }), ocls);'
new3 = '      ok3 = drawQChart("qm3Chart", kl3.map(function (x) { return (x.d || "").slice(5); }), kl3.map(function (x) { return x.c; }), ocls);'
assert js.count(old3) == 1, "m3 labels"
js = js.replace(old3, new3, 1)
open(p, "w").write(js)
print("labels 修复 OK")

# ===== 2) build.py:外汇模块信息面板(占满图区高度) + 工具行压缩 =====
p2 = B + "build.py"
src = open(p2).read()

# 2a) qm2 结构:chart 区改信息面板
old2 = '''        <div class="tq-chart" id="qm2ChartBox" style="display:none"><canvas id="qm2Chart" height="132"></canvas></div>
        <div class="tq-spark" id="qm2Spark"></div>'''
new2 = '''        <div class="tq-chart tq-fxinfo">
          <div class="fxline"><span class="fxk">美元指数 DXY</span><span class="fxv" id="qm2Dxy">—</span><span class="fxchg" id="qm2DxyChg">—</span></div>
          <div class="fxline sub"><span>日内高 <b id="qm2DxyH">—</b></span><span>日内低 <b id="qm2DxyL">—</b></span></div>
          <div class="fxline sub"><span>1 CNY ≈ <b id="qm2Inv">—</b> USD</span></div>
          <div class="fxnote">外汇为银行中间价口径,无分时/K线数据;切换上方币种查看对应牌价</div>
        </div>'''
assert src.count(old2) == 1, "qm2 chart"
src = src.replace(old2, new2, 1)

# 2b) CSS:tq-fxinfo + 工具行单行压缩
old_css = '''.tq-chart{height:132px;padding:2px 8px 8px;position:relative}
.tq-chart canvas{display:block}'''
new_css = '''.tq-chart{height:132px;padding:2px 8px 8px;position:relative}
.tq-chart canvas{display:block}
.tq-fxinfo{display:flex;flex-direction:column;justify-content:center;gap:8px;background:var(--surface-2)}
.fxline{display:flex;align-items:baseline;gap:10px;font-size:13px;color:var(--ink)}
.fxline.sub{font-size:11.5px;color:var(--sub)}
.fxline.sub b{color:var(--ink);font-variant-numeric:tabular-nums}
.fxk{font-size:12px;color:var(--sub)}
.fxv{font-size:20px;font-weight:750;color:var(--ink);font-variant-numeric:tabular-nums}
.fxchg{font-size:12px;font-weight:650}
.fxchg.up{color:var(--up)}
.fxchg.down{color:var(--down)}
.fxnote{font-size:10.5px;color:var(--sub);line-height:1.5;border-top:1px dashed var(--line-2);padding-top:6px}'''
assert src.count(old_css) == 1
src = src.replace(old_css, new_css, 1)

# 工具行压缩(单行)
src = src.replace(".tq-tools{display:flex;align-items:center;gap:10px;flex-wrap:wrap;padding:6px 12px 8px;border-top:1px dashed var(--line-2)}",
                  ".tq-tools{display:flex;align-items:center;gap:8px;flex-wrap:wrap;padding:5px 10px 7px;border-top:1px dashed var(--line-2)}", 1)
src = src.replace(".tq-tools a{font-size:11px;color:var(--sub);padding:3px 8px;border-radius:6px;cursor:pointer;transition:.12s}",
                  ".tq-tools a{font-size:10.5px;color:var(--sub);padding:2px 6px;border-radius:6px;cursor:pointer;transition:.12s;white-space:nowrap}", 1)
src = src.replace('.tq-tools .tt-g::before{content:attr(data-g);font-size:10px;color:var(--sub);margin-right:2px;letter-spacing:1px}',
                  '.tq-tools .tt-g::before{content:attr(data-g);font-size:9.5px;color:var(--sub);margin-right:1px;letter-spacing:.5px}', 1)
open(p2, "w").write(src)
print("外汇面板 + 工具行压缩 OK")

# ===== 3) app.js:renderQM 模块2 填信息面板(替换旧 spark 逻辑) =====
js = open(p).read()
old3 = '''    var dxy = ((d.extra || {}).dxy) || null;
    var sp2 = $("#qm2Spark");
    if (sp2) {
      if (dxy) {
        var dch = chgPair(dxy.last, dxy.prev);
        var dcls = dch ? dch.cls : "flat";
        sp2.innerHTML = '<div class="tq-sub" style="text-align:left">美元指数&nbsp;&nbsp;<b style="font-size:16px">' +
          fmt(dxy.last) + '</b> <span class="' + dcls + '">' +
          (dch ? (dch.d > 0 ? "▲ +" : "▼ ") + fmt(dch.pct) + "%" : "—") +
          '</span><br><span style="opacity:.7">高 ' + fmt(dxy.high) + " · 低 " + fmt(dxy.low) + "</span></div>";
      } else {
        sp2.innerHTML = "";
      }
    }'''
new3 = '''    var dxy = ((d.extra || {}).dxy) || null;
    var dE = $("#qm2Dxy"), cE = $("#qm2DxyChg"), hE = $("#qm2DxyH"), lE = $("#qm2DxyL");
    if (dxy && dE) {
      _set("qm2Dxy", fmt(dxy.last));
      var dch = chgPair(dxy.last, dxy.prev);
      if (cE) {
        cE.className = "fxchg " + (dch ? dch.cls : "flat");
        cE.textContent = dch ? (dch.d > 0 ? "▲ +" : "▼ ") + fmt(dch.pct) + "%" : "—";
      }
      _set("qm2DxyH", fmt(dxy.high)); _set("qm2DxyL", fmt(dxy.low));
    }
    var inv = $("#qm2Inv");
    if (inv && fx) inv.textContent = fmt(fx.per_cny, 4);'''
assert js.count(old3) == 1, "qm2 render"
js = js.replace(old3, new3, 1)
open(p, "w").write(js)
print("renderQM 模块2 OK")
