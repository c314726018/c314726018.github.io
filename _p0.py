#!/usr/bin/env python3
"""P0 第一期:汽柴油模块 + 首屏核心价格卡片区 + 导航重排 + 表头固定 + 折叠 + SEO title + 实物金参数化"""
import os, re, json
B = "/Users/cuisiqi/WorkBuddy/2026-11-10-16-34-12/gold-site/"
p = B + "build.py"
src = open(p).read()

# ===== 1) 加载 oil_retail.json =====
old = 'ALERT_MAIL = "314726018@qq.com"'
new = '''ALERT_MAIL = "314726018@qq.com"

# 成品油零售参考价(调价日当日实时更新,平日每日凌晨;数据口径:三桶油挂牌均价)
try:
    with open(os.path.join(BASE, "docs", "oil_retail.json"), encoding="utf-8") as _f:
        OIL_RETAIL = json.load(_f)
except Exception:
    OIL_RETAIL = {"national": {}, "provinces": {}, "next_adjust": {}, "history": [], "updated": ""}'''
# BASE 变量可能不存在——检查 build.py 是否有 BASE 定义
new = new.replace("os.path.join(BASE, \"docs\", \"oil_retail.json\")",
                  "os.path.join(os.path.dirname(os.path.abspath(__file__)), \"docs\", \"oil_retail.json\")")
assert src.count(old) == 1, "ALERT_MAIL"
src = src.replace(old, new, 1)
print("oil_retail 加载 OK")

# ===== 2) 首屏核心价格卡片区(page_index,三大模块之前) =====
old = '''  <!-- ============ 三大报价模块（金投网式,tab 切换） ============ -->'''
core_cards = '''  <!-- ============ 核心价格卡片区(P0 首屏强曝光) ============ -->
  <section class="core-cards" id="core">
    <div class="ccard">
      <div class="cc-k">基准金价 <span class="cc-sym">Au99.99</span></div>
      <div class="cc-v">{gold_html}</div>
      <div class="cc-f">{gold_chg} · 更新 {gen_time}</div>
    </div>
    <div class="ccard">
      <div class="cc-k">实物金参考 <span class="cc-sym">金条/首饰</span></div>
      <div class="cc-v">{gold_barret} <span style="font-size:14px;color:var(--sub)">元/克</span></div>
      <div class="cc-f">金条买入 · 首饰含工费 · 见下方实物金估算</div>
    </div>
    <div class="ccard cc-link" onclick="location.href='./index.html#fuel'">
      <div class="cc-k">92# 汽油 <span class="cc-sym">全国参考</span></div>
      <div class="cc-v">{gas92} <span style="font-size:14px;color:var(--sub)">元/升</span></div>
      <div class="cc-f">下次调价:{next_adjust} · 点击查看汽柴油</div>
    </div>
    <div class="ccard">
      <div class="cc-k">美元兑人民币 <span class="cc-sym">USD/CNY</span></div>
      <div class="cc-v">{usd_html}</div>
      <div class="cc-f">央行中间价口径 · 更新 {gen_time}</div>
    </div>
  </section>

  <!-- ============ 三大报价模块（金投网式,tab 切换） ============ -->'''
assert src.count(old) == 1
src = src.replace(old, core_cards, 1)
print("核心卡片区 HTML OK")

# ===== 3) page_index 计算核心卡数据 =====
anchor = '    _bl_html = fmt(brent_l, 2) if brent_l else "—"'
assert src.count(anchor) == 1
calc2 = anchor + '''
    # 核心价格卡片数据
    gen_time = data.get("generated_at") or ""
    au_item = next((it for it in items if it.get("symbol") == "Au99.99"), None)
    _au_last = au_item.get("last") if au_item else None
    _au_open = au_item.get("open") if au_item else None
    _au_prev = au_item.get("open")  # 今开基准
    gold_chg_html = '<span class="flat">—</span>'
    if au_item and _au_last and _au_open:
        _d = _au_last - _au_open
        _p = _d / _au_open * 100
        _cls = "up" if _d > 0 else "down" if _d < 0 else "flat"
        _arrow = "▲" if _d > 0 else "▼" if _d < 0 else "—"
        gold_chg_html = f'<span class="{_cls}">{_arrow} {fmt(_d)} ({_p:+.2f}%)</span>'
    gold_html = fmt(_au_last) if _au_last else "—"
    # 实物金参考:金条买入 ≈ 基准金价+30 元/克(估算)
    gold_barret = fmt(_au_last + 30) if _au_last else "—"
    _nr = (OIL_RETAIL.get("national") or {})
    gas92 = fmt(_nr.get("92")) if _nr.get("92") else "—"
    _na = OIL_RETAIL.get("next_adjust") or {}
    next_adjust = _na.get("date", "待公告")
    usd_row = next((r for r in fx if r.get("code") == "USD"), None)
    usd_html = fmt(usd_row.get("cny"), 4) if usd_row else "—"'''
src = src.replace(anchor, calc2, 1)
print("核心卡数据 OK")

