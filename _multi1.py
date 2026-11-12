#!/usr/bin/env python3
# 提醒多选+等于方向+留言页
import os
B = "/Users/cuisiqi/WorkBuddy/2026-11-10-16-34-12/gold-site/"
p = B + "build.py"
src = open(p).read()

# ===== 1) 品种池函数(40 品种) =====
old = '    sym_opts = "".join(\n        f\'<option value="{esc(it.get("symbol"))}">{esc(it.get("label"))} {esc(it.get("symbol"))}</option>\'\n        for it in items)'
new = '''    sym_pool = []
    for it in items:
        sym_pool.append((it.get("symbol"), it.get("label") + " " + it.get("symbol")))
    for k, nm in (("BRENT", "布伦特原油"), ("WTI", "WTI原油"), ("SC", "上海原油")):
        sym_pool.append((k, nm))
    for x in (data.get("extra") or {}).get("futures") or []:
        sym_pool.append((x.get("code"), x.get("name")))
    for x in (data.get("extra") or {}).get("indices") or []:
        sym_pool.append((x.get("code"), x.get("name")))
    for x in (data.get("extra") or {}).get("intl") or []:
        sym_pool.append((x.get("code"), x.get("name")))
    D = (data.get("extra") or {}).get("dxy")
    if D:
        sym_pool.append(("DINIW", "美元指数"))
    sym_pills = "".join(
        f'<a class="sp" data-v="{esc(sv)}" title="点击选中/取消">{esc(sl)}</a>'
        for sv, sl in sym_pool)'''
assert src.count(old) == 1
src = src.replace(old, new, 1)
print("品种池 OK")

# ===== 2) 表单:select→多选胶囊;dir 加等于 =====
old = '''          <div class="alert-row">
            <select id="alertSym" aria-label="选择品种">{sym_opts}</select>
            <select id="alertDir" aria-label="提醒方向"><option value="above">≥ 高于</option><option value="below">≤ 低于</option></select>
            <input id="alertVal" type="number" step="0.01" placeholder="目标价格" aria-label="目标价格">
          </div>'''
new = '''          <div class="sym-multi" id="alertSymBox" aria-label="选择品种(可多选)">{sym_pills}</div>
          <div class="hint" style="margin:4px 2px">可多选品种;每个品种将分别建立提醒规则。</div>
          <div class="alert-row">
            <select id="alertDir" aria-label="提醒方向"><option value="above">≥ 高于</option><option value="below">≤ 低于</option><option value="equal">= 等于</option></select>
            <input id="alertVal" type="number" step="0.01" placeholder="目标价格" aria-label="目标价格">
          </div>'''
assert src.count(old) == 1
src = src.replace(old, new, 1)
print("表单多选+等于 OK")

# ===== 3) 多选/等于 CSS =====
old = ".mail-box{margin-top:14px;"
new = '''.sym-multi{display:flex;flex-wrap:wrap;gap:5px;margin:4px 0;max-height:132px;overflow-y:auto;scrollbar-width:thin;
  padding:8px;border:1px solid var(--line);border-radius:var(--r-sm);background:var(--surface-2)}
.sym-multi .sp{font-size:11px;color:var(--ink-2);padding:3px 9px;border-radius:14px;cursor:pointer;
  border:1px solid var(--line);background:var(--surface);transition:.12s;white-space:nowrap;user-select:none}
.sym-multi .sp:hover{color:var(--gold);border-color:var(--gold-2)}
.sym-multi .sp.on{color:#fff;background:var(--gold);border-color:var(--gold);font-weight:650}
.mail-box{margin-top:14px;'''
assert src.count(old) == 1
src = src.replace(old, new, 1)
print("多选 CSS OK")

open(p, "w").write(src)
print("build.py 阶段完成")
