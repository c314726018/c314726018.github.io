#!/usr/bin/env python3
# 任务21-1(修正版):宽度1660 / 频道统一(hero+行情表移进portal-main) / 模块3 tabs 13 / 热力图
import os
B = "/Users/cuisiqi/WorkBuddy/2026-11-10-16-34-12/gold-site/"
p = B + "build.py"
src = open(p).read()

# ===== 1) 宽度 1240 → 1660 =====
src = src.replace(".wrap{max-width:1240px;margin:0 auto;padding:0 20px}",
                  ".wrap{max-width:1660px;margin:0 auto;padding:0 24px}", 1)
src = src.replace(".portal{display:grid;grid-template-columns:180px minmax(0,1fr) 300px;gap:14px;align-items:start;margin:16px 0}",
                  ".portal{display:grid;grid-template-columns:210px minmax(0,1fr) 360px;gap:16px;align-items:start;margin:16px 0}", 1)

# ===== 2) 频道统一:hero + 行情表移进 portal-main =====
# 当前顺序: hero → 行情表 → portal{left, main → 溢价…}
i_hero = src.index('  <!-- ============ 三大报价模块（金投网式,tab 切换） ============ -->')
i_q = src.index('  <!-- ============ 行情表 ============ -->')
i_portal = src.index("  <div class=\"portal\">{side_left('quotes')}")
i_pre = src.index('  <!-- ============ 多品种溢价 ============ -->')
assert i_hero < i_q < i_portal < i_pre, (i_hero, i_q, i_portal, i_pre)

hero_block = src[i_hero:i_q]      # 三大报价段
q_block = src[i_q:i_portal]       # 行情表段
rest = src[i_portal:]             # portal 开标签起

# rest 去掉 portal 开标签与 portal-main 行,保留 portal-main 之后的内容
pm_i = rest.index('<div class="portal-main">')
pm_end = rest.index("\n", pm_i) + 1
rest_body = rest[pm_end:]

PORTAL_OPEN = ('  <div class="portal">{side_left(\'quotes\')}\n'
               '  <div class="portal-main">\n\n')
src = src[:i_hero] + PORTAL_OPEN + hero_block + q_block + rest_body
print("频道统一 OK(hero+行情表 移入 portal-main)")

# ===== 3) 模块3 tabs 扩 13 品种 =====
old = '<div class="tq-tabs"><b>能源与商品</b><a class="on" data-i="0">布伦特</a><a data-i="1">WTI</a><a data-i="2">上海原油</a><a data-i="3">沪铜</a><a data-i="4">螺纹钢</a><span class="tq-mode"><a class="on" data-m="0">走势</a><a data-m="1">日K</a></span></div>'
new = '<div class="tq-tabs"><b>能源与商品</b><a class="on" data-i="0">布伦特</a><a data-i="1">WTI</a><a data-i="2">上海原油</a><a data-i="3">沪铜</a><a data-i="4">沪铝</a><a data-i="5">沪锌</a><a data-i="6">沪镍</a><a data-i="7">沪锡</a><a data-i="8">螺纹钢</a><a data-i="9">豆粕</a><a data-i="10">铁矿石</a><a data-i="11">玉米</a><a data-i="12">棉花</a><span class="tq-mode"><a class="on" data-m="0">走势</a><a data-m="1">日K</a></span></div>'
assert src.count(old) == 1
src = src.replace(old, new, 1)
print("模块3 tabs 13 品种 OK")

# ===== 4) heat_grid 函数 =====
old = 'def metals_rows(intl):'
heat_fn = '''def heat_grid(data):
    """全品种涨跌热力图:SGE+期货+股指+国际现货,色阶映射涨跌幅。"""
    def cell(name, last, base, link="./index.html#quotes"):
        try:
            if last is None or base in (None, 0, ""):
                raise ValueError
            d = float(last) - float(base)
            pct = d / float(base) * 100
        except (TypeError, ValueError):
            return ('<a class="heat flat" href="' + link + '"><span class="h-n">' + esc(name) +
                    '</span><span class="h-v">—</span></a>')
        cls = "up" if d > 0 else "down" if d < 0 else "flat"
        a = abs(pct)
        lv = "lv4" if a >= 4 else "lv3" if a >= 2 else "lv2" if a >= 1 else "lv1"
        arrow = "▲" if d > 0 else "▼" if d < 0 else "—"
        return ('<a class="heat ' + cls + ' ' + lv + '" href="' + link + '" title="' + esc(name) +
                ' ' + ("+" if d > 0 else "") + fmt(d) + '">' +
                '<span class="h-n">' + esc(name) + '</span>' +
                '<span class="h-v">' + arrow + ' ' + ("+" if pct > 0 else "") + fmt(pct) + '%</span></a>')

    cells = []
    for it in data.get("items") or []:
        cells.append(cell(it.get("label"), it.get("last"), it.get("open")))
    ex = data.get("extra") or {}
    for x in ex.get("futures") or []:
        cells.append(cell(x.get("name"), x.get("last"), x.get("prev")))
    for x in ex.get("indices") or []:
        if x.get("chg") is not None and x.get("pct") is not None:
            dd, pct = x["chg"], x["pct"]
            cls = "up" if dd > 0 else "down" if dd < 0 else "flat"
            a = abs(pct or 0)
            lv = "lv4" if a >= 4 else "lv3" if a >= 2 else "lv2" if a >= 1 else "lv1"
            arrow = "▲" if dd > 0 else "▼" if dd < 0 else "—"
            cells.append('<a class="heat ' + cls + ' ' + lv + '" href="./index.html#quotes" title="' + esc(x.get("name")) +
                         '"><span class="h-n">' + esc(x.get("name")) + '</span>' +
                         '<span class="h-v">' + arrow + ' ' + ("+" if pct > 0 else "") + fmt(abs(pct)) + '%</span></a>')
        else:
            cells.append(cell(x.get("name"), x.get("last"), x.get("prev")))
    for x in ex.get("intl") or []:
        cells.append(cell(x.get("name"), x.get("last"), x.get("prev")))
    D = ex.get("dxy")
    if D:
        cells.append(cell("美元指数", D.get("last"), D.get("prev")))
    return '<div class="heat-grid">' + "".join(cells) + '</div>'


def metals_rows(intl):'''
assert src.count(old) == 1
src = src.replace(old, heat_fn, 1)
print("heat_grid 函数 OK")

# ===== 5) 首页插热力图板块(行情表之后) =====
i_pre = src.index('  <!-- ============ 多品种溢价 ============ -->')
heat_sec = '''  <!-- ============ 全品种涨跌热力图 ============ -->
  <section class="section" id="heat">
    <div class="mbox-h"><span class="mh-l">全品种涨跌热力图</span>
      <span class="more">红涨绿跌 · 色深代表幅度 · 覆盖 36 个品种</span></div>
    <div class="card" style="padding:12px">
      {heat}
    </div>
    <div class="mbox-note">覆盖上海黄金交易所、国内期货主力、全球股指、国际现货与美元指数;涨跌幅口径:SGE 以今开为基准,期货以昨结,现货与指数以昨收。</div>
  </section>

'''
src = src[:i_pre] + heat_sec + src[i_pre:]
print("热力图板块 OK")

open(p, "w").write(src)
print("任务21-1(修正版)完成:", len(src))
