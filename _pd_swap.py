#!/usr/bin/env python3
# 钯金→Au(T+D) 递延溢价(修正锚点版)
import os
B = "/Users/cuisiqi/WorkBuddy/2026-11-10-16-34-12/gold-site/"
p = B + "build.py"
src = open(p).read()

# ===== 1) 还原钯金隐藏条件 =====
old = '''        if x.get("sge") is None and x.get("premium_pct") is None and x.get("intl_cny") is None:
            continue  # 境内与国际均无报价才隐藏（钯金保留国际折算）'''
new = '''        if x.get("sge") is None and x.get("premium_pct") is None:
            continue  # 境内无报价且无溢价（钯金关注度低,由 Au(T+D) 递延溢价替代）'''
assert src.count(old) == 1, "step1 %d" % src.count(old)
src = src.replace(old, new, 1)

# ===== 2) 签名加 data 参数 =====
old = 'def metals_rows(intl):\n    """多品种溢价对照表静态行（首屏可用，app.js 刷新后重建）。'
new = 'def metals_rows(intl, data=None):\n    """多品种溢价对照表静态行（首屏可用，app.js 刷新后重建）。'
assert src.count(old) == 1, "step2"
src = src.replace(old, new, 1)

# ===== 3) return 前追加递延溢价行(intl_symbol 行唯一) =====
old = '''            f'<td class="unit" data-label="口径">{esc(x.get("intl_symbol") or "")} × USD/CNY</td>'
            "</tr>")
    return "".join(rows)'''
assert src.count(old) == 1, "step3 %d" % src.count(old)
new = '''            f'<td class="unit" data-label="口径">{esc(x.get("intl_symbol") or "")} × USD/CNY</td>'
            "</tr>")
    # 黄金延期 Au(T+D) 递延溢价（多空失衡核心指标）
    try:
        autd = None
        for it in (data or {}).get("items") or []:
            if it.get("symbol") == "Au(T+D)":
                autd = it
                break
        g = m.get("gold") or {}
        if autd and autd.get("last") is not None and g.get("intl_cny"):
            base = float(g["intl_cny"])
            d = float(autd["last"]) - base
            pct = d / base * 100
            cls = "up" if d > 0 else "down" if d < 0 else "flat"
            prem_txt = f"{pct:+.2f}%"
            rows.append(
                "<tr>"
                f'<td class="lbl" data-label="品种">黄金延期（递延溢价） <span class="sym">Au(T+D)</span></td>'
                f'<td class="num" data-label="境内报价">{fmt(autd.get("last"))} <span class="unit">元/克</span></td>'
                f'<td class="num" data-label="国际折算">{fmt(base)}</td>'
                f'<td data-label="国内溢价"><span class="chg {cls}">{prem_txt}</span></td>'
                f'<td class="unit" data-label="口径">Au(T+D) 相对国际金 · 递延费方向</td>'
                "</tr>")
    except (TypeError, ValueError):
        pass
    return "".join(rows)'''
src = src.replace(old, new, 1)

# ===== 4) 调用处传 data =====
old = "{metals_rows(intl)}"
assert src.count(old) == 1, "step4"
src = src.replace(old, "{metals_rows(intl, data)}", 1)

open(p, "w").write(src)
print("钯金→Au(T+D) OK")