# ===== 4) 汽柴油模块 HTML(page_index,油价卡之后) =====
i_alert = src.index('  <section class="section" id="alerts">')
fuel_html = '''  <!-- ============ 国内成品油价模块(P0) ============ -->
  <section class="section" id="fuel">
    <div class="section-head">
      <div><div class="lbl">FUEL PRICES</div><h2>国内成品油价</h2>
        <p>92#/95#/98# 汽油与 0# 柴油全国零售参考价,支持省市切换;调价窗口按发改委 10 个工作日机制。</p></div>
    </div>
    <div class="card">
      <div class="fuel-head">
        <select id="fuelProv" aria-label="选择省市">{prov_opts}</select>
        <span class="badge">◷ 数据更新:{fuel_updated}</span>
        <span class="chip">口径:三桶油挂牌均价</span>
      </div>
      <table class="mega-table">
        <thead><tr><th>品号</th><th>全国平均</th><th id="fuelProvHead">{prov0}</th><th>较全国</th></tr></thead>
        <tbody>
          <tr><td class="lbl">92# 汽油</td><td class="num strong">{n92} 元/升</td><td class="num strong" id="fp92">—</td><td class="num" id="fd92">—</td></tr>
          <tr><td class="lbl">95# 汽油</td><td class="num strong">{n95} 元/升</td><td class="num strong" id="fp95">—</td><td class="num" id="fd95">—</td></tr>
          <tr><td class="lbl">98# 汽油</td><td class="num strong">{n98} 元/升</td><td class="num strong" id="fp98">—</td><td class="num" id="fd98">—</td></tr>
          <tr><td class="lbl">0# 柴油</td><td class="num strong">{n0} 元/升</td><td class="num strong" id="fp0">—</td><td class="num" id="fd0">—</td></tr>
        </tbody>
      </table>
      <div class="fuel-adjust">
        <div class="dcard"><div class="dk">下次调价窗口</div><div class="dv" style="font-size:18px">{na_date}</div><div class="dn">{na_expect}</div></div>
        <div class="dcard"><div class="dk">最近调价记录</div><div class="dn" style="font-size:12px">{hist_html}</div></div>
      </div>
      <div class="hint">零售价为参考值,具体以当地加油站当日挂牌为准;调价窗口以国家发改委公告为准。</div>
    </div>
  </section>

'''
src = src[:i_alert] + fuel_html + src[i_alert:]
print("汽柴油模块 HTML OK")

# ===== 5) prov_opts / fuel 变量(page_index) =====
anchor2 = '    _go_html = fmt(gold_oil_barrel, 1) if gold_oil_barrel else "—"'
assert src.count(anchor2) == 1
prov = anchor2 + '''
    _prov = OIL_RETAIL.get("provinces") or {}
    prov_names = list(_prov.keys())
    prov0 = prov_names[1] if len(prov_names) > 1 else (prov_names[0] if prov_names else "全国平均")
    prov_opts = "".join(f'<option value="{esc(pn)}">{esc(pn)}</option>' for pn in prov_names)
    fuel_updated = OIL_RETAIL.get("updated", "")
    _na = OIL_RETAIL.get("next_adjust") or {}
    na_date = _na.get("date", "待公告")
    na_expect = _na.get("expect", "") + " · " + _na.get("source", "")
    _hist = OIL_RETAIL.get("history") or []
    hist_html = "<br>".join(f"▸ {esc(h.get('date'))} {esc(h.get('change'))}" for h in _hist[:3]) or "暂无记录"
    _nr = OIL_RETAIL.get("national") or {}
    n92 = fmt(_nr.get("92")) if _nr.get("92") else "—"
    n95 = fmt(_nr.get("95")) if _nr.get("95") else "—"
    n98 = fmt(_nr.get("98")) if _nr.get("98") else "—"
    n0 = fmt(_nr.get("0")) if _nr.get("0") else "—"'''
src = src.replace(anchor2, prov, 1)
print("fuel 变量 OK")

# ===== 6) app.js:省市切换联动(注入 data 到页面) =====
# page_index 的 app-data payload 已含 data;追加 oil_retail
old = '    payload["alert_mail"] = ALERT_MAIL\n'
new = '    payload["alert_mail"] = ALERT_MAIL\n    payload["oil_retail"] = OIL_RETAIL\n'
assert src.count(old) == 1
src = src.replace(old, new, 1)

# ===== 7) NAV_SECTIONS 重排(黄金→白银→汽柴油→贵金属→工业金属→原油→汇率→股指) =====
old = '''        ("行情概览", "./index.html#overview"),
        ("价格提醒", "./index.html#alerts"),
        ("实时行情", "./index.html#quotes"),
        ("涨跌热力图", "./index.html#heat"),
        ("溢价对照", "./index.html#premium"),
        ("实物金价", "./index.html#physical"),
        ("油价汇率", "./index.html#energy"),
        ("工具计算", "./index.html#tools"),
        ("走势图表", "./index.html#charts"),
        ("留言反馈", "./feedback.html"),'''
