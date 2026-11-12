#!/usr/bin/env python3
# 汇率表修列 + 溢价钯金行 + 衍生指标卡 + 快讯条目卡片化 + app.js renderFx 同步
import os, re
B = "/Users/cuisiqi/WorkBuddy/2026-11-10-16-34-12/gold-site/"
p = B + "build.py"
src = open(p).read()

# ===== 1) fx_rows:删反算列,加计价单位列(按行正则) =====
pat = re.compile(
    r"f'<td class=\"num\" data-label=\"人民币兑\">1 CNY = \{fmt\(r\.get\(\"per_cny\"\), 4\)\}</td>'")
n = len(pat.findall(src))
src = pat.sub(
    "f'<td class=\"unit\" data-label=\"计价单位\">{unit_note} 外币</td>'", src, 1)
src = src.replace("<thead><tr><th>币种</th><th>代码</th><th>兑人民币</th><th>人民币兑</th></tr></thead>",
                  "<thead><tr><th>币种</th><th>代码</th><th>兑人民币</th><th>计价单位</th></tr></thead>", 1)
open(p, "w").write(src)
print("汇率表修列 OK(命中 %d)" % n)

# ===== 2) metals_rows:钯金行保留(sge None 也显示) =====
src = open(p).read()
old = '        if x.get("sge") is None and x.get("premium_pct") is None:\n            continue  # 境内无报价,整行隐藏'
if old in src:
    src = src.replace(old,
        '        if x.get("sge") is None and x.get("premium_pct") is None and x.get("intl_cny") is None:\n            continue  # 境内与国际均无报价才隐藏(钯金保留国际折算)', 1)
    pat2 = re.compile(r"f'<td class=\"num\" data-label=\"境内报价\">\{fmt\(x\.get\(\"sge\"\)\)\} <span class=\"unit\">\{unit\}</span></td>'")
    src = pat2.sub(
        'f\'<td class="num" data-label="境内报价">{"—" if x.get("sge") is None else fmt(x.get("sge"))} <span class="unit">{unit}</span></td>\'', src, 1)
    open(p, "w").write(src)
    print("钯金行 OK")
else:
    print("钯金锚点未命中(检查)")

# ===== 3) 溢价区衍生指标卡 =====
src = open(p).read()
anchor = '<tbody id="metalsBody">{metals_rows(intl)}</tbody>\n      </table>'
if src.count(anchor) == 1 and "deriv-grid" not in src:
    deriv = anchor + '''
      <div class="deriv-grid">
        <div class="dcard"><div class="dk">金银比</div><div class="dv" id="drGoldSilver">—</div><div class="dn">XAU ÷ XAG,历史均值约 70-80,极端高低常对应情绪拐点</div></div>
        <div class="dcard"><div class="dk">金油比</div><div class="dv" id="drGoldOil">—</div><div class="dn">1 盎司黄金可兑换的布伦特原油桶数</div></div>
        <div class="dcard"><div class="dk">金铂比</div><div class="dv" id="drGoldPlat">—</div><div class="dn">XAU ÷ XPT,观察铂金相对强弱</div></div>
      </div>'''
    src = src.replace(anchor, deriv, 1)
    open(p, "w").write(src)
    print("衍生指标卡 OK")
else:
    print("衍生卡跳过(anchor=%d)" % src.count(anchor))

# ===== 4) 快讯条目卡片化 CSS =====
src = open(p).read()
if ".nl-item{position:relative" in src and ".nl-item{background" not in src:
    src = src.replace(
        ".nl-item{position:relative;padding:10px 0 12px;border-bottom:1px dashed var(--line-2)}",
        ".nl-item{position:relative;background:var(--surface);border:1px solid var(--line);border-radius:10px;"
        "padding:12px 14px 12px 16px;margin-bottom:10px;transition:.12s}"
        ".nl-item:hover{border-color:var(--gold-2);box-shadow:var(--shadow)}", 1)
    src = src.replace(".news-timeline{position:relative;padding-left:18px}",
                      ".news-timeline{position:relative;padding-left:0;display:flex;flex-direction:column;gap:10px}", 1)
    src = src.replace(".news-timeline::before{content:\"\";position:absolute;left:5px;top:6px;bottom:6px;width:2px;background:var(--line)}\n", "")
    src = src.replace(".nl-dot{position:absolute;left:-18px;top:16px;width:10px;height:10px;border-radius:50%;\n  background:var(--surface);border:2px solid var(--gold-2)}\n", "")
    src = src.replace(".nl-item:last-child{border-bottom:none}\n", "")
    open(p, "w").write(src)
    print("快讯卡片化 OK")
