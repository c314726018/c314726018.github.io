#!/usr/bin/env python3
# kChart labels 修复 + 油价卡排版填充(折算/金油比/迷你走势)
import os
B = "/Users/cuisiqi/WorkBuddy/2026-11-10-16-34-12/gold-site/"

# ===== 1) app.js:kChart 加 labels(category 对齐) =====
ap = B + "docs/app.js"
js = open(ap).read()
old = '''      var candles = bucketCandles(series, Math.max(2, Math.ceil(series.length / 24)));
      charts.k = new Chart(kc, {
          type: "candlestick",
          data: { datasets: [{ label: primary.symbol || "主力", data: candles,
            color: { up: "#d4380d", down: "#389e0d", unchanged: "#999" } }] },
          options: baseOpts(c, true)
        });'''
new = '''      var candles = bucketCandles(series, Math.max(2, Math.ceil(series.length / 24)));
      charts.k = new Chart(kc, {
          type: "candlestick",
          data: { labels: candles.map(function (_, i) { return "K" + (i + 1); }),
            datasets: [{ label: primary.symbol || "主力", data: candles.map(function (x, i) {
              return { x: i + 1, o: x.o, h: x.h, l: x.l, c: x.c }; }),
            color: { up: "#d4380d", down: "#389e0d", unchanged: "#999" } }] },
          options: baseOpts(c, true)
        });'''
assert js.count(old) == 1, "kChart"
js = js.replace(old, new, 1)
open(ap, "w").write(js)
print("kChart labels OK")

# ===== 2) build.py:油价卡排版填充 =====
p = B + "build.py"
src = open(p).read()

# 2a) 油价卡:油表后加 折算表 + 迷你走势 + 金油比
anchor = '本表不直接等于加油站价格。</div>'
# 查实际结尾文本
import re
m = re.search(r'(<div class="tfoot">布伦特 / WTI 为国际基准原油[^<]*(?:<[^>]+>[^<]*)*</div>)', src)
if not m:
    # 宽松定位
    m = re.search(r'(<div class="tfoot">[^<]*布伦特[^<]*</div>)', src)
assert m, "油价卡 tfoot 未命中"
TFOOT = m.group(1)

# 计算数据(服务端):折算元/升 + 金油比 + spark 点
calc = '''
      <!-- 油价衍生:折算/走势/金油比 -->
      <div class="oil-extra">
        <div class="oe-grid">
          <div class="dcard"><div class="dk">布伦特 折算人民币</div><div class="dv">{brent_l} <span style="font-size:12px">元/升</span></div><div class="dn">美元/桶 × 汇率 ÷ 158.97 升,原料口径</div></div>
          <div class="dcard"><div class="dk">WTI 折算人民币</div><div class="dv">{wti_l} <span style="font-size:12px">元/升</span></div><div class="dn">同口径折算,跨市场价差参考</div></div>
          <div class="dcard"><div class="dk">金油比</div><div class="dv">{gold_oil} <span style="font-size:12px">桶/盎司</span></div><div class="dn">1 盎司黄金可兑换的布伦特桶数</div></div>
        </div>
        <div class="oe-spark">
          <div class="dk" style="margin-bottom:6px">布伦特 近 60 个交易日收盘</div>
          {spark_svg}
        </div>
      </div>'''

# 服务端数据
usd = 0
for r in data.get("fx") or []:
    if r.get("code") == "USD":
        usd = r.get("cny") or 0
        break
oil_b = (data.get("oil") or {}).get("brent") or {}
oil_w = (data.get("oil") or {}).get("wti") or {}
last_b = oil_b.get("last") or 0
last_w = oil_w.get("last") or 0
bl = last_b * usd / 158.97 if usd else 0
wl = last_w * usd / 158.97 if usd else 0
gold_last = 0
for it in data.get("items") or []:
    if it.get("symbol") == "Au99.99":
        gold_last = it.get("last") or 0
        break
gold_oil = gold_last / (oil_b.get("last") or 1) * 31.1035 / usd if (oil_b.get("last") and usd) else 0
# 金油比:1 盎司黄金(31.1035g) 元价 = gold_last;1 桶布伦特元价 = last_b*usd;桶/盎司 = gold_last / (last_b*usd)
gold_oil = gold_last / (last_b * usd) if (last_b and usd) else 0

# spark SVG(布伦特 KL 60 根 close)
kl = data.get("klines") or {}
oil_kl = kl.get("OIL") or []
pts = oil_kl[-60:]
svg = ""
if len(pts) >= 5:
    vals = [x["c"] for x in pts]
    lo, hi = min(vals), max(vals)
    rng = (hi - lo) or 1
    W, H = 900, 90
    step = W / (len(vals) - 1)
    poly = " ".join(f"{i*step:.1f},{H-6-(v-lo)/rng*(H-12):.1f}" for i, v in enumerate(vals))
    up = vals[-1] >= vals[0]
    color = "#d4380d" if up else "#129b63"
    svg = (f'<svg viewBox="0 0 {W:.0f} {H}" style="width:100%;height:60px;display:block">'
           f'<polyline points="{poly}" fill="none" stroke="{color}" stroke-width="2"/></svg>'
           f'<div style="font-size:10.5px;color:var(--sub)">{esc(pts[0]["d"])} → {esc(pts[-1]["d"])} · {esc(fmt(vals[0]))} → {esc(fmt(vals[-1]))} 美元/桶</div>')

calc_html = calc.replace("{brent_l}", fmt(bl, 2)).replace("{wti_l}", fmt(wl, 2)).replace("{gold_oil}", fmt(gold_oil, 1)).replace("{spark_svg}", svg)

src = src.replace(TFOOT, TFOOT + calc_html, 1)

# 2b) oil-extra CSS(插在 deriv-grid 前)
src = src.replace("/* ============ 溢价衍生指标卡 ============ */",
'''.oe-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;margin:14px 0}
.oe-spark{background:var(--surface-2);border:1px solid var(--line);border-radius:10px;padding:12px 14px}
@media(max-width:720px){.oe-grid{grid-template-columns:1fr}}

/* ============ 溢价衍生指标卡 ============ */''', 1)

open(p, "w").write(src)
print("油价卡填充 OK")