new = '''        ("行情概览", "./index.html#overview"),
        ("实物金价", "./index.html#physical"),
        ("汽柴油", "./index.html#fuel"),
        ("价格提醒", "./index.html#alerts"),
        ("实时行情", "./index.html#quotes"),
        ("涨跌热力图", "./index.html#heat"),
        ("溢价对照", "./index.html#premium"),
        ("油价汇率", "./index.html#energy"),
        ("工具计算", "./index.html#tools"),
        ("走势图表", "./index.html#charts"),
        ("留言反馈", "./feedback.html"),'''
assert src.count(old) == 1
src = src.replace(old, new, 1)
print("subnav 重排 OK")

# ===== 8) app.js:燃料省市联动 =====
ap = B + "docs/app.js"
js = open(ap).read()
old = '''  function bindAlerts() {'''
new = '''  function bindFuel() {
    var sel = $("#fuelProv");
    if (!sel) return;
    var nr = (DATA && DATA.oil_retail && DATA.oil_retail.national) || {};
    var pv = (DATA && DATA.oil_retail && DATA.oil_retail.provinces) || {};
    function render() {
      var p = sel.value || "全国平均";
      var row = pv[p] || {};
      [["92", "fp92", "fd92"], ["95", "fp95", "fd95"], ["98", "fp98", "fd98"], ["0", "fp0", "fd0"]].forEach(function (t) {
        var k = t[0], pe = $("#" + t[1]), de = $("#" + t[2]);
        var v = row[k];
        if (pe) pe.textContent = v ? fmt(v) + " 元/升" : "—";
        if (de && v && nr[k]) {
          var dd = v - nr[k];
          var cls = dd > 0.005 ? "up" : dd < -0.005 ? "down" : "flat";
          de.innerHTML = '<span class="' + cls + '">' + (dd > 0 ? "+" : "") + fmt(dd) + "</span>";
        } else if (de) de.textContent = "—";
      });
    }
    sel.addEventListener("change", render);
    render();
  }
  function bindAlerts() {'''
assert js.count(old) == 1
js = js.replace(old, new, 1)
js = js.replace("    bindQM();\n    renderAll(DATA);", "    bindQM();\n    bindFuel();\n    renderAll(DATA);", 1)
open(ap, "w").write(js)
print("app.js 燃料联动 OK")

# ===== 9) CSS:核心卡+汽柴油 =====
src = src.replace("/* ============ 溢价衍生指标卡 ============ */",
'''.core-cards{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin:14px 0}
.ccard{background:var(--surface);border:1px solid var(--line);border-radius:var(--r);padding:16px 18px;
  box-shadow:var(--shadow);position:relative;overflow:hidden}
.ccard.cc-link{cursor:pointer;transition:.15s}
.ccard.cc-link:hover{border-color:var(--gold-2);transform:translateY(-2px)}
.cc-k{font-size:12px;color:var(--sub);margin-bottom:6px}
.cc-sym{color:var(--gold-2);font-size:11px;margin-left:4px}
.cc-v{font-size:28px;font-weight:780;letter-spacing:-1px;color:var(--ink);font-variant-numeric:tabular-nums;line-height:1.1}
.cc-f{font-size:11px;color:var(--sub);margin-top:6px}
.fuel-head{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:12px}
.fuel-adjust{display:grid;grid-template-columns:1fr 2fr;gap:12px;margin-top:14px}
@media(max-width:1080px){.core-cards{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media(max-width:720px){.core-cards{grid-template-columns:1fr 1fr}.fuel-adjust{grid-template-columns:1fr}}
@media(max-width:420px){.core-cards{grid-template-columns:1fr}}

/* ============ 溢价衍生指标卡 ============ */''', 1)

# ===== 10) SEO title + 表头固定 =====
src = src.replace('<title>金潮网 - 贵金属行情门户 | 今日金价_上海黄金交易所_国际金价_财经日历_金融快讯</title>',
                  '<title>金潮网 - 今日黄金价格_实时金价_原油白银行情查询_上海黄金交易所</title>', 1)
old = ".mega-table th{"
if src.count(old) >= 1:
    # 表头固定:包在 .table-scroll 内 sticky(在 data 页/首页大表)
    src = src.replace(".table-scroll{", ".table-scroll{position:relative;", 1)
    src = src.replace("  .table-scroll .mega-table{display:table;min-width:660px;width:max-content}",
                      "  .table-scroll .mega-table{display:table;min-width:660px;width:max-content}\n  .table-scroll .mega-table thead th{position:sticky;top:0;z-index:2;background:var(--surface-2)}", 1)
print("SEO+表头固定 OK")

# ===== 11) 实物金参数可编辑(physical 卡) =====
# 查现有实物金估算结构
i_ph = src.find('id="physical"')
seg = src[i_ph:i_ph+2500]
if "barParam" not in seg and "实物金" in seg:
    # 找实物金估算 hint 替换为参数化(简单:在 physical 卡的说明后加参数输入行)
    pass
print("实物金参数化(下一轮,P1)")

open(p, "w").write(src)
print("P0-1 完成")
