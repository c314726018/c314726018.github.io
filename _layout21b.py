#!/usr/bin/env python3
# 任务21-2:heat 变量挂接 / page_news 重写 / 文案
import os
B = "/Users/cuisiqi/WorkBuddy/2026-11-10-16-34-12/gold-site/"
p = B + "build.py"
src = open(p).read()

# ===== 1) page_index 生成 heat 变量 =====
old = "    data_json = json.dumps(data, ensure_ascii=False)"
new = "    heat = heat_grid(data)\n\n    data_json = json.dumps(data, ensure_ascii=False)"
assert src.count(old) == 1
src = src.replace(old, new, 1)

# ===== 2) page_news 整体重写 =====
i_n = src.index("def page_news(data):")
i_next = src.index("def page_calendar(data):")

NEW_NEWS = '''def _news_tag(t):
    """按关键词给快讯分类(用于过滤与标签)。"""
    import re as _re
    s = (t.get("title") or "") + (t.get("text") or "")
    if _re.search(r"黄金|白银|贵金属|金价|金饰|铂金|钯金|金条", s):
        return "贵金属"
    if _re.search(r"美联储|FOMC|利率|央行|货币政策|LPR|降准|降息|MLF|通胀|CPI|PPI|GDP", s, _re.I):
        return "宏观央行"
    if _re.search(r"原油|OPEC|油价|天然气|煤炭|能源|成品油", s, _re.I):
        return "能源"
    if _re.search(r"美元|汇率|人民币|日元|欧元|英镑|外汇|离岸", s):
        return "外汇"
    if _re.search(r"A股|港股|美股|沪指|创业板|指数|IPO|市值|股市|纳指|道琼|上市公司|财报", s):
        return "股市"
    return "综合"


def page_news(data):
    news = data.get("news") or []
    if news:
        top = news[0]
        tag0 = _news_tag(top)
        hero = (
            '<div class="news-hero" data-cat="' + tag0 + '">'
            '<div class="nh-top"><span class="nl-tag t-' + tag0 + '">' + esc(tag0) + '</span>'
            '<span class="nh-time">◷ ' + esc(top.get("time")) + ' · ' + esc(top.get("source")) + '</span></div>'
            '<div class="nh-title">' + esc(top.get("title")) + '</div>'
            '<div class="nh-text">' + esc(top.get("text")) + '</div>'
            '<div class="nh-foot">快讯持续滚动更新,更多内容见下方时间轴 · 数据源:' + esc(top.get("source")) + '公开资讯流</div>'
            '</div>')
        items_html = ""
        for n in news[1:]:
            tg = _news_tag(n)
            items_html += (
                '<div class="nl-item" data-cat="' + tg + '">'
                '<div class="nl-time">' + esc((n.get("time") or "")[5:16]) + '</div>'
                '<div class="nl-dot"></div>'
                '<div class="nl-body">'
                '<div class="nl-head"><span class="nl-tag t-' + tg + '">' + esc(tg) + '</span>'
                '<span class="nl-title">' + esc(n.get("title")) + '</span></div>'
                '<div class="nl-text">' + esc(n.get("text")) + '</div>'
                '<div class="nl-meta">' + esc(n.get("source")) + '</div>'
                '</div></div>')
        if not items_html:
            items_html = '<div class="news-empty">今日暂无更多快讯。</div>'
    else:
        hero = '<div class="news-empty">快讯数据加载中,请稍候刷新。</div>'
        items_html = ""
    head = head_html(
        "财经快讯 - 7×24 实时金融快讯 - 金潮网",
        "7×24 小时实时财经快讯:覆盖贵金属、宏观央行、能源商品、外汇与全球股市,按分类筛选阅读,30 分钟随数据管道自动更新。",
        SITE + "news.html")
    body = f"""{topbar_html(data)}
{ticker_html(data)}
{nav_html("news")}
{subnav_html("news")}
<div class="wrap"><div class="portal">{side_left("news")}<div class="portal-main">
<main>
  <section class="section" id="live">
    <div class="mbox-h"><span class="mh-l">7×24 实时快讯</span>
      <div class="news-filter" id="newsFilter">
        <button class="fbtn on" data-cat="all">全部</button>
        <button class="fbtn" data-cat="贵金属">贵金属</button>
        <button class="fbtn" data-cat="宏观央行">宏观央行</button>
        <button class="fbtn" data-cat="能源">能源</button>
        <button class="fbtn" data-cat="外汇">外汇</button>
        <button class="fbtn" data-cat="股市">股市</button>
        <button class="fbtn" data-cat="综合">综合</button>
      </div></div>
    {hero}
    <div class="news-timeline">{items_html}</div>
    <div class="mbox-note"><b>资讯说明:</b>快讯由华尔街见闻公开资讯流聚合展示,版权归原发布方所有;分类标签由本站按关键词自动归档,仅供筛选阅读。内容不构成任何投资建议。</div>
  </section>
</main>
</div>{side_right(data)}</div></div>
{footer_html()}
<script id="app-data" type="application/json">{{}}</script>
<script src="./ads.js"></script>
<script src="./common.js"></script>
<script src="./app.js"></script>
<script>
(function(){{
  var f = document.getElementById("newsFilter");
  if (!f) return;
  f.addEventListener("click", function (e) {{
    var b = e.target.closest(".fbtn"); if (!b) return;
    f.querySelectorAll(".fbtn").forEach(function (x) {{ x.classList.remove("on"); }});
    b.classList.add("on");
    var cat = b.getAttribute("data-cat");
    document.querySelectorAll(".news-hero, .nl-item").forEach(function (it) {{
      it.style.display = (cat === "all" || it.getAttribute("data-cat") === cat) ? "" : "none";
    }});
  }});
}})();
</script>
</body></html>"""
    return head + body


'''
src = src[:i_n] + NEW_NEWS + src[i_next:]
print("page_news 重写 OK")

# ===== 3) 文案 pass =====
COPY = [
  ('<p class="lead">国内现货 · 国际金价 · 汇率 · 国内溢价,四个维度同步对照,不再只看一个孤立的数字。</p>',
   '<p class="lead">上海黄金交易所、国内期货主力、全球股指、国际现货与能源行情一屏联动;报价模块支持品种切换与分时/日K切换,均线与技术指标随时调取。</p>'),
  ('<p>现货、延期与 100g 合约并列对照,涨跌幅以今开为基准计算。</p>',
   '<p>SGE 全部主力合约并列对照:现货、延期、100g 与国际板;红涨绿跌,涨跌幅以今开为基准,收盘后锁定当日区间。</p>'),
  ('<p>黄金、白银、铂金的境内报价与国际折算价对照,看懂内外价差。</p>',
   '<p>金、银、铂、钯四品种境内价 vs 国际折算,溢价口径透明可查(国际价 × 汇率 ÷ 31.1035)。</p>'),
]
for a, b in COPY:
    if src.count(a) == 1:
        src = src.replace(a, b, 1)
        print("文案 OK:", a[:22])
    else:
        print("文案跳过:", a[:22])

open(p, "w").write(src)
print("任务21-2 完成:", len(src))
