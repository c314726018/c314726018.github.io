#!/usr/bin/env python3
# 钯金行 + 最终校验
import os
B = "/Users/cuisiqi/WorkBuddy/2026-11-10-16-34-12/gold-site/"
p = B + "build.py"
src = open(p).read()

old = '''        if x.get("sge") is None and x.get("premium_pct") is None:
            continue  # 境内无报价，整行隐藏'''
new = '''        if x.get("sge") is None and x.get("premium_pct") is None and x.get("intl_cny") is None:
            continue  # 境内与国际均无报价才隐藏（钯金保留国际折算）'''
assert src.count(old) == 1, src.count(old)
src = src.replace(old, new, 1)

# sge None 时境内列显 —
pat_old = 'f\'<td class="num" data-label="境内报价">{fmt(x.get("sge"))} <span class="unit">{unit}</span></td>\''
assert src.count(pat_old) == 1, src.count(pat_old)
src = src.replace(pat_old,
    'f\'<td class="num" data-label="境内报价">{"—" if x.get("sge") is None else fmt(x.get("sge"))} <span class="unit">{unit}</span></td>\'', 1)

# premium None 时溢价列显 —(钯金无 sge 无法算溢价)
pat_prem = 'f\'<td data-label="国内溢价"><span class="chg {cls}">{prem_txt}</span></td>\''
assert src.count(pat_prem) == 1
src = src.replace(pat_prem,
    'f\'<td data-label="国内溢价">{"—" if prem is None else \'<span class="chg {cls}">{prem_txt}</span>\'}</td>\'', 1)

open(p, "w").write(src)
print("钯金行 OK")
