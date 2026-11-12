#!/usr/bin/env python3
# 交互可供性系统强化:所有可点击元素按钮化/pill化 + hover/active 反馈
import os
B = "/Users/cuisiqi/WorkBuddy/2026-11-10-16-34-12/gold-site/"
p = B + "build.py"
src = open(p).read()
R = []  # (old, new, 说明)

# ===== 1) 报价模块 tabs:纯文字下划线 → 明显 pill 按钮 =====
R.append((
    ".tq-tabs a{font-size:12px;color:var(--sub);padding:9px 9px;cursor:pointer;white-space:nowrap;\n  border-bottom:2px solid transparent;transition:.13s}",
    ".tq-tabs a{font-size:12px;color:var(--sub);padding:5px 10px;margin:4px 2px;cursor:pointer;white-space:nowrap;\n  border:1px solid var(--line);border-radius:16px;background:color-mix(in srgb,var(--ink) 4%,transparent);transition:.13s}", "tabs pill"))
R.append((
    ".tq-tabs a:hover{color:var(--ink)}",
    ".tq-tabs a:hover{color:var(--gold);border-color:var(--gold-2);background:var(--gold-soft)}", "tabs hover"))
R.append((
    ".tq-tabs a.on{color:var(--gold);border-bottom-color:var(--gold);font-weight:650}",
    ".tq-tabs a.on{color:#fff;background:var(--gold);border-color:var(--gold);font-weight:650}", "tabs on"))
R.append((
    ".tq-mode a{font-size:11px;padding:9px 8px;color:var(--sub)}",
    ".tq-mode a{font-size:11px;padding:5px 8px;color:var(--sub)}", "mode"))
R.append((
    ".tq-mode a.on{color:var(--ink);border-bottom-color:var(--ink)}",
    ".tq-mode a.on{color:#fff;background:var(--ink);border-color:var(--ink)}", "mode on"))

# ===== 2) 工具行按钮:无边框文字 → 边框按钮 =====
R.append((
    ".tq-tools a{font-size:10.5px;color:var(--sub);padding:2px 6px;border-radius:6px;cursor:pointer;transition:.12s;white-space:nowrap}",
    ".tq-tools a{font-size:10.5px;color:var(--ink-2);padding:3px 9px;border-radius:7px;cursor:pointer;transition:.12s;white-space:nowrap;\n  border:1px solid var(--line);background:var(--surface)}", "tools btn"))
R.append((
    ".tq-tools a:hover{color:var(--ink);background:var(--surface-2)}",
    ".tq-tools a:hover{color:var(--gold);border-color:var(--gold-2);background:var(--gold-soft)}", "tools hover"))
R.append((
    ".tq-tools a.on{color:var(--gold);background:var(--gold-soft);font-weight:650}",
    ".tq-tools a.on{color:#fff;background:var(--gold);border-color:var(--gold);font-weight:650}", "tools on"))

# ===== 3) 二级导航 subnav:文字 → pill =====
R.append((
    ".subnav-links a{font-size:12.5px;color:var(--ink-2);padding:5px 2px;text-decoration:none;border-radius:6px;transition:.12s}",
    ".subnav-links a{font-size:12.5px;color:var(--ink-2);padding:5px 12px;text-decoration:none;border-radius:16px;transition:.12s;\n  background:color-mix(in srgb,var(--ink) 4%,transparent);border:1px solid transparent}", "subnav pill"))
R.append((
    ".subnav-links a:hover{color:var(--gold)}",
    ".subnav-links a:hover{color:var(--gold);border-color:var(--gold-2);background:var(--gold-soft)}", "subnav hover"))

# ===== 4) 左栏/右栏 mini-list 链接:加箭头 + hover 背景条 =====
R.append((
    ".pmod-b .mini-list li{padding:7px 2px;line-height:1.65}",
    ".pmod-b .mini-list li{padding:6px 8px;line-height:1.65;border-radius:8px;transition:.12s}", "mini li"))
R.append((
    ".pmod-b .mini-list li:hover{background:var(--surface-2)}\n",
    ".pmod-b .mini-list li:hover{background:var(--surface-2)}\n.pmod-b .mini-list li a::after{content:\" ›\";color:var(--gold-2);font-weight:700}\n.pmod-b .mini-list li:hover a{color:var(--gold)}\n", "mini arrow"))
# 首页大表旁的 mini-list(左栏)可能没有 pmod-b 前缀——补通用
R.append((
    ".side-nav .mini-list a{",
    ".side-nav .mini-list a{", "side-nav 占位(若无变化)"))

# ===== 5) footer 链接:hover 下划线+金 =====
R.append((
    ".foot-col a:hover{color:var(--gold-2)}",
    ".foot-col a:hover{color:var(--gold-2);text-decoration:underline;text-underline-offset:3px}", "footer hover"))

# ===== 6) 星标:更大可点区+hover 反馈 =====
R.append((
    ".fav{cursor:pointer;margin-right:5px;color:var(--sub);font-size:12px;user-select:none}",
    ".fav{cursor:pointer;margin-right:6px;color:var(--sub);font-size:14px;user-select:none;padding:2px 4px;border-radius:6px;transition:.12s;display:inline-block}", "fav"))
R.append((
    ".fav:hover{color:var(--gold)}",
    ".fav:hover{color:var(--gold);background:var(--gold-soft);transform:scale(1.15)}", "fav hover"))

# ===== 7) 主导航 ntab:当前页/ hover 增强 =====
R.append((
    ".nav-menu .ntab{",
    ".nav-menu .ntab{", "ntab 占位"))

# ===== 8) 全局:按钮类统一按压反馈 =====
R.append((
    "@media(prefers-reduced-motion:reduce){",
    "button, .fbtn, .tq-tabs a, .tq-tools a, .heat{cursor:pointer}\n"
    "button:active, .fbtn:active{transform:scale(.97)}\n"
    "@media(prefers-reduced-motion:reduce){", "active 反馈"))

ok = 0
for old, new, name in R:
    n = src.count(old)
    if n >= 1:
        src = src.replace(old, new, 1)
        ok += 1
        print(f"  ✓ {name}")
    else:
        print(f"  ⚠️ 跳过({n} 命中): {name} | {old[:60]}")
open(p, "w").write(src)
print(f"完成 {ok}/{len(R)}")
