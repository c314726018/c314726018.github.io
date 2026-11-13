#!/usr/bin/env python3
# 油价卡填充(在 page_data 内正确插入)
import os, re
B = "/Users/cuisiqi/WorkBuddy/2026-11-10-16-34-12/gold-site/"
p = B + "build.py"
src = open(p).read()

if "oe-grid" in src:
    print("已存在,跳过")
else:
    # 1) 计算代码插在 usd_cny 定义后
    anchor = '    usd_cny = intl.get("usd_cny")\n'
    assert src.count(anchor) == 1
    calc = anchor + '''    fx_usd = next((r.get("cny") for r in fx if r.get("code") == "USD"), 0) or usd_cny or 0
    wti_last = (oil.get("wti") or {}).get("last")
    brent_l = brent_last * fx_usd / 158.97 if (brent_last and fx_usd) else None
    wti_l = wti_last * fx_usd / 158.97 if (wti_last and fx_usd) else None
    gold_oil_barrel = (gold_last * 31.1035) / (brent_last * fx_usd) if (brent_last and fx_usd and gold_last) else None
    _oil_kl = (data.get("klines") or {}).get("OIL") or []
    _pts = _oil_kl[-60:]
    _svg = ""
    if len(_pts) >= 5:
        _vals = [x["c"] for x in _pts]
        _lo, _hi = min(_vals), max(_vals)
        _rng = (_hi - _lo) or 1
        _W, _H = 900, 90
        _step = _W / (len(_vals) - 1)
        _poly = " ".join(f"{i*_step:.1f},{_H-6-(v-_lo)/_rng*(_H-12):.1f}" for i, v in enumerate(_vals))
        _up = _vals[-1] >= _vals[0]
        _color = "#d4380d" if _up else "#129b63"
        _svg = (f'<svg viewBox="0 0 {_W:.0f} {_H}" style="width:100%;height:60px;display:block">'
                f'<polyline points="{_poly}" fill="none" stroke="{_color}" stroke-width="2"/></svg>'
                f'<div style="font-size:10.5px;color:var(--sub)">{esc(_pts[0]["d"])} → {esc(_pts[-1]["d"])} · {fmt(_vals[0])} → {fmt(_vals[-1])} 美元/桶</div>')
    _bl_html = fmt(brent_l, 2) if brent_l else "—"
    _wl_html = fmt(wti_l, 2) if wti_l else "—"
    _go_html = fmt(gold_oil_barrel, 1) if gold_oil_barrel else "—"
'''
    src = src.replace(anchor, calc, 1)

    # 2) 油价卡 tfoot 后插 HTML(f-string 内引用)
    m = re.search(r'(<div class="tfoot">布伦特 / WTI 为国际基准原油.*?</div>)', src, re.S)
    assert m, "tfoot"
    TFOOT = m.group(1)
    calc_html = TFOOT + '''
      <!-- 油价衍生:折算/走势/金油比 -->
      <div class="oil-extra">
        <div class="oe-grid">
          <div class="dcard"><div class="dk">布伦特 折算人民币</div><div class="dv">{_bl_html} <span style="font-size:12px">元/升</span></div><div class="dn">美元/桶 × 汇率 ÷ 158.97 升,原料口径</div></div>
          <div class="dcard"><div class="dk">WTI 折算人民币</div><div class="dv">{_wl_html} <span style="font-size:12px">元/升</span></div><div class="dn">同口径折算,跨市场价差参考</div></div>
          <div class="dcard"><div class="dk">金油比</div><div class="dv">{_go_html} <span style="font-size:12px">桶/盎司</span></div><div class="dn">1 盎司黄金可兑换的布伦特桶数</div></div>
        </div>
        <div class="oe-spark">
          <div class="dk" style="margin-bottom:6px">布伦特 近 60 个交易日收盘</div>
          {_svg}
        </div>
      </div>'''
    src = src.replace(TFOOT, calc_html, 1)

    # 3) CSS
    src = src.replace("/* ============ 溢价衍生指标卡 ============ */",
'''.oe-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;margin:14px 0}
.oe-spark{background:var(--surface-2);border:1px solid var(--line);border-radius:10px;padding:12px 14px}
@media(max-width:720px){.oe-grid{grid-template-columns:1fr}}

/* ============ 溢价衍生指标卡 ============ */''', 1)

    open(p, "w").write(src)
    print("油价卡填充 OK")
