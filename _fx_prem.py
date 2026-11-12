#!/usr/bin/env python3
# 汇率表修列 / 溢价加钯金+衍生指标 / 快讯条目卡片化
import os
B = "/Users/cuisiqi/WorkBuddy/2026-11-10-16-34-12/gold-site/"
p = B + "build.py"
src = open(p).read()

# ===== 1) fx_rows 删反算列(显示不全根因) =====
old = '''def fx_rows(fx):
    """人民币汇率表：1（或 100）外币兑人民币 + 1 人民币兑外币。"""
    rows = []
    for r in fx or []:
        unit_note = "100" if r.get("unit") == 100 else "1"
        rows.append(
            "<tr>"
            f'<td class="lbl" data-label="币种">{esc(r.get("name"))}</td>'
            f'<td class="sym" data-label="代码">{esc(r.get("code"))}</td>'
            f'<td class="num strong" data-label="兑人民币">{unit_note} {esc(r.get("code"))} = {fmt(r.get("cny"), 4)}</td>'
            f'<td class="num" data-label="人民币兑">1 CNY = {fmt(r.get("per_cny"), 4)}</td>'
            "</tr>")
    return "".join(rows)'''
new = '''def fx_rows(fx):
    """人民币汇率表：1（或 100）外币兑人民币。"""
    rows = []
    for r in fx or []:
        unit_note = "100" if r.get("unit") == 100 else "1"
        rows.append(
            "<tr>"
            f'<td class="lbl" data-label="币种">{esc(r.get("name"))}</td>'
            f'<td class="sym" data-label="代码">{esc(r.get("code"))}</td>'
            f'<td class="num strong" data-label="兑人民币">{unit_note} {esc(r.get("code"))} = {fmt(r.get("cny"), 4)}</td>'
            f'<td class="unit" data-label="计价单位">{unit_note} 外币</td>'
            "</tr>")
    return "".join(rows)'''
assert src.count(old) == 1
src = src.replace(old, new, 1)
# 表头同步
src = src.replace("<thead><tr><th>币种</th><th>代码</th><th>兑人民币</th><th>人民币兑</th></tr></thead>",
                  "<thead><tr><th>币种</th><th>代码</th><th>兑人民币</th><th>计价单位</th></tr></thead>", 1)
print("汇率表修列 OK")

# ===== 2) 溢价表:钯金显示(sge None 也显示) =====
old = '''        if x.get("sge") is None and x.get("premium_pct") is None:
            continue  # 境内无报价,整行隐藏'''
new = '''        if x.get("sge") is None and x.get("premium_pct") is None and x.get("intl_cny") is None:
            continue  # 境内与国际均无报价才隐藏(钯金保留国际折算)'''
assert src.count(old) == 1
src = src.replace(old, new, 1)
# sge None 时境内报价列显示 —
old = '''            f'<td class="num" data-label="境内报价">{fmt(x.get("sge"))} <span class="unit">{unit}</span></td>\''''
if src.count(old) != 1:
    old = '''            f'<td class="num" data-label="境内报价">{fmt(x.get("sge"))} <span class="unit">{unit}</span></td>' ''
new = '''            f'<td class="num" data-label="境内报价">{"—" if x.get("sge") is None else fmt(x.get("sge"))} <span class="unit">{unit}</span></td>' '''
assert src.count(old) == 1, "sge cell"
src = src.replace(old, new, 1)
print("溢价表钯金行 OK")

# ===== 3) 溢价区加 3 个衍生指标卡(金银比/金油比/金铂比) =====
# 在 page_data 的溢价 section 表格 card 后插入
anchor = '''      <table class="mega-table">
        <thead><tr><th>品种</th><th>境内报价 (SGE)</th><th>国际折算</th><th>国内溢价</th><th>口径</th></tr></thead>
        <tbody id="metalsBody">{metals_rows(intl)}</tbody>
      </table>'''
assert src.count(anchor) == 1
deriv = anchor + '''
      <div class="deriv-grid">
        <div class="dcard"><div class="dk">金银比</div><div class="dv" id="drGoldSilver">—</div><div class="dn">XAU ÷ XAG,历史均值约 70-80</div></div>
        <div class="dcard"><div class="dk">金油比</div><div class="dv" id="drGoldOil">—</div><div class="dn">1 盎司黄金可买多少桶布伦特</div></div>
        <div class="dcard"><div class="dk">金铂比</div><div class="dv" id="drGoldPlat">—</div><div class="dn">XAU ÷ XPT,铂金强弱对照</div></div>
      </div>'''
src = src.replace(anchor, deriv, 1)
print("衍生指标卡 OK")

open(p, "w").write(src)
print("阶段1 完成")