else:
    print("快讯卡片化跳过")

# ===== 5) 衍生卡 CSS =====
src = open(p).read()
if ".deriv-grid{" not in src:
    anchor = "/* ============ 全品种涨跌热力图 ============ */"
    css = (".pmod-b .mini-list .mini-sub{font-size:10.5px;color:var(--sub);line-height:1.6;margin-top:2px}\n\n"
           "/* ============ 溢价衍生指标卡 ============ */\n"
           ".deriv-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;margin-top:12px}\n"
           ".dcard{background:var(--surface-2);border:1px solid var(--line);border-radius:10px;padding:14px 16px}\n"
           ".dcard .dk{font-size:12px;color:var(--sub);margin-bottom:4px}\n"
           ".dcard .dv{font-size:24px;font-weight:750;color:var(--gold);font-variant-numeric:tabular-nums}\n"
           ".dcard .dn{font-size:11px;color:var(--sub);margin-top:4px;line-height:1.6}\n"
           "@media(max-width:720px){.deriv-grid{grid-template-columns:1fr}}\n\n"
           + anchor)
    assert src.count(anchor) == 1
    src = src.replace(anchor, css, 1)
    open(p, "w").write(src)
    print("衍生卡 CSS OK")
else:
    print("衍生卡 CSS 跳过")

# ===== 6) app.js:renderFx 同步(删第4列) + renderDeriv =====
ap = B + "docs/app.js"
js = open(ap).read()
m = re.search(r"function renderFx\(d\) \{.*?\n  \}", js, re.S)
if m:
    old_fx = m.group(0)
    # 替换其中第4列 td 与表头无关;直接重建 renderFx
    new_fx = '''function renderFx(d) {
    var tb = $("#fxBody");
    if (!tb) return;
    tb.innerHTML = (d.fx || []).map(function (r) {
      var unitNote = r.unit === 100 ? "100" : "1";
      return "<tr>" +
        '<td class="lbl" data-label="币种">' + esc(r.name) + "</td>" +
        '<td class="sym" data-label="代码">' + esc(r.code) + "</td>" +
        '<td class="num strong" data-label="兑人民币">' + unitNote + " " + esc(r.code) + " = " + fmt(r.cny, 4) + "</td>" +
        '<td class="unit" data-label="计价单位">' + unitNote + " 外币</td>" +
        "</tr>";
    }).join("");
  }'''
    js = js.replace(old_fx, new_fx, 1)
    print("renderFx 同步 OK")

# renderDeriv(挂到 renderAll)
if "function renderDeriv" not in js:
    deriv_fn = '''  function renderDeriv(d) {
    var intl = d.intl || {};
    var xau = intl.xau_usd, xag = (intl.metals || {}).silver || {}, xpt = (intl.metals || {}).platinum || {};
    var oil = ((d.oil || {}).brent || {}).last;
    var g1 = $("#drGoldSilver"), g2 = $("#drGoldOil"), g3 = $("#drGoldPlat");
    if (g1 && xau && xag.intl_usd) g1.textContent = fmt(xau / xag.intl_usd, 1);
    if (g2 && xau && oil) g2.textContent = fmt(xau / oil, 1);
    if (g3 && xau && xpt.intl_usd) g3.textContent = fmt(xau / xpt.intl_usd, 1);
  }
  function renderAll(d) {'''
    js = js.replace("  function renderAll(d) {", deriv_fn, 1)
    js = js.replace("    renderOverview(d);\n    renderQM(d);", "    renderOverview(d);\n    renderQM(d);\n    renderDeriv(d);", 1)
    open(ap, "w").write(js)
    print("renderDeriv OK")
else:
    print("renderDeriv 已存在")
