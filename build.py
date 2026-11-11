#!/usr/bin/env python3
"""
读取 data.json，渲染静态站点 docs/index.html（零依赖）。

输出：docs/index.html —— 富功能响应式页面（概览卡片 / 行情表 / 分时·K线·对比图 /
价格提醒 / 科普SEO内容 / 广告位），自托管 Chart.js，适配手机·平板·桌面。
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "data.json")
OUT = os.path.join(HERE, "docs", "index.html")


def load_data():
    try:
        with open(CACHE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"generated_at": "", "source": "上海黄金交易所 (SGE)", "items": [], "primary": {}, "intl": {}}


CSS = """
:root{
  --bg:#f6f7f9; --card:#ffffff; --ink:#1f2329; --sub:#6b7280; --line:#e7e9ee;
  --gold:#b8860b; --up:#d4380d; --down:#389e0d; --accent:#2f6fed; --chip:#eef2ff;
}
html.dark{
  --bg:#0f1115; --card:#171a21; --ink:#e5e7eb; --sub:#9aa3af; --line:#262b36;
  --gold:#e0b341; --up:#ff6b4a; --down:#5fd07a; --accent:#6ea0ff; --chip:#1b2333;
}
*{box-sizing:border-box}
body{margin:0;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif;
  background:var(--bg);color:var(--ink);line-height:1.6;-webkit-text-size-adjust:100%}
a{color:var(--accent);text-decoration:none}
.wrap{max-width:980px;margin:0 auto;padding:0 16px 64px}
header{position:sticky;top:0;z-index:20;background:var(--card);border-bottom:1px solid var(--line)}
.bar{max-width:980px;margin:0 auto;padding:12px 16px;display:flex;align-items:center;gap:10px}
.bar h1{font-size:17px;margin:0;flex:1}
.bar .dot{width:8px;height:8px;border-radius:50%;background:var(--down);display:inline-block;margin-right:6px}
#themeBtn{background:var(--chip);border:1px solid var(--line);color:var(--ink);border-radius:8px;
  padding:6px 10px;font-size:13px;cursor:pointer}
.hero{padding:22px 0 6px}
.ov-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin-top:10px}
.ov{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:14px}
.ov .k{color:var(--sub);font-size:12px}
.ov-val{font-size:24px;font-weight:700;font-variant-numeric:tabular-nums;margin-top:4px}
.ov-val.up{color:var(--up)} .ov-val.down{color:var(--down)}
.ov .u{color:var(--sub);font-size:12px;margin-left:3px}
.ov .t{color:var(--sub);font-size:11px;margin-top:4px}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:16px;margin:16px 0;
  box-shadow:0 1px 3px rgba(0,0,0,.03)}
.card h2{font-size:15px;margin:0 0 12px;display:flex;align-items:center;gap:8px}
.card h2 .tag{font-size:11px;color:var(--sub);font-weight:400}
table{width:100%;border-collapse:collapse;font-size:14px}
th,td{padding:10px 8px;text-align:right;border-bottom:1px solid var(--line)}
th:first-child,td:first-child,th:nth-child(2),td:nth-child(2){text-align:left}
th{color:var(--sub);font-weight:600;font-size:12px}
.lbl{font-weight:600} .sym{color:var(--sub);font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:12px}
.num{font-variant-numeric:tabular-nums} .strong{font-weight:700;color:var(--gold);font-size:15px}
.up{color:var(--up)} .down{color:var(--down)} .unit{color:var(--sub);font-size:12px}
.charts{display:grid;grid-template-columns:1fr 1fr;gap:16px}
.chart-box{height:260px;position:relative}
.chart-box.full{grid-column:1/-1}
@media(max-width:720px){.charts{grid-template-columns:1fr}.chart-box{height:230px}}
.alert-row{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:12px}
.alert-row select,.alert-row input{background:var(--bg);border:1px solid var(--line);color:var(--ink);
  border-radius:8px;padding:8px 10px;font-size:14px}
.alert-row input{width:120px}
#alertAdd{background:var(--accent);color:#fff;border:none;border-radius:8px;padding:8px 14px;font-size:14px;cursor:pointer}
#notifyBtn{background:var(--chip);border:1px solid var(--line);color:var(--ink);border-radius:8px;padding:8px 12px;font-size:13px;cursor:pointer}
#alertList{list-style:none;padding:0;margin:0;display:flex;flex-direction:column;gap:8px}
#alertList li{display:flex;align-items:center;gap:8px;background:var(--bg);border:1px solid var(--line);
  border-radius:8px;padding:8px 12px;font-size:14px}
