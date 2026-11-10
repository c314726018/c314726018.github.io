#!/usr/bin/env python3
"""
读取 data.json，渲染静态站点 docs/index.html（零依赖）。
GitHub Pages 从该仓库的 /docs 目录发布。
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "data.json")
OUT = os.path.join(HERE, "docs", "index.html")


def fmt(v):
    try:
        return f"{float(v):,.2f}"
    except (TypeError, ValueError):
        return "—"


def render(data):
    items = data.get("items", [])
    primary = data.get("primary") or {}
    gen = data.get("generated_at", "")
    src = data.get("source", "上海黄金交易所")

    rows = []
    for it in items:
        rows.append(f"""
        <tr>
          <td class="lbl">{it['label']}</td>
          <td class="sym">{it['symbol']}</td>
          <td class="num strong">{fmt(it['last'])}</td>
          <td class="num">{fmt(it['open'])}</td>
          <td class="num up">{fmt(it['max'])}</td>
          <td class="num down">{fmt(it['min'])}</td>
          <td class="unit">{it['unit']}</td>
        </tr>""")

    # 主图数据（走势图）
    chart_labels = primary.get("time", []) or [str(i) for i in range(len(primary.get("series", [])))]
    chart_data = primary.get("series", [])
    chart_sym = primary.get("symbol", "Au99.99")

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>贵金属实时行情 · 上海黄金交易所</title>
<meta name="description" content="上海黄金交易所黄金、白银、铂金、钯金实时行情，数据每日更新。">
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<style>
  :root {{
    --bg:#f7f8fa; --card:#ffffff; --ink:#1f2329; --sub:#6b7280;
    --line:#e5e7eb; --gold:#b8860b; --up:#d4380d; --down:#389e0d; --accent:#2f6fed;
  }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif;
         background:var(--bg); color:var(--ink); line-height:1.5; }}
  .wrap {{ max-width:920px; margin:0 auto; padding:28px 16px 56px; }}
  header h1 {{ font-size:22px; margin:0 0 4px; }}
  .meta {{ color:var(--sub); font-size:13px; margin-bottom:20px; }}
  .card {{ background:var(--card); border:1px solid var(--line); border-radius:14px; padding:18px 18px 8px;
          box-shadow:0 1px 3px rgba(0,0,0,.04); margin-bottom:20px; }}
  table {{ width:100%; border-collapse:collapse; font-size:14px; }}
  th,td {{ padding:11px 8px; text-align:right; border-bottom:1px solid var(--line); }}
  th:first-child,td:first-child, th:nth-child(2),td:nth-child(2) {{ text-align:left; }}
  th {{ color:var(--sub); font-weight:600; font-size:12px; }}
  .lbl {{ font-weight:600; }}
  .sym {{ color:var(--sub); font-family:ui-monospace,SFMono-Regular,Menlo,monospace; font-size:12px; }}
  .num {{ font-variant-numeric:tabular-nums; }}
  .strong {{ font-weight:700; color:var(--gold); font-size:15px; }}
  .up {{ color:var(--up); }} .down {{ color:var(--down); }}
  .unit {{ color:var(--sub); font-size:12px; }}
  .chart-title {{ font-size:14px; font-weight:600; margin:4px 2px 12px; }}
  .chart-box {{ height:260px; }}
  .disclaimer {{ color:var(--sub); font-size:12px; margin-top:8px; line-height:1.7; }}
  footer {{ color:var(--sub); font-size:12px; text-align:center; margin-top:24px; }}
  a {{ color:var(--accent); text-decoration:none; }}
</style>
</head>
<body>
<div class="wrap">
  <header>
    <h1>贵金属实时行情</h1>
    <div class="meta">数据来源：{src} · 生成时间：{gen} · 仅供参考，不构成投资建议</div>
  </header>

  <div class="card">
    <table>
      <thead>
        <tr><th>品种</th><th>合约</th><th>最新价</th><th>今开</th><th>最高</th><th>最低</th><th>单位</th></tr>
      </thead>
      <tbody>{''.join(rows)}</tbody>
    </table>
    <div class="disclaimer">「今开/最高/最低」为当日（或最近交易时段）区间；“最新价”为最近一笔成交。非交易时段显示最近一次有效报价。</div>
  </div>

  <div class="card">
    <div class="chart-title">{chart_sym} 日内走势</div>
    <div class="chart-box"><canvas id="c"></canvas></div>
  </div>

  <footer>
    本页为行情聚合展示，所有价格以交易所官方发布为准 ·
    <a href="https://www.sge.com.cn/" target="_blank" rel="noopener">上海黄金交易所官网</a>
  </footer>
</div>

<script>
const LABELS = {json.dumps(chart_labels, ensure_ascii=False)};
const SERIES = {json.dumps(chart_data)};
const SYM = {json.dumps(chart_sym, ensure_ascii=False)};
if (SERIES.length) {{
  new Chart(document.getElementById('c'), {{
    type:'line',
    data:{{ labels:LABELS, datasets:[{{ label:SYM, data:SERIES, borderColor:'#b8860b',
            backgroundColor:'rgba(184,134,11,.08)', borderWidth:1.6, pointRadius:0, tension:.25, fill:true }}] }},
    options:{{ responsive:true, maintainAspectRatio:false,
      plugins:{{ legend:{{ display:false }} }},
      scales:{{ x:{{ ticks:{{ maxTicksLimit:8, color:'#9ca3af', font:{{size:10}} }}, grid:{{display:false}} }},
               y:{{ ticks:{{ color:'#9ca3af', font:{{size:10}} }}, grid:{{color:'#eef0f3'}} }} }} }}
  }});
}}
</script>
</body>
</html>"""


def main():
    with open(CACHE, encoding="utf-8") as f:
        data = json.load(f)
    html = render(data)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[ok] 已生成 {OUT} （{len(data.get('items', []))} 个合约）")


if __name__ == "__main__":
    main()