.alert-empty{color:var(--sub);font-size:13px}
.a-sym{font-weight:600} .a-cond{color:var(--sub)} .a-val{font-variant-numeric:tabular-nums}
.a-del{margin-left:auto;background:none;border:none;color:var(--sub);cursor:pointer;font-size:14px}
.sub{margin-top:14px;display:flex;flex-wrap:wrap;gap:8px;align-items:center}
.sub input{flex:1;min-width:200px;background:var(--bg);border:1px solid var(--line);color:var(--ink);
  border-radius:8px;padding:8px 10px;font-size:14px}
.sub button{background:var(--accent);color:#fff;border:none;border-radius:8px;padding:8px 14px;font-size:14px;cursor:pointer}
#subNote{width:100%;color:var(--sub);font-size:12px;margin-top:4px}
.ad-slot{margin:16px 0;border:1px dashed var(--line);border-radius:12px;padding:14px;text-align:center;
  color:var(--sub);font-size:12px;background:var(--card)}
.prose h3{font-size:15px;margin:18px 0 6px}
.prose p{color:var(--ink);font-size:14px;margin:6px 0}
.prose .muted{color:var(--sub)}
.disclaimer{color:var(--sub);font-size:12px;margin-top:10px;line-height:1.7}
footer{color:var(--sub);font-size:12px;text-align:center;margin-top:28px}
@media(max-width:640px){
  table,thead,tbody,th,td,tr{display:block}
  thead{display:none}
  tr{border:1px solid var(--line);border-radius:10px;margin-bottom:10px;padding:6px 10px;background:var(--card)}
  td{display:flex;justify-content:space-between;padding:6px 4px;border:none;text-align:right}
  td::before{content:attr(data-label);color:var(--sub);font-size:12px;font-weight:600;text-align:left}
  td.lbl,td.sym{text-align:left}
}
"""

FAQ = [
    {"q": "今日金价是多少？", "a": "本页实时展示上海黄金交易所 Au99.99 等合约最新价，以及国际现货黄金（XAU/USD）折算人民币后的价格与国内溢价，数据每次构建自动刷新。"},
    {"q": "Au99.99 是什么？", "a": "Au99.99 是上海黄金交易所纯度 99.99% 的现货黄金合约，是国内黄金现货的基准报价，单位元/克。"},
    {"q": "国内溢价怎么算？", "a": "国内溢价 = (SGE Au99.99 元/克 − 国际金价折算元/克) ÷ 国际金价折算元/克 × 100%，反映国内供需与税费带来的价差。"},
    {"q": "账户黄金和实物黄金有什么区别？", "a": "账户黄金（如 SGE 现货合约、银行积存金）不提取实物、交易便捷；实物黄金（金条、金币）需考虑加工费、保管与回购价差。"},
]


def render(data):
    items = data.get("items", [])
    intl = data.get("intl", {})
    gen = data.get("generated_at", "")
    src = data.get("source", "上海黄金交易所 (SGE)")
    prim = data.get("primary") or {}

    faq_ld = {
        "@context": "https://schema.org", "@type": "FAQPage",
        "mainEntity": [{"@type": "Question", "name": f["q"],
                       "acceptedAnswer": {"@type": "Answer", "text": f["a"]}} for f in FAQ]
    }
    faq_html = "".join(
        f'<div class="prose"><h3>{f["q"]}</h3><p>{f["a"]}</p></div>' for f in FAQ)

    # 提醒合约下拉
    sym_opts = "".join(f'<option value="{it["symbol"]}">{it["label"]} {it["symbol"]}</option>' for it in items)

    data_json = json.dumps(data, ensure_ascii=False)

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>今日金价_实时黄金价格_上海黄金交易所行情 | 国内溢价</title>
<meta name="description" content="实时黄金价格：上海黄金交易所 Au99.99 等合约最新价、国际现货黄金 XAU/USD、美元兑人民币汇率，及国内溢价测算。数据自动更新，仅供参考。">
<meta name="keywords" content="今日金价,黄金价格,实时金价,上海黄金交易所, Au99.99, 国际金价, 国内溢价, 白银价格, 铂金价格">
<meta property="og:title" content="今日金价 · 实时黄金价格与国内溢价">
<meta property="og:description" content="SGE 实时行情 + 国际金价 + 汇率 + 国内溢价，一站看懂黄金价格。">
<meta property="og:type" content="website">
<link rel="canonical" href="https://c314726018.github.io/gold-site/">
<script type="application/ld+json">{json.dumps(faq_ld, ensure_ascii=False)}</script>
<script src="./vendor/chart.umd.min.js"></script>
<script src="./vendor/chartjs-chart-financial.umd.min.js"></script>
<style>{CSS}</style>
</head>
<body>
<header><div class="bar">
  <h1><span class="dot"></span>今日金价 · 实时行情</h1>
  <button id="themeBtn" aria-label="切换主题">🌓 主题</button>
</div></header>

<div class="wrap">
  <div class="hero">
    <div class="ov-grid">
      <div class="ov"><div class="k">SGE 黄金 Au99.99（元/克）</div>
        <div class="ov-val" id="ovSge">—<span class="u" id="ovSgeUnit"></span></div>
        <div class="t" id="ovSgeTime"></div></div>
      <div class="ov"><div class="k">国际现货黄金 XAU/USD</div>
        <div class="ov-val" id="ovXau">—</div><div class="t">美元/盎司</div></div>
      <div class="ov"><div class="k">美元兑人民币 USD/CNY</div>
        <div class="ov-val" id="ovFx">—</div><div class="t">实时汇率</div></div>
      <div class="ov"><div class="k">国内溢价</div>
        <div class="ov-val" id="ovPremium">—</div><div class="t">SGE 较国际折算</div></div>
    </div>
    <div class="disclaimer" id="genTime"></div>
  </div>

  <div class="ad-slot">广告位（百度联盟 / AdSense 代码粘贴于此 · 顶部通栏）</div>

  <div class="card">
    <h2>行情表 <span class="tag">上海黄金交易所</span></h2>
    <table>
      <thead><tr><th>品种</th><th>合约</th><th>最新价</th><th>今开</th><th>最高</th><th>最低</th><th>单位</th></tr></thead>
      <tbody id="tbody"></tbody>
    </table>
    <div class="disclaimer">「今开/最高/最低」为当日（或最近交易时段）区间；"最新价"为最近一笔成交。非交易时段显示最近一次有效报价。</div>
  </div>

  <div class="charts">
    <div class="card"><h2>{prim.get('symbol','主力')} 分时走势</h2><div class="chart-box"><canvas id="lineChart"></canvas></div></div>
    <div class="card"><h2>{prim.get('symbol','主力')} K线（分时聚合）</h2><div class="chart-box"><canvas id="kChart"></canvas></div></div>
    <div class="card full"><h2>多品种日内对比（归一化 %）</h2><div class="chart-box"><canvas id="cmpChart"></canvas></div></div>
  </div>

  <div class="card">
    <h2>价格提醒 <span class="tag">免费 · 浏览器通知</span></h2>
    <div class="alert-row">
      <select id="alertSym">{sym_opts}</select>
      <select id="alertDir"><option value="above">≥ 高于</option><option value="below">≤ 低于</option></select>
      <input id="alertVal" type="number" step="0.01" placeholder="目标价格">
      <button id="alertAdd">添加提醒</button>
      <button id="notifyBtn">开启通知</button>
    </div>
    <ul id="alertList"></ul>
    <form id="subForm" class="sub">
      <input id="subEmail" type="email" placeholder="留邮箱，金价异动邮件通知你" required>
      <button type="submit">订阅提醒</button>
      <div id="subNote"></div>
    </form>
    <div class="disclaimer">提醒保存在本机浏览器；开启桌面通知后，价格触发时自动弹窗。邮箱订阅需接入邮件服务后生效。</div>
  </div>

  <div class="ad-slot">广告位（信息流 / 内容中插 · 百度联盟 / AdSense）</div>

  <div class="card">
    <h2>黄金价格科普</h2>
    {faq_html}
    <div class="prose"><p class="muted">温馨提示：金价受国际宏观、汇率、供需等多因素影响，短期波动较大。本页仅作行情展示与数据参考，不构成任何投资建议或交易依据。</p></div>
  </div>

  <footer>
    数据来源：{src} · 本页为行情聚合展示，价格以交易所官方发布为准<br>
    <a href="https://www.sge.com.cn/" target="_blank" rel="noopener">上海黄金交易所官网</a> ·
    <a href="https://c314726018.github.io/gold-site/" rel="canonical">今日金价</a>
  </footer>

  <div class="ad-slot">广告位（页脚 / 侧栏 · 开户返佣 / 实物黄金导流位）</div>
</div>

<script id="app-data" type="application/json">{data_json}</script>
<script src="./app.js"></script>
</body>
</html>"""


def main():
    data = load_data()
    html = render(data)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(html)
    # 同时写出 docs/data.json：站点以 /docs 为根发布，前端 ./data.json 才能拉到实时数据
    with open(os.path.join(HERE, "docs", "data.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"[ok] 已生成 {OUT}（{len(data.get('items', []))} 个合约）")


if __name__ == "__main__":
    main()
