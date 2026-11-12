#!/usr/bin/env python3
"""
读取 data.json，渲染静态站点（零 Python 依赖，仅标准库）。

产出（均在 docs/，GitHub Pages 以 /docs 为根发布）：
  index.html    行情主页（品牌头部 / 跑马灯 / Hero / 概览 / 行情表 / 图表 / 提醒 / 百科）
  about.html    关于与数据说明
  privacy.html  隐私政策（AdSense 要求）
  site.css      全站样式
  data.json     前端 60s 轮询的数据副本

设计约束：
  - app.js 依赖的 DOM id 全部保留，改版不得破坏交互
  - AdSense loader 必须字面存在于每个页面的 <head>
  - 涨=红 / 跌=绿（中国市场习惯）
"""
import json
import os
import datetime
import html as _html

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "data.json")
DOCS = os.path.join(HERE, "docs")
OUT = os.path.join(DOCS, "index.html")

SITE = "https://c314726018.github.io/"

# AdSense 网站代码 —— 直接写入生成页的 <head>，确保验证时原始 HTML 抓取也能命中
ADSENSE_LOADER = '<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-4401257427601930" crossorigin="anonymous"></script>'


def load_data():
    try:
        with open(CACHE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"generated_at": "", "source": "上海黄金交易所 (SGE)", "items": [],
                "primary": {}, "intl": {}}


def esc(s):
    return _html.escape(str(s if s is not None else ""), quote=True)


def fmt(v, d=2):
    try:
        return f"{float(v):,.{d}f}"
    except (TypeError, ValueError):
        return "—"


def delta(item):
    """返回 (涨跌额, 涨跌幅%, 方向 class)；数据不足返回 None。"""
    try:
        o = float(item.get("open"))
        l = float(item.get("last"))
        if not o:
            return None
        chg = l - o
        return chg, chg / o * 100, ("up" if chg > 0 else "down" if chg < 0 else "flat")
    except (TypeError, ValueError):
        return None


CSS = r"""
:root{
  --bg:#f4f6f9; --surface:#fff; --surface-2:#fafbfd; --ink:#111827; --ink-2:#3b4658;
  --sub:#77839a; --line:#e7ebf1; --line-2:#f0f2f6;
  --gold:#a9780f; --gold-2:#d9a92b; --gold-soft:#fdf7e7; --gold-ink:#8a6210;
  --up:#d4380d; --down:#129b63; --accent:#2f6fed;
  --brand:#0e1626; --brand-2:#16233b;
  --shadow:0 1px 2px rgba(16,24,40,.04),0 10px 28px rgba(16,24,40,.055);
  --shadow-lg:0 18px 48px rgba(10,18,34,.14);
  --r:16px; --r-sm:10px;
}
html.dark{
  --bg:#0a0e16; --surface:#121a27; --surface-2:#0e1521; --ink:#e9eef7; --ink-2:#c4cede;
  --sub:#8996ab; --line:#232e40; --line-2:#1b2433;
  --gold:#e0b341; --gold-2:#f0c75c; --gold-soft:#241f12; --gold-ink:#e8c260;
  --up:#ff6b4a; --down:#4ec98a; --accent:#6ea0ff;
  --brand:#0a0e16; --brand-2:#111b2c;
  --shadow:0 1px 2px rgba(0,0,0,.3),0 10px 28px rgba(0,0,0,.28);
  --shadow-lg:0 18px 48px rgba(0,0,0,.5);
}
*{box-sizing:border-box}
html{scroll-behavior:smooth;scroll-padding-top:112px}
body{margin:0;background:var(--bg);color:var(--ink);line-height:1.65;
  font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Hiragino Sans GB","Microsoft YaHei",sans-serif;
  -webkit-text-size-adjust:100%;-webkit-font-smoothing:antialiased}
a{color:inherit;text-decoration:none}
a:hover{color:var(--gold)}
button,input,select{font:inherit}
.num,.ov-val,.hero-price,.tk-v{font-variant-numeric:tabular-nums;font-feature-settings:"tnum"}
.wrap{max-width:1240px;margin:0 auto;padding:0 20px}
.up{color:var(--up)}.down{color:var(--down)}.flat{color:var(--sub)}

/* 顶部信息条 */
.topbar{background:var(--brand);color:#aab7cc;font-size:12px;letter-spacing:.2px}
.topbar .wrap{display:flex;align-items:center;gap:18px;min-height:34px;flex-wrap:wrap}
.topbar .tb-l{display:flex;align-items:center;gap:8px}
.live-dot{width:7px;height:7px;border-radius:50%;background:#31c48d;
  box-shadow:0 0 0 4px rgba(49,196,141,.15);display:inline-block;animation:pulse 2.4s infinite}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.45}}
.topbar .tb-r{margin-left:auto;display:flex;align-items:center;gap:14px}
.topbar a{color:#dbe4f2}
.topbar a:hover{color:var(--gold-2)}

/* 跑马灯 */
.ticker{background:var(--gold-soft);border-bottom:1px solid var(--line);overflow:hidden}
.ticker-inner{display:flex;align-items:center;min-height:38px}
.ticker-label{flex:0 0 auto;display:flex;align-items:center;gap:6px;padding:0 14px 0 24px;
  font-size:11px;font-weight:700;color:var(--gold-ink);letter-spacing:.6px;white-space:nowrap}
.ticker-view{overflow:hidden;flex:1;position:relative;
  -webkit-mask-image:linear-gradient(90deg,transparent,#000 24px,#000 calc(100% - 24px),transparent);
  mask-image:linear-gradient(90deg,transparent,#000 24px,#000 calc(100% - 24px),transparent)}
.ticker-track{display:flex;width:max-content;animation:marquee 46s linear infinite}
.ticker-view:hover .ticker-track{animation-play-state:paused}
@keyframes marquee{from{transform:translateX(0)}to{transform:translateX(-50%)}}
.tk{display:inline-flex;align-items:baseline;gap:7px;padding:0 20px;white-space:nowrap;font-size:12px;
  border-right:1px solid var(--line)}
.tk .tk-n{color:var(--ink-2);font-weight:600}
.tk .tk-v{font-weight:700;color:var(--ink)}
.tk .tk-c{font-size:11px;font-weight:700}

/* 导航 */
header.nav{position:sticky;top:0;z-index:60;background:var(--surface);
  border-bottom:1px solid var(--line)}
@supports(backdrop-filter:blur(1px)){
  header.nav{background:color-mix(in srgb,var(--surface) 90%,transparent);
    backdrop-filter:saturate(180%) blur(14px);-webkit-backdrop-filter:saturate(180%) blur(14px)}
}
.nav .wrap{display:flex;align-items:center;gap:28px;min-height:64px}
.brand{display:flex;align-items:center;gap:11px;flex:0 0 auto}
.brand-mark{width:36px;height:36px;border-radius:11px;display:grid;place-items:center;
  background:linear-gradient(145deg,#e6bd55,#b5840f);color:#231704;font-weight:800;font-size:14px;
  letter-spacing:-.5px;box-shadow:0 4px 12px rgba(180,132,11,.28)}
.brand-txt strong{display:block;font-size:15px;line-height:1.15;letter-spacing:.3px}
.brand-txt small{display:block;font-size:9px;letter-spacing:1.4px;color:var(--sub);text-transform:uppercase;margin-top:3px}
.nav-menu{display:flex;align-items:center;gap:4px;flex:1}
.nav-menu a{font-size:13.5px;color:var(--ink-2);padding:8px 12px;border-radius:8px;transition:.15s;white-space:nowrap}
.nav-menu a:hover{background:var(--surface-2);color:var(--gold)}
.nav-menu a.active{color:var(--gold);font-weight:600}
.nav-act{display:flex;align-items:center;gap:10px;flex:0 0 auto}
.icon-btn{background:var(--surface-2);border:1px solid var(--line);color:var(--ink-2);
  border-radius:9px;padding:7px 11px;font-size:13px;cursor:pointer;transition:.15s;white-space:nowrap}
.icon-btn:hover{border-color:var(--gold-2);color:var(--gold)}
.nav-toggle{display:none;background:none;border:1px solid var(--line);color:var(--ink);
  border-radius:9px;padding:7px 10px;font-size:17px;cursor:pointer;line-height:1}

/* Hero */
.hero-wrap{padding:28px 0 8px}
.hero{position:relative;overflow:hidden;border-radius:22px;color:#fff;
  background:radial-gradient(900px 420px at 82% -10%,rgba(224,179,65,.26),transparent 62%),
             radial-gradient(600px 320px at 8% 110%,rgba(47,111,237,.18),transparent 60%),
             linear-gradient(125deg,#101a2d 0%,#16243d 52%,#0d1424 100%);
  box-shadow:var(--shadow-lg)}
.hero::before{content:"";position:absolute;inset:0;opacity:.16;pointer-events:none;
  background-image:linear-gradient(rgba(255,255,255,.09) 1px,transparent 1px),
                   linear-gradient(90deg,rgba(255,255,255,.09) 1px,transparent 1px);
  background-size:44px 44px;-webkit-mask-image:linear-gradient(90deg,#000,transparent 78%);
  mask-image:linear-gradient(90deg,#000,transparent 78%)}
.hero::after{content:"";position:absolute;right:-60px;top:-90px;width:320px;height:320px;border-radius:50%;
  border:1px solid rgba(224,179,65,.22);box-shadow:0 0 0 44px rgba(224,179,65,.045),0 0 0 88px rgba(224,179,65,.03)}
.hero-grid{position:relative;display:grid;grid-template-columns:minmax(0,1.15fr) minmax(0,1fr);gap:34px;
  padding:38px 40px 34px;z-index:1}
.eyebrow{display:inline-flex;align-items:center;gap:8px;font-size:11px;letter-spacing:1.2px;
  text-transform:uppercase;color:#e0b341;font-weight:700}
.eyebrow::before{content:"";width:18px;height:1px;background:#e0b341}
.hero h1{font-size:27px;line-height:1.35;margin:14px 0 8px;font-weight:700;letter-spacing:.3px}
.hero p.lead{color:#aab8cf;font-size:13.5px;margin:0 0 24px;max-width:430px}
.hero-price-box{display:flex;align-items:flex-end;gap:16px;flex-wrap:wrap}
.hero-price{font-size:58px;line-height:1;font-weight:750;letter-spacing:-2px;color:#fff}
.hero-unit{font-size:14px;color:#aab8cf;margin-bottom:7px}
.hero-chg{display:inline-flex;align-items:center;gap:8px;margin-bottom:8px;font-size:14px;font-weight:700;
  padding:5px 11px;border-radius:8px;background:rgba(255,255,255,.08);color:#e6edf8}
.hero-chg.up{color:#ff9a7d;background:rgba(212,56,13,.18)}
.hero-chg.down{color:#6fe0aa;background:rgba(18,155,99,.18)}
.hero-meta{margin-top:16px;display:flex;align-items:center;gap:16px;flex-wrap:wrap;color:#9fb0c9;font-size:11.5px}
.hero-meta span{display:inline-flex;align-items:center;gap:6px}
.hero-side{display:grid;grid-template-columns:1fr 1fr;gap:12px;align-content:center}
.hs{background:rgba(255,255,255,.055);border:1px solid rgba(255,255,255,.1);border-radius:14px;
  padding:15px 16px;backdrop-filter:blur(6px)}
.hs .k{font-size:11.5px;color:#a9b8cf;display:flex;align-items:center;gap:6px}
.hs .v{font-size:22px;font-weight:700;margin-top:7px;letter-spacing:-.5px}
.hs .t{font-size:10.5px;color:#8c9db8;margin-top:3px}
.hs .v.up{color:#ff8f72}.hs .v.down{color:#5fd6a0}

/* 概览卡 */
.ov-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:14px;margin:18px 0 4px}
.ov{position:relative;background:var(--surface);border:1px solid var(--line);border-radius:var(--r);
  padding:18px;box-shadow:var(--shadow);overflow:hidden;transition:transform .18s,box-shadow .18s}
.ov:hover{transform:translateY(-3px);box-shadow:var(--shadow-lg)}
.ov::before{content:"";position:absolute;left:0;top:0;bottom:0;width:3px;background:var(--gold-2);opacity:.85}
.ov:nth-child(2)::before{background:var(--accent)}
.ov:nth-child(3)::before{background:#8b5cf6}
.ov:nth-child(4)::before{background:#0ea5a5}
.ov .k{color:var(--sub);font-size:12px;display:flex;align-items:center;justify-content:space-between;gap:8px}
.ov .ic{width:26px;height:26px;border-radius:8px;background:var(--gold-soft);color:var(--gold);
  display:grid;place-items:center;font-size:13px;flex:0 0 auto}
.ov-val{font-size:27px;font-weight:730;letter-spacing:-.7px;margin-top:9px;line-height:1.2}
.ov-val.up{color:var(--up)}.ov-val.down{color:var(--down)}
.ov .u{color:var(--sub);font-size:12px;margin-left:4px;font-weight:400}
.ov .t{color:var(--sub);font-size:11.5px;margin-top:6px}

/* 区块标题 */
.section{padding-top:38px}
.section-head{display:flex;align-items:flex-end;justify-content:space-between;gap:16px;margin-bottom:16px;flex-wrap:wrap}
.section-head .lbl{font-size:11px;letter-spacing:1.4px;text-transform:uppercase;color:var(--gold);font-weight:700}
.section-head h2{font-size:21px;margin:5px 0 0;letter-spacing:-.3px;font-weight:700}
.section-head p{color:var(--sub);font-size:13px;margin:5px 0 0}
.section-head .side{color:var(--sub);font-size:12px}

/* 卡片 / 表格 */
.card{background:var(--surface);border:1px solid var(--line);border-radius:var(--r);
  padding:20px;box-shadow:var(--shadow)}
.card-head{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:16px;flex-wrap:wrap}
.card-head h3{font-size:15px;margin:0;display:flex;align-items:center;gap:8px;font-weight:700}
.card-head h3::before{content:"";width:3px;height:15px;border-radius:2px;background:var(--gold-2)}
.badge{display:inline-flex;align-items:center;gap:5px;font-size:11px;color:var(--sub);
  background:var(--surface-2);border:1px solid var(--line);border-radius:20px;padding:4px 10px}
table{width:100%;border-collapse:collapse;font-size:13.5px}
th,td{padding:12px 10px;text-align:right;border-bottom:1px solid var(--line-2);white-space:nowrap}
th:first-child,td:first-child,th:nth-child(2),td:nth-child(2){text-align:left}
th{color:var(--sub);font-weight:600;font-size:11.5px;letter-spacing:.3px;background:var(--surface-2)}
tbody tr{transition:background .15s}
tbody tr:hover{background:var(--surface-2)}
tbody tr:last-child td{border-bottom:none}
.lbl{font-weight:650}.sym{color:var(--sub);font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:12px}
.num{font-variant-numeric:tabular-nums}.strong{font-weight:730;color:var(--ink);font-size:15px}
.unit{color:var(--sub);font-size:12px}
.chg{font-weight:700;font-size:12.5px}
.spark{width:76px;height:26px;display:block;margin-left:auto}
.tfoot{margin-top:12px;color:var(--sub);font-size:11.5px;line-height:1.7}

/* 图表 */
.charts{display:grid;grid-template-columns:1fr 1fr;gap:16px}
.charts .full{grid-column:1/-1}
.chart-box{height:262px;position:relative}
.chart-box.tall{height:280px}
.chip-row{display:flex;gap:7px;flex-wrap:wrap}
.chip{font-size:11px;padding:4px 9px;border-radius:20px;background:var(--surface-2);
  border:1px solid var(--line);color:var(--sub)}

/* 提醒 */
.alert-grid{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:20px}
.alert-row{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:12px}
.alert-row select,.alert-row input{background:var(--surface-2);border:1px solid var(--line);
  color:var(--ink);border-radius:var(--r-sm);padding:9px 11px;font-size:13.5px;min-width:0}
.alert-row input{width:126px}
.btn{background:var(--gold);color:#fff;border:none;border-radius:var(--r-sm);padding:9px 16px;
  font-size:13.5px;font-weight:600;cursor:pointer;transition:.15s;display:inline-block}
.btn:hover{background:var(--gold-ink);color:#fff}
.btn.ghost{background:var(--surface-2);border:1px solid var(--line);color:var(--ink-2)}
.btn.ghost:hover{border-color:var(--gold-2);color:var(--gold);background:var(--gold-soft)}
.hint{color:var(--sub);font-size:11.5px;line-height:1.75;margin-top:12px}
#alertList{list-style:none;padding:0;margin:0;display:flex;flex-direction:column;gap:8px}
#alertList li{display:flex;align-items:center;gap:9px;background:var(--surface-2);
  border:1px solid var(--line);border-radius:var(--r-sm);padding:10px 13px;font-size:13.5px}
.alert-empty{color:var(--sub);font-size:13px;justify-content:center;padding:20px!important}
.a-sym{font-weight:650}.a-cond{color:var(--sub)}.a-val{font-weight:650;font-variant-numeric:tabular-nums}
.a-del{margin-left:auto;background:none;border:none;color:var(--sub);cursor:pointer;font-size:14px;padding:2px 6px}
.a-del:hover{color:var(--up)}
.steps{margin:0 0 14px;padding-left:18px;color:var(--ink-2);font-size:12.5px;line-height:1.9}

/* 科普 */
.prose-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px}
.prose-card{background:var(--surface);border:1px solid var(--line);border-radius:var(--r);
  padding:22px;box-shadow:var(--shadow)}
.prose-card .no{font-size:11px;letter-spacing:1px;color:var(--gold);font-weight:700}
.prose-card h3{font-size:16px;margin:8px 0 10px;letter-spacing:-.2px}
.prose-card p{color:var(--ink-2);font-size:13.5px;margin:0 0 10px;line-height:1.85}
.prose-card p:last-child{margin-bottom:0}
.faq-list{margin-top:16px;background:var(--surface);border:1px solid var(--line);
  border-radius:var(--r);overflow:hidden;box-shadow:var(--shadow)}
.faq-list details{border-bottom:1px solid var(--line-2)}
.faq-list details:last-child{border-bottom:none}
.faq-list summary{padding:15px 20px;cursor:pointer;font-size:14px;font-weight:600;
  display:flex;align-items:center;gap:10px;list-style:none}
.faq-list summary::-webkit-details-marker{display:none}
.faq-list summary::before{content:"+";color:var(--gold);font-size:17px;font-weight:600;line-height:1}
.faq-list details[open] summary::before{content:"−"}
.faq-list details[open] summary{color:var(--gold)}
.faq-list .ans{padding:0 20px 17px 40px;color:var(--ink-2);font-size:13.5px;line-height:1.85}

/* 广告位 */
.ad-slot{margin:22px 0;border:1px dashed var(--line);border-radius:12px;padding:16px;
  text-align:center;color:var(--sub);font-size:11.5px;background:var(--surface-2);min-height:60px}
.ad-slot.ad-active{border-style:solid;background:transparent;padding:8px}

/* 说明条 */
.note-strip{display:flex;align-items:center;gap:14px;flex-wrap:wrap;background:var(--surface);
  border:1px solid var(--line);border-radius:var(--r);padding:16px 20px;margin-top:22px;box-shadow:var(--shadow)}
.note-strip .ni{width:34px;height:34px;border-radius:10px;background:var(--gold-soft);color:var(--gold);
  display:grid;place-items:center;font-size:16px;flex:0 0 auto}
.note-strip .nt{flex:1;min-width:220px}
.note-strip strong{font-size:13.5px;display:block}
.note-strip span{font-size:12px;color:var(--sub)}

/* 页脚 */
footer.site{margin-top:52px;background:var(--brand);color:#98a8c0;font-size:12.5px}
.foot-grid{display:grid;grid-template-columns:1.7fr 1fr 1fr 1fr 1fr;gap:28px;padding:44px 0 34px}
.foot-brand .brand-txt strong{color:#fff}
.foot-brand p{margin:14px 0 0;font-size:12.5px;line-height:1.9;max-width:290px}
.foot-col h4{color:#fff;font-size:13px;margin:0 0 14px;font-weight:650}
.foot-col a{display:block;padding:5px 0;color:#98a8c0;font-size:12.5px}
.foot-col a:hover{color:var(--gold-2)}
.foot-bottom{border-top:1px solid rgba(255,255,255,.09);padding:18px 0 26px;font-size:11.5px;
  line-height:1.85;color:#7e8ea8}
.foot-bottom strong{color:#b9c6da}

/* 悬浮 */
.back-top{position:fixed;right:22px;bottom:22px;width:42px;height:42px;border-radius:12px;
  background:var(--surface);border:1px solid var(--line);color:var(--ink-2);cursor:pointer;
  box-shadow:var(--shadow-lg);display:none;place-items:center;font-size:17px;z-index:50}
.back-top.show{display:grid}
.back-top:hover{color:var(--gold);border-color:var(--gold-2)}

/* 内页 */
.page-hero{padding:36px 0 6px}
.page-hero .eyebrow{color:var(--gold)}
.page-hero h1{font-size:30px;margin:10px 0 8px;letter-spacing:-.5px}
.page-hero p{color:var(--sub);font-size:14px;margin:0;max-width:720px}
.doc{background:var(--surface);border:1px solid var(--line);border-radius:var(--r);
  padding:30px 34px;box-shadow:var(--shadow);margin-top:22px}
.doc h2{font-size:18px;margin:30px 0 10px;padding-top:22px;border-top:1px solid var(--line-2)}
.doc h2:first-child{margin-top:0;padding-top:0;border-top:none}
.doc h3{font-size:15px;margin:20px 0 8px}
.doc p,.doc li{color:var(--ink-2);font-size:14px;line-height:1.95}
.doc ul{padding-left:20px;margin:8px 0}
.doc code{background:var(--surface-2);border:1px solid var(--line);border-radius:6px;
  padding:2px 7px;font-size:12.5px;color:var(--gold-ink)}
.doc .muted{color:var(--sub);font-size:12.5px}
.doc .callout{background:var(--gold-soft);border-left:3px solid var(--gold-2);
  padding:14px 18px;border-radius:0 var(--r-sm) var(--r-sm) 0;margin:16px 0}
.doc .callout p{margin:0;color:var(--gold-ink);font-size:13px}

/* 响应式 */
@media(max-width:1024px){
  .hero-grid{grid-template-columns:1fr;gap:24px;padding:32px}
  .hero-side{grid-template-columns:repeat(4,1fr)}
  .ov-grid{grid-template-columns:repeat(2,minmax(0,1fr))}
  .foot-grid{grid-template-columns:repeat(4,1fr);gap:22px;padding:34px 0 26px}
  .foot-brand{grid-column:1/-1}
  .foot-brand p{max-width:none}
}
@media(max-width:900px){
  .nav-menu{display:none;position:absolute;top:64px;left:0;right:0;background:var(--surface);
    border-bottom:1px solid var(--line);flex-direction:column;align-items:stretch;padding:10px 18px 16px;
    box-shadow:var(--shadow-lg)}
  .nav-menu.open{display:flex}
  .nav-menu a{padding:11px 12px}
  .nav-toggle{display:block}
  .nav .wrap{gap:12px}
  .charts{grid-template-columns:1fr}
  .charts .full{grid-column:auto}
  .prose-grid{grid-template-columns:1fr}
  .alert-grid{grid-template-columns:1fr}
}
@media(max-width:720px){
  .wrap{padding:0 16px}
  html{scroll-padding-top:88px}
  .ticker-label{padding-left:16px}
  .hero-grid{padding:26px 22px}
  .hero h1{font-size:22px}
  .hero-price{font-size:46px;letter-spacing:-1.5px}
  .hero-chg{flex-basis:100%;max-width:max-content;margin:2px 0 0}
  .hero-side{grid-template-columns:1fr 1fr}
  .ov-grid{gap:10px}
  .ov{padding:14px}
  .ov-val{font-size:22px}
  .section{padding-top:30px}
  .section-head h2{font-size:19px}
  .card{padding:16px}
  .chart-box{height:230px}
  .doc{padding:22px 20px}
  .foot-grid{grid-template-columns:1fr 1fr;gap:16px 20px;padding:30px 0 22px}
  .foot-brand{grid-column:1/-1}
  .foot-brand p{margin-top:8px;font-size:12px;line-height:1.7}
  .foot-col h4{margin-bottom:8px;font-size:12.5px}
  .foot-col a{padding:4px 0;font-size:12px}
  table,thead,tbody,th,td,tr{display:block}
  thead{display:none}
  tbody tr{border:1px solid var(--line);border-radius:12px;margin-bottom:10px;padding:6px 12px;background:var(--surface-2)}
  td{display:flex;justify-content:space-between;align-items:center;padding:8px 2px;border:none;text-align:right;white-space:normal}
  td::before{content:attr(data-label);color:var(--sub);font-size:12px;font-weight:600;text-align:left;flex:0 0 auto}
  td.lbl,td.sym{text-align:right}
  .spark{width:64px}
}

@media(max-width:420px){
  .hero-side{grid-template-columns:1fr 1fr;gap:9px}
  .hs{padding:12px}
  .hs .v{font-size:19px}
  .ov-grid{grid-template-columns:1fr}
  .foot-grid{gap:14px 16px}
  .topbar .tb-r{width:100%;margin-left:0;padding-bottom:6px}
}
@media(max-width:360px){
  .hero-side{grid-template-columns:1fr}
}
@media(prefers-reduced-motion:reduce){
  *{animation-duration:.001ms!important;transition-duration:.001ms!important}
  html{scroll-behavior:auto}
}

/* ============ 实物金价参考 ============ */
.phys-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px}
.phys-card{position:relative;background:var(--surface);border:1px solid var(--line);border-radius:var(--r);
  padding:18px;box-shadow:var(--shadow);overflow:hidden;transition:transform .18s,box-shadow .18s}
.phys-card:hover{transform:translateY(-3px);box-shadow:var(--shadow-lg)}
.phys-card.real{border-color:color-mix(in srgb,var(--gold-2) 45%,var(--line))}
.phys-card.real::before{content:"";position:absolute;left:0;top:0;bottom:0;width:3px;background:var(--gold)}
.phys-card .pk{display:flex;align-items:center;gap:8px;color:var(--sub);font-size:12px;font-weight:600}
.phys-card .pk .dot{width:8px;height:8px;border-radius:50%;background:var(--gold-2);flex:0 0 auto}
.phys-card .pv{font-size:25px;font-weight:730;letter-spacing:-.6px;margin-top:10px;line-height:1.1}
.phys-card .pu{color:var(--sub);font-size:11.5px;margin-left:4px;font-weight:400}
.phys-card .pn{color:var(--sub);font-size:11.5px;margin-top:8px;line-height:1.6}
.assume-row{display:flex;flex-wrap:wrap;gap:12px;align-items:center;margin:16px 0 4px}
.assume-row .a-item{display:flex;flex-direction:column;gap:5px}
.assume-row label{font-size:11.5px;color:var(--sub)}
.assume-row input{width:80px;background:var(--surface-2);border:1px solid var(--line);color:var(--ink);
  border-radius:8px;padding:7px 9px;font-size:13.5px}
.btn.mini{padding:6px 13px;font-size:12.5px}
.phys-note{color:var(--sub);font-size:11.5px;line-height:1.8;margin-top:14px}
.phys-note b{color:var(--gold-ink)}

/* ============ 工具计算器 ============ */
.tool-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px}
.tool-card{background:var(--surface);border:1px solid var(--line);border-radius:var(--r);padding:20px;box-shadow:var(--shadow)}
.tool-card h3{font-size:15px;margin:0 0 14px;display:flex;align-items:center;gap:8px;font-weight:700}
.tool-card h3::before{content:"";width:3px;height:15px;border-radius:2px;background:var(--accent)}
.field{display:flex;flex-direction:column;gap:5px;margin-bottom:11px}
.field label{font-size:12px;color:var(--sub)}
.field input,.field select{background:var(--surface-2);border:1px solid var(--line);color:var(--ink);
  border-radius:8px;padding:9px 11px;font-size:13.5px;width:100%}
.field .hintu{font-size:11px;color:var(--sub);margin-top:-2px}
.tool-out{margin-top:8px;padding:14px 16px;border-radius:var(--r-sm);background:var(--gold-soft);
  color:var(--gold-ink);font-size:13.5px;line-height:1.85;border:1px solid color-mix(in srgb,var(--gold-2) 30%,var(--line))}
.tool-out b{font-size:19px;color:var(--gold-ink);font-variant-numeric:tabular-nums}
.tool-card .src{font-size:11px;color:var(--sub);margin-top:10px;line-height:1.7}

/* ============ 术语表 ============ */
.glossary{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px}
.gloss{background:var(--surface);border:1px solid var(--line);border-radius:var(--r-sm);padding:15px 17px;box-shadow:var(--shadow)}
.gloss h4{margin:0 0 6px;font-size:13.5px;color:var(--gold-ink);display:flex;align-items:center;gap:8px;font-weight:700}
.gloss h4::before{content:"";width:6px;height:6px;border-radius:2px;background:var(--gold-2);flex:0 0 auto}
.gloss p{margin:0;font-size:12.5px;color:var(--ink-2);line-height:1.75}

/* ============ 快捷入口 / 相关板块 ============ */
.quick-row{display:flex;flex-wrap:wrap;gap:10px;margin-top:18px}
.quick-row a{padding:9px 16px;border:1px solid var(--line);border-radius:30px;font-size:13px;
  background:var(--surface);color:var(--ink-2);box-shadow:var(--shadow);transition:.15s;white-space:nowrap}
.quick-row a:hover{border-color:var(--gold-2);color:var(--gold);background:var(--gold-soft)}
.rel-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin-top:14px}
.rel{background:var(--surface);border:1px solid var(--line);border-radius:var(--r-sm);padding:16px;box-shadow:var(--shadow);transition:.15s}
.rel:hover{transform:translateY(-2px);box-shadow:var(--shadow-lg);border-color:color-mix(in srgb,var(--gold-2) 40%,var(--line))}
.rel .rt{font-size:14px;font-weight:700;display:flex;align-items:center;gap:7px}
.rel .rt::before{content:"◈";color:var(--gold-2)}
.rel p{margin:7px 0 0;font-size:12px;color:var(--sub);line-height:1.65}

@media(max-width:900px){
  .phys-grid,.glossary,.tool-grid{grid-template-columns:1fr}
  .rel-grid{grid-template-columns:1fr 1fr}
}
@media(max-width:540px){
  .rel-grid{grid-template-columns:1fr}
}

/* ============ 一级导航：大标签（与二级条明确区分） ============ */
.nav-top{display:flex;align-items:stretch;gap:0}
.nav-menu{display:flex;align-items:stretch;gap:0;flex:1;margin-left:18px}
.nav-menu .ntab{display:inline-flex;align-items:center;padding:0 22px;font-size:16px;font-weight:750;
  color:var(--ink-2);letter-spacing:.5px;border-bottom:3px solid transparent;transition:.15s;white-space:nowrap}
.nav-menu .ntab:hover{color:var(--gold)}
.nav-menu .ntab.active{color:var(--gold);border-bottom-color:var(--gold);background:var(--gold-soft)}
@media(max-width:900px){
  .nav-menu{display:none;position:absolute;top:64px;left:0;right:0;background:var(--surface);
    border-bottom:1px solid var(--line);flex-direction:column;padding:8px;z-index:70}
  .nav-menu.open{display:flex}
  .nav-menu .ntab{padding:13px 18px;border-bottom:1px solid var(--line-2);border-left:3px solid transparent}
  .nav-menu .ntab.active{border-bottom-color:var(--line-2);border-left-color:var(--gold)}
}

/* ============ 快讯流 ============ */
.news-list{display:flex;flex-direction:column;gap:0}
.news-item{display:flex;gap:14px;padding:15px 4px;border-bottom:1px solid var(--line);align-items:flex-start}
.news-item:last-child{border-bottom:none}
.news-item .n-time{flex:0 0 88px;font-size:11.5px;color:var(--sub);font-variant-numeric:tabular-nums;padding-top:2px}
.news-item .n-body{flex:1}
.news-item .n-title{font-size:14px;font-weight:650;line-height:1.5;margin-bottom:4px}
.news-item .n-text{font-size:12.5px;color:var(--ink-2);line-height:1.7}
.news-item .n-src{flex:0 0 60px;font-size:11px;color:var(--sub);text-align:right;padding-top:2px}
.news-item.hot .n-title{color:var(--gold-ink)}
.news-empty{padding:30px;text-align:center;color:var(--sub);font-size:13px}

/* ============ 财经日历 ============ */
.cal-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}
.cal-item{background:var(--surface);border:1px solid var(--line);border-radius:var(--r-sm);padding:16px;
  box-shadow:var(--shadow);border-left:4px solid var(--line)}
.cal-item.imp-high{border-left-color:#e11d48}
.cal-item.imp-mid{border-left-color:var(--gold-2)}
.cal-item.imp-low{border-left-color:#6b7280}
.cal-item .ci-date{font-size:11.5px;color:var(--sub);font-variant-numeric:tabular-nums;letter-spacing:.3px}
.cal-item .ci-name{font-size:14px;font-weight:700;margin:5px 0 6px;line-height:1.45}
.cal-item .ci-meta{font-size:11.5px;color:var(--sub);line-height:1.7}
.cal-item .ci-imp{display:inline-flex;align-items:center;gap:4px;font-size:10.5px;font-weight:700;
  padding:2px 8px;border-radius:20px;margin-top:8px}
.imp-high .ci-imp{background:color-mix(in srgb,#e11d48 12%,transparent);color:#e11d48}
.imp-mid .ci-imp{background:var(--gold-soft);color:var(--gold-ink)}
.imp-low .ci-imp{background:color-mix(in srgb,#6b7280 12%,transparent);color:#6b7280}
.fomc-table{width:100%;border-collapse:collapse;font-size:12.5px;margin-top:8px}
.fomc-table th{font-size:11px;color:var(--sub);text-align:left;padding:8px 10px;background:var(--surface-2);font-weight:650}
.fomc-table td{padding:10px;border-bottom:1px solid var(--line);color:var(--ink-2);vertical-align:top}
.fomc-table tr:last-child td{border-bottom:none}
.fomc-table .star{color:var(--gold);font-weight:700}

/* ============ 投资学院 ============ */
.acad-cats{display:flex;flex-wrap:wrap;gap:10px;margin-bottom:20px}
.acad-cat{padding:8px 16px;border:1px solid var(--line);border-radius:30px;font-size:12.5px;font-weight:600;
  background:var(--surface);color:var(--ink-2);cursor:pointer;transition:.15s}
.acad-cat:hover{border-color:var(--gold-2);color:var(--gold);background:var(--gold-soft)}
.acad-cat.sel{background:var(--gold);color:#fff;border-color:var(--gold)}
.acad-card{background:var(--surface);border:1px solid var(--line);border-radius:var(--r-sm);padding:20px;
  box-shadow:var(--shadow);transition:.15s;display:flex;flex-direction:column}
.acad-card:hover{transform:translateY(-3px);box-shadow:var(--shadow-lg)}
.acad-card .a-tag{display:inline-block;font-size:10.5px;font-weight:700;letter-spacing:.4px;padding:2px 9px;
  border-radius:20px;background:var(--gold-soft);color:var(--gold-ink);margin-bottom:10px;align-self:flex-start}
.acad-card h3{font-size:15px;margin:0 0 8px;line-height:1.5;font-weight:700}
.acad-card p{margin:0;font-size:12.5px;color:var(--ink-2);line-height:1.75;flex:1}
.acad-card .a-no{font-size:11px;color:var(--sub);margin-top:12px;letter-spacing:.5px}

/* ============ 数据中心指标卡 ============ */
.ind-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:14px}
.ind-card{background:var(--surface);border:1px solid var(--line);border-radius:var(--r-sm);padding:18px;
  box-shadow:var(--shadow);text-align:center}
.ind-card .ik{font-size:11.5px;color:var(--sub);font-weight:600;margin-bottom:8px}
.ind-card .iv{font-size:24px;font-weight:730;letter-spacing:-.5px;font-variant-numeric:tabular-nums}
.ind-card .iu{font-size:11px;color:var(--sub);margin-top:5px}
.ind-card .iv.up{color:#d4380d}
.ind-card .iv.down{color:#129b63}

@media(max-width:900px){
  .cal-grid{grid-template-columns:1fr}
  .ind-grid{grid-template-columns:1fr 1fr}
}
@media(max-width:540px){
  .ind-grid{grid-template-columns:1fr}
}

/* ============ 常驻二级导航条（小字轻量,与一级大标签区分） ============ */
.subnav{background:var(--surface-2);border-bottom:1px solid var(--line)}
.subnav-inner{display:flex;align-items:center;gap:12px;min-height:36px;flex-wrap:wrap}
.subnav-home{font-size:11.5px;color:var(--sub);white-space:nowrap}
.subnav-home a{color:var(--sub)}
.subnav-home a:hover{color:var(--gold)}
.subnav-home i{font-style:normal;margin:0 3px;opacity:.5}
.subnav-home b{color:var(--ink-2);font-weight:650}
.subnav-links{display:flex;align-items:center;gap:0;flex-wrap:wrap}
.subnav-links a{font-size:12px;color:var(--sub);padding:4px 11px;font-weight:500;white-space:nowrap;transition:.13s;
  border-right:1px solid var(--line)}
.subnav-links a:last-child{border-right:none}
.subnav-links a:hover{color:var(--gold)}
@media(max-width:640px){
  .subnav-inner{gap:6px;padding:5px 20px}
  .subnav-home{width:100%}
  .subnav-links a{border-right:none;padding:4px 8px}
}

/* ============ 金投网式三栏门户布局 ============ */
.portal{display:grid;grid-template-columns:180px minmax(0,1fr) 300px;gap:14px;align-items:start;margin:16px 0}
.portal-l, .portal-r{position:sticky;top:12px;display:flex;flex-direction:column;gap:12px}
.pmod{background:var(--surface);border:1px solid var(--line);border-radius:var(--r-sm);overflow:hidden}
.pmod-h{padding:8px 12px;font-size:13px;font-weight:750;color:var(--ink);background:var(--surface-2);
  border-bottom:1px solid var(--line);display:flex;align-items:center;justify-content:space-between}
.pmod-h::before{content:"";width:3px;height:13px;background:var(--gold);border-radius:2px;margin-right:8px;flex:0 0 auto}
.pmod-h .more{font-size:11px;color:var(--sub);font-weight:500}
.pmod-h .more:hover{color:var(--gold)}
.pmod-b{padding:8px 10px;font-size:12.5px}
.pmod-b .mini-list{list-style:none;margin:0;padding:0}
.pmod-b .mini-list li{padding:6px 2px;border-bottom:1px dashed var(--line-2);line-height:1.55}
.pmod-b .mini-list li:last-child{border-bottom:none}
.pmod-b .mini-list a{color:var(--ink-2);font-size:12px}
.pmod-b .mini-list a:hover{color:var(--gold)}
.pmod-b .mini-list .t{color:var(--sub);font-size:10.5px;margin-right:6px;font-variant-numeric:tabular-nums}
.side-nav{list-style:none;margin:0;padding:0}
.side-nav li a{display:block;padding:7px 10px;font-size:12.5px;color:var(--ink-2);border-radius:6px;line-height:1.5}
.side-nav li a:hover{background:var(--gold-soft);color:var(--gold)}
.side-nav li a.cur{background:var(--gold-soft);color:var(--gold);font-weight:650}
.portal-main{display:flex;flex-direction:column;gap:14px;min-width:0}

/* 模块盒（中栏,金投网式标题栏+更多） */
.m\boxed{background:var(--surface);border:1px solid var(--line);border-radius:var(--r-sm);overflow:hidden}
.mbox-h{padding:10px 14px;font-size:14px;font-weight:750;background:var(--surface-2);border-bottom:1px solid var(--line);
  display:flex;align-items:center;justify-content:space-between}
.mbox-h .mh-l{display:flex;align-items:center;gap:8px}
.mbox-h .mh-l::before{content:"";width:3px;height:15px;background:var(--gold);border-radius:2px}
.mbox-h .more{font-size:11.5px;color:var(--sub);font-weight:500}
.mbox-h .more:hover{color:var(--gold)}
.mbox-b{padding:12px 14px}
.mbox-b.tight{padding:0}
.portal-main .card{overflow-x:auto}
.portal-main table{min-width:560px}
.mbox-note{font-size:11px;color:var(--sub);padding:8px 14px;background:var(--surface-2);border-top:1px solid var(--line);line-height:1.7}

/* 紧凑价格横栏（三栏模式下的 hero 替代） */
.price-strip{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:1px;background:var(--line);
  border:1px solid var(--line);border-radius:var(--r-sm);overflow:hidden}
.price-cell{background:var(--surface);padding:12px 14px}
.price-cell .pk{font-size:11px;color:var(--sub);margin-bottom:6px}
.price-cell .pv{font-size:22px;font-weight:750;letter-spacing:-.5px;font-variant-numeric:tabular-nums;line-height:1.15}
.price-cell .pt{font-size:10.5px;color:var(--sub);margin-top:4px}
.ov-strip{display:flex;gap:22px;flex-wrap:wrap;padding:8px 14px;margin-top:8px;font-size:11.5px;color:var(--sub);
  background:var(--surface);border:1px solid var(--line);border-radius:var(--r-sm)}
.ov-strip b{margin-left:4px;font-variant-numeric:tabular-nums}

/* ============ 三大报价模块(金投网式,tab 切换品种) ============ */
.three-quote{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;margin-top:14px}
.tq{background:var(--surface);border:1px solid var(--line);border-radius:var(--r-sm);overflow:hidden}
.tq-tabs{display:flex;align-items:center;background:var(--surface-2);border-bottom:1px solid var(--line);padding:0 4px;overflow-x:auto}
.tq-tabs b{font-size:12.5px;color:var(--gold-ink);padding:9px 10px;letter-spacing:1px;white-space:nowrap}
.tq-tabs a{font-size:12px;color:var(--sub);padding:9px 9px;cursor:pointer;white-space:nowrap;
  border-bottom:2px solid transparent;transition:.13s}
.tq-tabs a:hover{color:var(--ink)}
.tq-tabs a.on{color:var(--gold);border-bottom-color:var(--gold);font-weight:650}
.tq-mode{margin-left:auto;display:inline-flex}
.tq-mode a{font-size:11px;padding:9px 8px;color:var(--sub)}
.tq-mode a.on{color:var(--ink);border-bottom-color:var(--ink)}
.tq-top{padding:12px 14px 6px}
.tq-name{font-size:12px;color:var(--sub);margin-bottom:3px}
.tq-priceline{display:flex;align-items:baseline;gap:8px;flex-wrap:wrap}
.tq-price{font-size:30px;font-weight:780;letter-spacing:-1px;font-variant-numeric:tabular-nums;line-height:1.05}
.tq-unit{font-size:11px;color:var(--sub)}
.tq-chg{font-size:12.5px;font-variant-numeric:tabular-nums}
.tq-chg .up{color:var(--up)}
.tq-chg .down{color:var(--down)}
.tq-chart{height:132px;padding:2px 8px 8px;position:relative}
.tq-chart canvas{width:100%!important;height:100%!important}
.tq-spark{flex:0 0 118px;text-align:right}
.tq-spark svg{width:118px;height:46px}
.tq-sub{font-size:11px;color:var(--sub);line-height:1.6}

/* ============ 全宽大行情表(金投网式,紧凑+色块涨跌) ============ */
.mega-table{width:100%;border-collapse:collapse;font-size:12.5px}
.mega-table th{font-size:11.5px;color:var(--sub);background:var(--surface-2);padding:8px 10px;text-align:right;
  font-weight:650;white-space:nowrap;border-bottom:1px solid var(--line)}
.mega-table th:first-child,.mega-table td:first-child{text-align:left}
.mega-table td{padding:8px 10px;text-align:right;border-bottom:1px solid var(--line-2);
  font-variant-numeric:tabular-nums;white-space:nowrap;color:var(--ink)}
.mega-table tbody tr:nth-child(even){background:color-mix(in srgb,var(--surface-2) 50%,transparent)}
.mega-table tbody tr:hover{background:var(--gold-soft)}
.mega-table .sym{color:var(--sub);font-size:11px}
.pill{display:inline-block;padding:2px 9px;border-radius:12px;font-size:12px;font-weight:650}
.pill.up{background:color-mix(in srgb,var(--up) 15%,transparent);color:var(--up)}
.pill.down{background:color-mix(in srgb,var(--down) 15%,transparent);color:var(--down)}
.pill.flat{background:var(--surface-2);color:var(--sub)}
.mega-table .grow td{background:var(--surface-2);color:var(--gold-ink);font-size:11.5px;font-weight:750;
  letter-spacing:1.5px;padding:7px 10px;text-align:left;border-bottom:1px solid var(--line)}

@media(max-width:1080px){
  .portal{grid-template-columns:160px minmax(0,1fr) 260px}
}
@media(max-width:900px){
  .portal{grid-template-columns:1fr;gap:12px}
  .portal-l,.portal-r{position:static}
  .price-strip{grid-template-columns:1fr 1fr}
}

/* ============ 首页频道导航网格（5 板块层级一屏展示） ============ */
.chan-grid{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:12px}
.chan{background:var(--surface);border:1px solid var(--line);border-radius:var(--r);padding:16px;
  box-shadow:var(--shadow);transition:.16s;display:flex;flex-direction:column}
.chan:hover{transform:translateY(-3px);box-shadow:var(--shadow-lg);border-color:color-mix(in srgb,var(--gold-2) 45%,var(--line))}
.chan .ch-t{font-size:14px;font-weight:750;display:flex;align-items:center;gap:7px;margin-bottom:4px}
.chan .ch-t::before{content:"◈";color:var(--gold-2);font-size:12px}
.chan .ch-t a{color:inherit;text-decoration:none}
.chan .ch-t a:hover{color:var(--gold)}
.chan .ch-d{font-size:11px;color:var(--sub);margin-bottom:10px;line-height:1.55}
.chan ul{list-style:none;margin:0;padding:0;display:flex;flex-direction:column;gap:2px}
.chan li a{display:block;font-size:12px;color:var(--ink-2);padding:4px 7px;border-radius:6px;line-height:1.5}
.chan li a:hover{background:var(--gold-soft);color:var(--gold)}
.chan li a::before{content:"›";margin-right:6px;color:var(--gold-2);font-weight:700}
@media(max-width:1080px){.chan-grid{grid-template-columns:repeat(3,minmax(0,1fr))}}
@media(max-width:720px){.chan-grid{grid-template-columns:1fr 1fr}}
@media(max-width:480px){.chan-grid{grid-template-columns:1fr}}

/* ============ 章节自动编号（层级视觉强化） ============ */
main{counter-reset:secno}
.section{counter-increment:secno}
.section.no-num{counter-increment:none}
/* ============ 移动端适配覆盖(置于所有主定义之后,确保生效) ============ */
  .portal-main table,.portal table{min-width:0}
  .table-scroll{overflow-x:auto;-webkit-overflow-scrolling:touch;margin:0 -16px;padding:0 16px}
  .table-scroll .mega-table{display:table;min-width:660px;width:max-content}
  .mega-table thead{display:table-header-group}
  .mega-table tbody,.mega-table tr,.mega-table td,.mega-table th{display:table-cell}
  .mega-table tbody tr{border:none;border-bottom:1px solid var(--line-2);border-radius:0;margin:0;padding:0;background:transparent;display:table-row}
  .mega-table tbody tr:hover{background:var(--gold-soft)}
  .mega-table tbody tr:nth-child(even){background:color-mix(in srgb,var(--surface-2) 50%,transparent)}
  .mega-table td{text-align:right;padding:8px 10px;white-space:nowrap;border-bottom:1px solid var(--line-2)}
  .mega-table td::before{content:none}
  .mega-table td.lbl,.mega-table td.sym{text-align:left}
  .mega-table .grow td{text-align:left;background:var(--surface-2);color:var(--gold-ink);font-size:11.5px;font-weight:750;letter-spacing:1.5px;padding:7px 10px}
  .mega-table th{display:table-cell;padding:8px 10px;font-size:11px}
  /* 三大报价模块:窄屏单列 + 缩图防截断 */
  .three-quote{grid-template-columns:1fr}
  .tq-spark{flex:0 0 84px}
  .tq-spark svg{width:84px;height:38px}
  .tq-price{font-size:27px}
  .tq-body{padding:12px 12px}
@media(max-width:900px) and (min-width:721px){
  .tq-price{font-size:26px}
  .tq-spark{flex:0 0 96px}
  .tq-spark svg{width:96px;height:42px}
  /* 平板:左导航栏保留为窄列,右栏(快讯/日历)并为双列网格垫底 */
  .portal{grid-template-columns:172px minmax(0,1fr)}
  .portal-r{grid-column:1/-1;display:grid;grid-template-columns:1fr 1fr;gap:12px;align-items:start}
}
@media(max-width:720px){
  /* 手机:左栏频道导航隐藏(二级导航条已覆盖其入口),内容直达 */
  .portal-l{display:none}
}
"""

FAQ = [
    {"q": "今日金价是多少？", "a": "本页实时展示上海黄金交易所 Au99.99 等合约最新价，以及国际现货黄金（XAU/USD）折算人民币后的价格与国内溢价。数据每小时自动更新，页面每 60 秒检查一次新数据。"},
    {"q": "Au99.99 是什么？和 Au99.95 有什么区别？", "a": "Au99.99 是上海黄金交易所纯度 99.99% 的现货黄金合约，单位元/克，是国内黄金现货最主要的基准报价。Au99.95 纯度为 99.95%，成交活跃度较低，两者价格通常相差很小。iAu99.99 是国际板合约，以人民币计价但面向国际投资者，可观察境内外价差。"},
    {"q": "国内溢价怎么算？为什么会是负数？", "a": "国内溢价 =（SGE Au99.99 元/克 − 国际金价折算元/克）÷ 国际金价折算元/克 × 100%。国际折算价 = XAU/USD × USD/CNY ÷ 31.1034768。溢价为正说明国内比国际贵，常见于实物需求旺盛或进口配额紧张；为负说明国内贴水，可能与人民币汇率预期、境内供给充裕或国际金价短期快速上涨有关。"},
    {"q": "一盎司黄金等于多少克？", "a": "金衡盎司（troy ounce）是国际贵金属计价单位，1 金衡盎司 = 31.1034768 克。注意它与日常用的常衡盎司（28.3495 克）不同。把国际金价换算成人民币每克，需要先乘以美元兑人民币汇率，再除以 31.1034768。"},
    {"q": "账户黄金和实物黄金有什么区别？", "a": "账户黄金（如 SGE 现货合约、银行积存金）不提取实物，交易便捷、买卖价差小；实物黄金（金条、金币、首饰）需额外考虑加工费、保管、鉴定与回购折价，实际买入成本通常显著高于交易所报价。"},
    {"q": "数据多久更新一次？非交易时段显示什么？", "a": "站点每小时抓取一次上海黄金交易所官方行情、国际现货金价与美元兑人民币汇率。非交易时段（夜间、周末、节假日）会显示最近一次有效报价，不会用空值或 0 填充。分时图展示的是最近一个交易时段采集到的价格序列。"},
    {"q": "价格提醒会上传到服务器吗？", "a": "不会。提醒规则只保存在你当前浏览器的 localStorage 中，页面每 60 秒用本地数据比对一次，触发时通过浏览器桌面通知提示。我们不会收集你的邮箱、价格目标或任何个人信息。"},
]

ARTICLES = [
    {"no": "01", "h": "国内金价与国际金价，为什么不一样？",
     "p": ["很多人在新闻里看到「国际金价突破某美元关口」，换算成人民币每克后，却发现与上海黄金交易所的报价对不上。这中间的差额，就是本页展示的「国内溢价」。",
           "造成价差的原因主要有四类。其一是汇率：国际金价以美元计价，人民币兑美元的任何波动都会直接改变折算后的每克价格。其二是供需：国内婚庆、节庆与投资性实物需求集中释放时，境内买盘会把 SGE 报价推高到国际折算价之上。其三是跨境流通成本与配额：黄金进口存在资质、运输、保险与税费成本，境内外的套利并非瞬时完成，价差因此会持续一段时间。其四是交易时段差异：国际现货黄金近乎全天候交易，而 SGE 有固定交易时段，若国际金价在国内休市时大幅跳动，次日开盘就容易出现明显的溢价或贴水。",
           "因此，看金价不能只看一个数字。把 SGE 现价、XAU/USD、USD/CNY 与国内溢价放在一起观察，才能判断当前的高价究竟来自全球金价上涨，还是来自人民币汇率与境内供需的阶段性变化。"]},
    {"no": "02", "h": "读懂合约代码：Au99.99、Au99.95、iAu99.99、Ag99.99",
     "p": ["上海黄金交易所的合约代码由「元素符号 + 纯度」构成。Au 是黄金，Ag 是白银，Pt 是铂金，Pd 是钯金；后面的数字代表纯度百分比，例如 Au99.99 即纯度 99.99% 的黄金现货，Au99.95 为 99.95%。",
           "iAu99.99 中的 i 指国际板（International Board），以人民币计价、面向境外参与者，是观察境内外金价联动的重要窗口。计价单位也要注意：黄金、铂金、钯金按「元/克」报价，白银按「元/千克」报价，跨品种比较时务必先统一单位。",
           "本页行情表把六个常用合约并列展示，并对每个合约给出今开、最高、最低与相对今开的涨跌幅。分时图与 K 线以成交最活跃的 Au99.99 为主力，多品种对比图则把不同品种的日内走势归一化成百分比，方便直接比较强弱。"]},
    {"no": "03", "h": "影响黄金价格的五个核心变量",
     "p": ["黄金同时具备货币属性、避险属性与商品属性，因此价格驱动因素比一般商品复杂。第一是实际利率：黄金本身不生息，当债券实际收益率上升，持有黄金的机会成本提高，金价通常承压；反之则受支撑。",
           "第二是美元走势：国际金价以美元标价，美元走弱时，同样数量的其他货币可以买到更多黄金，需求上升往往推高价格。第三是地缘政治与金融风险事件，避险资金会在短期内集中流入黄金。第四是各国央行的储备配置，近年来央行持续购金构成中长期需求底仓。第五是通胀预期与实物消费季节性，包括中国与印度的婚庆、节庆用金高峰。",
           "对国内投资者而言，还要额外叠加一层人民币汇率：即使国际金价横盘，人民币贬值也会让以人民币计价的黄金看起来在上涨。这正是本页同时展示 USD/CNY 与国内溢价的原因。"]},
    {"no": "04", "h": "如何看懂分时图与 K 线",
     "p": ["分时图把某一交易时段内按时间顺序采集到的成交价连成曲线，适合观察日内节奏：价格沿均线缓慢抬升通常代表买盘持续，快速冲高后回落则可能是短线获利了结。",
           "K 线（蜡烛图）把一段连续的价格压缩成四个数值——开盘价、最高价、最低价、收盘价。实体表示开收盘区间，上下影线表示期间触及的极端价格。本页 K 线由分时序列按固定间隔聚合而成，属于「分时聚合 K 线」，用于观察日内结构，不等同于交易所日 K 线。按中国市场习惯，本页上涨用红色、下跌用绿色。",
           "多品种对比图把黄金、白银、铂金的日内走势都归一化到起点 0%，这样即便单位与价格量级完全不同，也能直观看出哪个品种当天更强。需要注意的是，日内走势受流动性与采样影响较大，不宜单独作为决策依据。"]},
    {"no": "05", "h": "常见黄金投资方式的区别",
     "p": ["交易所现货合约（如 SGE Au99.99）报价透明、买卖价差小，适合关注价格本身的投资者；银行积存金门槛低、可定投，但需留意点差与赎回规则；黄金 ETF 在证券账户内交易，流动性好、跟踪误差小；实物金条与金币具备持有感，但要承担加工费、鉴定、保管与回购折价。",
           "不同方式的成本结构差别很大。以实物金条为例，买入价通常在交易所基准价之上加若干元/克的加工与流通费用，回购时又可能低于基准价，这意味着金价需要上涨一段幅度才能回本。相比之下，账户类产品的成本更多体现在点差与管理费上。",
           "无论选择哪种方式，都建议先明确自己的持有期限与风险承受能力，并区分「看好金价」与「想持有实物」这两个不同目标。"]},
    {"no": "06", "h": "本页数据是怎么来的",
     "p": ["上海黄金交易所合约行情来自交易所官方行情接口，每个合约取最近一个交易时段的价格序列，并保留今开、最高、最低与交易所给出的更新时间。国际现货黄金 XAU/USD 与美元兑人民币汇率分别取自公开行情接口。所有数据在服务端每小时抓取一次并生成为静态文件，浏览器端每 60 秒检查是否有新版本。",
           "国内溢价与国际折算价由上述原始数据计算得出：先把 XAU/USD 按 USD/CNY 换算成人民币每盎司，再除以 31.1034768 得到每克价格，最后与 SGE Au99.99 比较得出百分比。若某个上游抓取失败，系统会回退到上一次的有效数据，避免页面出现空白或错误数字。",
           "本站为行情聚合展示，所有价格以上海黄金交易所及相应机构官方发布为准，内容仅作信息参考，不构成投资建议或交易依据。"]},
    {"no": "07", "h": "今日银价怎么看？三个最容易踩的单位坑",
     "p": ["国内白银报价以「元/千克」为单位，国际白银（XAG/USD）以「美元/盎司」为单位，两者直接对比毫无意义。正确换算：国际银价 × 美元兑人民币 ÷ 31.1034768 × 1000，得到元/千克后再与 SGE Ag99.99 比较。本页「多品种国内溢价」已代你完成这一步。",
           "第二个坑是含税口径：境内白银现货报价内含增值税因素，因此 SGE 白银对国际价的溢价天然偏高（常见 10% 以上），这不是套利机会，而是税制差异。把溢价直接理解为「白银被高估」是常见误读。",
           "第三个坑是波动弹性：白银盘子小、工业属性强，涨跌幅通常是黄金的 1.5～3 倍。看银价别只看绝对数字，把它与金价放在一起看相对强弱，信息量更大——本页对比图已把金银铂归一化到同一坐标。"]},
    {"no": "08", "h": "铂金多少钱一克？为什么比黄金便宜",
     "p": ["铂金（Pt）曾是四大贵金属中最贵的一个，但近十年多数时间反而低于黄金。核心原因在需求结构：铂金约一半需求来自汽车尾气催化剂，电动车渗透率上升直接削弱了这一底仓；而黄金的货币与储备需求则持续扩张。",
           "国内铂金现货报价看上海黄金交易所 Pt99.95（元/克），国际上看 XPT/USD（美元/盎司）。两者对比同样要先经过汇率与盎司-克换算，本页溢价表已直接给出「SGE 境内价 vs 国际折算价」的偏离程度。",
           "铂金流动性显著弱于金银：SGE 铂金合约成交清淡，买卖价差大，实物铂金回购渠道也少。它的价格弹性虽大，但进出的摩擦成本高，把它当「便宜的黄金」来配置是一种常见误解。"]},
    {"no": "09", "h": "Au(T+D) 延期合约是什么？和现货有何不同",
     "p": ["Au(T+D) 是上海黄金交易所的黄金延期交收合约：约定在未来某一日期交收，但可以无限递延。它与现货最大的区别是引入了「多空双向」——可以先卖后买，也可以加保证金杠杆，因此成交远比现货活跃，是国内黄金投机的最主流工具。",
           "延期合约的特有成本是「递延费」（延期补偿费）：当市场多空不平衡时，一方要向另一方支付一定比例的费用，方向每日都可能切换。长期持仓时递延费的累积成本不可忽视，这与持有现货完全不同。",
           "本页行情表同时展示 Au99.99 现货、Au(T+D) 延期与 mAu(T+D) 迷你延期：三者价差通常很小，但延期合约的价格里包含了对隔夜与资金成本的定价，波动节奏也可能与现货略有不同步。"]},
    {"no": "10", "h": "黄金 ETF、积存金与纸黄金，选哪个",
     "p": ["黄金 ETF 在证券账户内交易，跟踪国内金价、流动性好、费率透明（管理费约 0.5%/年），适合已有证券账户、想灵活进出的投资者；缺点是需要开证券账户，且买卖时机依赖自己的判断。",
           "银行积存金按克或按金额定期买入，门槛低、可设置自动定投，适合「无脑攒金」；但要留意银行的点差（买卖价差）与赎回规则，部分产品只能按金额赎回而不能提实物。",
           "「纸黄金」是银行的账户黄金，报价紧跟国际金价，交易时间长；但它只是记账资产，不对应实物，也有点差成本。三者的共同点：都无法变成手里的一块金子。真要实物，请回到本页科普第 05 篇提到的加工费、保管与回购折价问题，把成本算清楚再决定。"]},
    {"no": "11", "h": "今日油价：布伦特、WTI 和上海原油是什么关系",
     "p": ["国际上引用最多的两个基准：布伦特（Brent）出产于北大西洋，覆盖欧洲、非洲与中东原油定价，全球约三分之二原油贸易以其为参照；WTI（西得克萨斯轻质原油）是美国基准。两者走势高度相关，价差反映区域供需与运输成本。",
           "上海原油（SC）是上海国际能源交易中心的期货合约，以人民币计价、单位是「元/桶」，它既承接国际油价走势，又叠加了人民币汇率因素：国际油价涨、人民币贬值时，SC 的涨幅会被放大。",
           "一个常见误读：把国际油价直接当成国内加油站的油价。国内成品油价格遵循调价机制（每 10 个工作日一调，并有调控上下限），与国际油价联动但不同步。看懂了这三个价格的关系，再判断「油价涨了明天加油贵不贵」就准确得多。"]},
    {"no": "12", "h": "人民币汇率：在岸、离岸与中间价的区别",
     "p": ["新闻里的「人民币汇率」其实有三个口径：中间价是中国外汇交易中心每个交易日开盘前公布的基准价；在岸价（CNY）是境内银行间市场的成交价，浮动受管理；离岸价（CNH）在境外市场交易，波动更自由，常被视为市场情绪的温度计。",
           "本页展示的是公开接口的折算汇率，接近在岸口径，适合看「大数」与换算参考；真正的换汇成交价是各银行牌价，含买入/卖出点差，通常比中间价差 0.2%～0.5%。换大额外汇前值得先比一比不同银行的牌价。",
           "汇率对贵金属投资者还有一层意义：国际金价以美元计价，人民币贬值时，即使国际金价横盘，以人民币计价的国内金价也会走高——这也是本页同时展示汇率与国内溢价的原因。"]},
]


GLOSSARY = [
    {"t": "国内溢价", "d": "SGE 现货价相对「国际金价折算人民币」的偏离百分比。为正说明国内比国际贵，常见于实物需求旺、进口配额紧；为负称贴水。"},
    {"t": "递延费", "d": "Au(T+D) 等延期合约的特有成本：多空失衡时一方每日向另一方支付的费用，方向每日可能切换，长期持仓不可忽视。"},
    {"t": "T+D 延期", "d": "上海黄金交易所的黄金延期交收合约，可多空双向、带保证金杠杆，是国内黄金投机最主流的工具，成交远旺于现货。"},
    {"t": "基础金价", "d": "通常指 SGE Au99.99 等现货基准报价，是投资金条、积存金与首饰定价的锚点；实物买卖在此基础上加减工费与价差。"},
    {"t": "工费 / 佣金", "d": "实物金的加工与品牌溢价，按元/克或按件收取。投资金条约 +8~15 元/克，足金首饰常 +60~120 元/克，3D/古法金更高。"},
    {"t": "升水 / 贴水", "d": "升水指某市场价格高于基准（如国内溢价）；贴水指低于基准。用于描述境内外、期现、远近月之间的价格结构。"},
    {"t": "K 金", "d": "黄金与其他金属的合金，数字代表含金量：18K≈75%、14K≈58.3%、9K≈37.5%。硬度高、适合镶嵌，单价低于足金。"},
    {"t": "3D 硬金", "d": "电铸工艺制成的足金（99.9%），硬度高、造型立体，但按「一口价」卖、克单价远高于基础金价，回收仍按克重。"},
    {"t": "成色 / 纯度", "d": "Au99.99 即含金量 99.99%（万足金），Au99.95 为 99.95%。国内首饰常见足金 999（99.9%）。"},
    {"t": "金衡盎司", "d": "国际贵金属计价单位，1 金衡盎司 = 31.1034768 克；与日常常衡盎司（28.3495 克）不同，换算时务必用对。"},
    {"t": "上海金", "d": "上海黄金交易所推出的人民币黄金基准价（SHAU），每日两次定价，是国内黄金现货与衍生品的重要参考。"},
    {"t": "国际板 iAu", "d": "iAu99.99 是 SGE 国际板合约，以人民币计价、面向境外投资者，是观察境内外金价联动的窗口。"},
    {"t": "积存金", "d": "银行按克或金额定期买入黄金的账户产品，门槛低、可定投，部分支持赎回或提实物，留意点差与赎回规则。"},
    {"t": "回收折价", "d": "金店/机构回购实物金时低于基础金价的差额（常 −4~8 元/克），是买入到卖出之间必须跨越的成本。"},
    {"t": "伦敦金定盘", "d": "LBMA 每日两次公布的黄金定盘价，是国际现货黄金的权威参考，与 COMEX 期货共同构成全球定价体系。"},
]


# ---------------------------------------------------------------- 页面骨架

def head_html(title, desc, canonical, extra=""):
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="theme-color" content="#0e1626">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<meta name="keywords" content="金潮网,贵金属行情,今日金价,黄金价格,实时金价,上海黄金交易所,Au99.99,国际金价,国内溢价,白银价格,铂金价格,今日油价,布伦特原油,WTI,上海原油,人民币汇率,美元汇率">
<meta name="author" content="金潮网">
<meta name="robots" content="index,follow">
<meta property="og:site_name" content="金潮网 · 贵金属行情门户">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:type" content="website">
<meta property="og:url" content="{esc(canonical)}">
<link rel="canonical" href="{esc(canonical)}">
<meta name="google-site-verification" content="fg3VNE2jruGx8MIMWrvQDV9DXioc2BZQcWEDKzUmh9k">
<link rel="icon" type="image/svg+xml" href="./favicon.svg">
<link rel="apple-touch-icon" href="./favicon.svg">
<link rel="manifest" href="./manifest.json">
{ADSENSE_LOADER}
{extra}
<link rel="stylesheet" href="./site.css">
<script src="./common.js"></script>
</head>
"""


def topbar_html(data):
    return f"""<div class="topbar"><div class="wrap">
  <div class="tb-l"><span class="live-dot"></span><span>数据源：上海黄金交易所 · 国际现货黄金 · 美元兑人民币</span></div>
  <div class="tb-r">
    <span id="genTime">数据生成：{esc(data.get('generated_at') or '—')}</span>
    <a href="./about.html">数据说明</a>
  </div>
</div></div>"""


def ticker_html(data):
    items = data.get("items") or []
    chips = []
    for it in items:
        d = delta(it)
        if d:
            chg, pct, cls = d
            arrow = "▲" if chg > 0 else "▼" if chg < 0 else "—"
            c = f'<span class="tk-c {cls}">{arrow} {abs(pct):.2f}%</span>'
        else:
            c = '<span class="tk-c flat">—</span>'
        chips.append(
            f'<div class="tk"><span class="tk-n">{esc(it.get("label"))} {esc(it.get("symbol"))}</span>'
            f'<span class="tk-v num">{fmt(it.get("last"))}</span>{c}</div>')
    # 油价
    oil = data.get("oil") or {}
    for key in ("brent", "wti", "sc"):
        x = oil.get(key) or {}
        if x.get("last") is None:
            continue
        prev = x.get("prev_close") or x.get("prev_settle")
        if prev:
            pct = (x["last"] - prev) / prev * 100
            cls = "up" if pct > 0 else "down" if pct < 0 else "flat"
            arrow = "▲" if pct > 0 else "▼" if pct < 0 else "—"
            c = f'<span class="tk-c {cls}">{arrow} {abs(pct):.2f}%</span>'
        else:
            c = '<span class="tk-c flat">—</span>'
        chips.append(
            f'<div class="tk"><span class="tk-n">{esc(x.get("name"))}</span>'
            f'<span class="tk-v num">{fmt(x.get("last"))}</span>'
            f'<span class="flat" style="font-size:10px">{esc(x.get("unit"))}</span>{c}</div>')
    # 汇率（主币种）
    for r in (data.get("fx") or [])[:5]:
        chips.append(
            f'<div class="tk"><span class="tk-n">{esc(r.get("code"))}/CNY</span>'
            f'<span class="tk-v num">{fmt(r.get("cny"), 4)}</span></div>')
    if not chips:
        chips = ['<div class="tk"><span class="tk-n">行情加载中</span></div>']
    track = "".join(chips + chips)  # 复制一份实现无缝滚动
    return ('<div class="ticker"><div class="ticker-inner">'
            '<div class="ticker-label">◈ 实时行情</div>'
            f'<div class="ticker-view"><div class="ticker-track">{track}</div></div>'
            '</div></div>')


# 五大板块数据源（主导航下拉 + 常驻二级导航条 + 首页频道网格共用）
NAV_SECTIONS = [
    ("quotes", "行情中心", "./index.html", [
        ("行情概览", "./index.html#overview"),
        ("实时行情", "./index.html#quotes"),
        ("溢价对照", "./index.html#premium"),
        ("实物金价", "./index.html#physical"),
        ("油价汇率", "./index.html#energy"),
        ("工具计算", "./index.html#tools"),
        ("走势图表", "./index.html#charts"),
        ("价格提醒", "./index.html#alerts"),
    ]),
    ("data", "数据中心", "./data.html", [
        ("关键指标", "./data.html#indicators"),
        ("溢价数据", "./data.html#premium"),
        ("汇率一览", "./data.html#fx"),
        ("历史日线", "./data.html#history"),
        ("历史走势", "./history.html"),
    ]),
    ("calendar", "财经日历", "./calendar.html", [
        ("经济事件", "./calendar.html#events"),
        ("FOMC 议息", "./calendar.html#fomc"),
        ("央行决议", "./calendar.html#cb"),
    ]),
    ("news", "金融快讯", "./news.html", [
        ("7×24 快讯", "./news.html#live"),
        ("资讯来源", "./news.html#live"),
    ]),
    ("academy", "投资学院", "./academy.html", [
        ("科普文章", "./academy.html#articles"),
        ("术语速查", "./academy.html#glossary"),
        ("常见问题", "./academy.html#faq"),
    ]),
]


def nav_html(active=""):
    """一级导航：5 大板块大标签（金投网式）。子栏目由常驻二级导航条承载，不设悬停下拉。"""
    parts = []
    for key, text, url, subs in NAV_SECTIONS:
        cls = "ntab active" if key == active else "ntab"
        parts.append(f'<a class="{cls}" href="{url}">{text}</a>')
    a = "".join(parts)
    return f"""<header class="nav"><div class="wrap nav-top">
  <a class="brand" href="./index.html" aria-label="金潮网 首页">
    <span class="brand-mark">Au</span>
    <span class="brand-txt"><strong>金潮网</strong><small>贵金属行情门户</small></span>
  </a>
  <nav class="nav-menu" id="navMenu">{a}</nav>
  <div class="nav-act">
    <button class="icon-btn" id="themeBtn" type="button" aria-label="切换深浅色">🌓 <span>主题</span></button>
    <button class="nav-toggle" id="navToggle" type="button" aria-label="打开菜单">☰</button>
  </div>
</div></header>"""


def subnav_html(active=""):
    """常驻二级导航条：当前板块的子栏目始终可见（门户层级外显），附面包屑。"""
    sec = next((s for s in NAV_SECTIONS if s[0] == active), None)
    if not sec:
        return ""
    _, title, url, subs = sec
    links = "".join(f'<a href="{u}">{esc(t)}</a>' for t, u in subs)
    return f"""<div class="subnav"><div class="wrap subnav-inner">
  <span class="subnav-home"><a href="./index.html">首页</a> <i>›</i> <b>{esc(title)}</b></span>
  <nav class="subnav-links">{links}</nav>
</div></div>"""


def side_left(active):
    """三栏布局左栏：板块导航 + 当前板块子栏目（金投网式）。"""
    rows = []
    for key, text, url, subs in NAV_SECTIONS:
        cur = ' class="cur"' if key == active else ""
        rows.append(f'<li><a href="{url}"{cur}>{esc(text)}</a></li>')
        if key == active:
            rows.extend(f'<li><a href="{u}" style="padding-left:22px;font-size:11.5px;color:var(--sub)">{esc(t)}</a></li>'
                        for t, u in subs)
    return (f'<aside class="portal-l"><div class="pmod">'
            f'<div class="pmod-h">频道导航</div>'
            f'<div class="pmod-b"><ul class="side-nav">{"".join(rows)}</ul></div></div></aside>')


def side_right(data):
    """三栏布局右栏：快讯 / 财经日历 / 投资学院 / 术语速查（金投网式侧栏）。"""
    news = (data.get("news") or [])[:6]
    if news:
        news_li = "".join(
            f'<li><span class="t">{esc((n.get("time") or "")[5:16])}</span>'
            f'<a href="./news.html">{esc(n.get("title"))}</a></li>'
            for n in news)
    else:
        news_li = '<li><a href="./news.html">快讯加载中，点击查看 →</a></li>'
    ev_li = "".join(
        f'<li><span class="t">{esc(d[0][5:10])}</span><a href="./calendar.html">{esc(d[1])}</a></li>'
        for d in ECON_EVENTS[:5])
    ac_li = "".join(
        f'<li><a href="./academy.html#articles">{esc(a["h"])}</a></li>'
        for a in ACAD_ARTICLES[:5])
    gl_li = "".join(
        f'<li><a href="./academy.html#glossary"><b>{esc(g["t"])}</b> {esc(g["d"][:26])}…</a></li>'
        for g in GLOSSARY[:5])
    return f"""<aside class="portal-r">
  <div class="pmod"><div class="pmod-h">实时快讯<a class="more" href="./news.html">更多 »</a></div>
    <div class="pmod-b"><ul class="mini-list">{news_li}</ul></div></div>
  <div class="pmod"><div class="pmod-h">财经日历<a class="more" href="./calendar.html">更多 »</a></div>
    <div class="pmod-b"><ul class="mini-list">{ev_li}</ul></div></div>
  <div class="pmod"><div class="pmod-h">投资学院<a class="more" href="./academy.html">更多 »</a></div>
    <div class="pmod-b"><ul class="mini-list">{ac_li}</ul></div></div>
  <div class="pmod"><div class="pmod-h">术语速查<a class="more" href="./academy.html#glossary">更多 »</a></div>
    <div class="pmod-b"><ul class="mini-list">{gl_li}</ul></div></div>
</aside>"""


def footer_html():
    return f"""<footer class="site">
  <div class="wrap foot-grid">
    <div class="foot-brand">
      <a class="brand" href="./index.html" style="margin-bottom:6px">
        <span class="brand-mark">Au</span>
        <span class="brand-txt"><strong>金潮网</strong><small>贵金属行情门户</small></span>
      </a>
      <p>一站式贵金属行情门户：实时行情、数据中心、财经日历、金融快讯、投资学院五大板块。数据聚合展示，仅供参考，不构成投资建议。</p>
    </div>
    <div class="foot-col"><h4>行情中心</h4>
      <a href="./index.html#quotes">实时行情</a><a href="./index.html#premium">溢价对照</a>
      <a href="./index.html#physical">实物金价</a><a href="./index.html#charts">走势图表</a>
      <a href="./index.html#energy">油价汇率</a><a href="./index.html#tools">工具计算</a></div>
    <div class="foot-col"><h4>数据中心</h4>
      <a href="./data.html#indicators">关键指标</a><a href="./data.html#history">历史走势</a>
      <a href="./data.html#fx">汇率一览</a><a href="./history.html">历史日线</a></div>
    <div class="foot-col"><h4>日历快讯</h4>
      <a href="./calendar.html#events">经济事件</a><a href="./calendar.html#fomc">FOMC 议息</a>
      <a href="./calendar.html#cb">央行决议</a><a href="./news.html">7×24 快讯</a></div>
    <div class="foot-col"><h4>投资学院</h4>
      <a href="./academy.html#articles">科普文章</a><a href="./academy.html#glossary">术语速查</a>
      <a href="./academy.html#faq">常见问题</a><a href="./about.html">关于本站</a>
      <a href="./privacy.html">隐私政策</a></div>
  </div>
  <div class="wrap foot-bottom">
    <strong>免责声明：</strong>本站为行情信息聚合展示，价格以上海黄金交易所及相应机构官方发布为准。
    所有内容仅供信息参考，不构成任何投资建议、要约或交易依据。黄金价格波动较大，投资需自行判断并承担风险。<br>
    数据更新：每 30 分钟自动抓取 · 浏览器每 60 秒检查更新 · 非交易时段显示最近一次有效报价 · 快讯来自华尔街见闻公开流<br>
    © 2026 金潮网 · 页面含第三方广告（Google AdSense），广告内容由第三方提供，与本站点立场无关。
  </div>
</footer>
<button class="back-top" id="backTop" type="button" aria-label="返回顶部">↑</button>
"""


def faq_ld(faq):
    ld = {"@context": "https://schema.org", "@type": "FAQPage",
          "mainEntity": [{"@type": "Question", "name": f["q"],
                          "acceptedAnswer": {"@type": "Answer", "text": f["a"]}} for f in faq]}
    return json.dumps(ld, ensure_ascii=False)


def ad_slot():
    return '<div class="ad-slot" aria-label="广告位"></div>'


METAL_DEFS = [("gold", "黄金", "Au99.99"), ("silver", "白银", "Ag99.99"),
              ("platinum", "铂金", "Pt99.95"), ("palladium", "钯金", "Pd99.95")]


def oil_rows(oil):
    """能源行情表：布伦特 / WTI / 上海原油。涨跌基准：前收（Brent/WTI）或昨结（SC）。"""
    rows = []
    for key in ("brent", "wti", "sc"):
        x = oil.get(key) or {}
        last = x.get("last")
        if last is None:
            continue
        prev = x.get("prev_close") or x.get("prev_settle")
        if prev:
            chg = (last - prev) / prev * 100
            cls = "up" if chg > 0 else "down" if chg < 0 else "flat"
            chg_html = (f'<span class="chg {cls}">{"▲" if chg > 0 else "▼" if chg < 0 else "—"} '
                        f'{abs(chg):.2f}%</span>')
        else:
            chg_html = '<span class="flat">—</span>'
        rows.append(
            "<tr>"
            f'<td class="lbl" data-label="品种">{esc(x.get("name"))}</td>'
            f'<td class="sym" data-label="代码">{esc(x.get("symbol"))}</td>'
            f'<td class="num strong" data-label="最新价">{fmt(last)}</td>'
            f'<td data-label="涨跌幅">{chg_html}</td>'
            f'<td class="unit" data-label="单位">{esc(x.get("unit"))}</td>'
            f'<td class="unit" data-label="日期">{esc(x.get("date") or "—")}</td>'
            "</tr>")
    return "".join(rows)


def fx_rows(fx):
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
    return "".join(rows)


def grouped_rows(data):
    """全宽大行情表:SGE + 国内期货主力 + 全球股指 + 国际现货/能源,分组铺开(金投网式)。"""
    def chg_cells(last, base):
        try:
            if last is None or base in (None, 0, ""):
                raise ValueError
            d = float(last) - float(base)
            pct = d / float(base) * 100
            cls = "up" if d > 0 else "down" if d < 0 else "flat"
            arrow = "▲ +" if d > 0 else ("▼ " if d < 0 else "— ")
            return (f'<td class="num strong {cls}">{d:+,.2f}</td>'
                    f'<td><span class="pill {cls}">{arrow}{abs(pct):.2f}%</span></td>')
        except (TypeError, ValueError):
            return '<td class="num">—</td><td><span class="pill flat">—</span></td>'

    def row(name, code, last, base, open_, high, low, unit):
        c = chg_cells(last, base)
        return ("<tr>"
                f'<td class="lbl">{esc(name)}</td>'
                f'<td class="sym">{esc(code)}</td>'
                f'<td class="num strong">{fmt(last)}</td>{c}'
                f'<td class="num">{fmt(open_)}</td>'
                f'<td class="num up">{fmt(high)}</td>'
                f'<td class="num down">{fmt(low)}</td>'
                f'<td class="unit">{esc(unit)}</td></tr>')

    rows = []
    rows.append('<tr class="grow"><td colspan="9">◆ 上海黄金交易所 SGE</td></tr>')
    for it in data.get("items") or []:
        rows.append(row(it.get("label"), it.get("symbol"), it.get("last"),
                        it.get("open"), it.get("open"), it.get("max"), it.get("min"), it.get("unit")))
    ex = data.get("extra") or {}
    if ex.get("futures"):
        rows.append('<tr class="grow"><td colspan="9">◆ 国内期货主力 · 上期所 / 上期能源</td></tr>')
        for x in ex["futures"]:
            rows.append(row(x.get("name"), x.get("code"), x.get("last"), x.get("prev"),
                            x.get("open"), x.get("high"), x.get("low"), x.get("unit")))
    if ex.get("indices"):
        rows.append('<tr class="grow"><td colspan="9">◆ 全球股指</td></tr>')
        for x in ex["indices"]:
            rows.append(row(x.get("name"), x.get("code"), x.get("last"), x.get("prev"),
                            x.get("open"), x.get("high"), x.get("low"), x.get("unit") or "点"))
    if ex.get("intl") or ex.get("dxy"):
        rows.append('<tr class="grow"><td colspan="9">◆ 国际现货 · 能源 · 美元指数</td></tr>')
        for x in ex.get("intl") or []:
            rows.append(row(x.get("name"), x.get("code"), x.get("last"), x.get("prev"),
                            x.get("open"), x.get("high"), x.get("low"), x.get("unit")))
        D = ex.get("dxy")
        if D:
            rows.append(row(D.get("name"), "USD Index", D.get("last"), D.get("prev"),
                            D.get("open"), D.get("high"), D.get("low"), D.get("unit") or "点"))
    return "".join(rows)


def metals_rows(intl):
    """多品种溢价对照表静态行（首屏可用，app.js 刷新后重建）。
    SGE 无成交的品种（如钯金长期休市）自动隐藏，有数据时自动出现。"""
    m = intl.get("metals") or {}
    rows = []
    for key, label, sge_sym in METAL_DEFS:
        x = m.get(key) or {}
        if x.get("sge") is None and x.get("premium_pct") is None:
            continue  # 境内无报价，整行隐藏
        prem = x.get("premium_pct")
        cls = "up" if (prem or 0) >= 0 else "down"
        prem_txt = f"{prem:+.2f}%" if prem is not None else "—"
        unit = esc(x.get("unit") or "")
        rows.append(
            "<tr>"
            f'<td class="lbl" data-label="品种">{label} <span class="sym">{sge_sym}</span></td>'
            f'<td class="num" data-label="境内报价">{fmt(x.get("sge"))} <span class="unit">{unit}</span></td>'
            f'<td class="num" data-label="国际折算">{fmt(x.get("intl_cny"))} <span class="unit">{unit}</span></td>'
            f'<td data-label="国内溢价"><span class="chg {cls}">{prem_txt}</span></td>'
            f'<td class="unit" data-label="口径">{esc(x.get("intl_symbol") or "")} × USD/CNY</td>'
            "</tr>")
    return "".join(rows)


# ---------------------------------------------------------------- 首页

def page_index(data):
    items = data.get("items") or []
    intl = data.get("intl") or {}
    prim = data.get("primary") or {}
    sym = prim.get("symbol") or "Au99.99"

    sym_opts = "".join(
        f'<option value="{esc(it.get("symbol"))}">{esc(it.get("label"))} {esc(it.get("symbol"))}</option>'
        for it in items)

    faq_html = "".join(
        f'<details><summary>{esc(f["q"])}</summary><div class="ans">{esc(f["a"])}</div></details>'
        for f in FAQ)
    article_html = "".join(
        '<article class="prose-card"><div class="no">' + esc(a["no"]) + ' / GUIDE</div>'
        '<h3>' + esc(a["h"]) + '</h3>' + "".join('<p>' + esc(p) + '</p>' for p in a["p"]) + '</article>'
        for a in ARTICLES)
    glossary_html = "".join(
        '<div class="gloss"><h4>' + esc(g["t"]) + '</h4><p>' + esc(g["d"]) + '</p></div>'
        for g in GLOSSARY)
    # 频道导航网格：5 大板块 + 各子栏目，层级一屏可见
    chan_desc = {
        "quotes": "实时行情 / 溢价 / 实物金价",
        "data": "金银比 / 汇率 / 历史日线",
        "calendar": "FOMC / 非农 / CPI 日程",
        "news": "7×24 财经快讯流",
        "academy": "18 篇科普 / 术语 / 问答",
    }
    chan_html = "".join(
        '<div class="chan">'
        '<div class="ch-t"><a href="' + url + '">' + esc(text) + '</a></div>'
        '<div class="ch-d">' + chan_desc.get(key, "") + '</div>'
        '<ul>' + "".join('<li><a href="' + u + '">' + esc(t) + '</a></li>' for t, u in subs[:5]) + '</ul>'
        '</div>'
        for key, text, url, subs in NAV_SECTIONS)

    website_ld = json.dumps({
        "@context": "https://schema.org", "@type": "WebSite", "name": "金潮网",
        "url": SITE, "description": "实时黄金价格、上海黄金交易所行情、国际金价与国内溢价",
        "inLanguage": "zh-CN"}, ensure_ascii=False)
    ld = (f'<script type="application/ld+json">{faq_ld(FAQ)}</script>\n'
          f'<script type="application/ld+json">{website_ld}</script>')

    prem = intl.get("premium_pct")
    prem_cls = "up" if (prem or 0) >= 0 else "down"
    prem_txt = f"{prem:+.2f}%" if prem is not None else "—"
    silver_usd = fmt(((intl.get("metals") or {}).get("silver") or {}).get("intl_usd"))
    oil = data.get("oil") or {}
    fx = data.get("fx") or []

    # 主力合约日内区间（概览卡静态首屏值，app.js 会在数据刷新后覆盖）
    main_item = next((x for x in items if x.get("symbol") == "Au99.99"), None)
    ov_open = fmt(main_item.get("open")) if main_item else "—"
    ov_high = fmt(main_item.get("max")) if main_item else "—"
    ov_low = fmt(main_item.get("min")) if main_item else "—"
    try:
        ov_range = f"{(float(main_item['max']) - float(main_item['min'])) / float(main_item['open']) * 100:.2f}%" if main_item else "—"
    except (TypeError, ValueError, ZeroDivisionError, KeyError):
        ov_range = "—"

    data_json = json.dumps(data, ensure_ascii=False)

    return f"""{head_html(
        "金潮网 - 贵金属行情门户 | 今日金价_上海黄金交易所_国际金价_财经日历_金融快讯",
        "实时黄金白银铂金价格、今日油价（布伦特/WTI/上海原油）与人民币汇率：上海黄金交易所 Au99.99、Au(T+D)、Ag99.99 等合约最新价，国际现货 XAU/XAG/XPT，多品种国内溢价对照，附走势图表与知识百科。",
        SITE, ld)}
<body>
{topbar_html(data)}
{ticker_html(data)}
{nav_html('quotes')}
{subnav_html('quotes')}

<div class="wrap">

  <!-- ============ 三大报价模块（金投网式,tab 切换） ============ -->
  <section class="hero-wrap" id="overview" style="margin:14px 0 0">
    <div class="three-quote">
      <div class="tq" id="qm1">
        <div class="tq-tabs"><b>贵金属</b><a class="on" data-i="0">现货黄金</a><a data-i="1">黄金延期</a><a data-i="2">国际板金</a><a data-i="3">白银</a><a data-i="4">COMEX金</a><a data-i="5">COMEX银</a><span class="tq-mode"><a class="on" data-m="0">分时</a><a data-m="1">日K</a></span></div>
        <div class="tq-top">
          <div class="tq-name" id="qm1Name">现货黄金 Au99.99</div>
          <div class="tq-priceline"><span class="tq-price num" id="qm1Price">—</span><span class="tq-unit" id="qm1Unit">元/克</span><span class="tq-chg" id="qm1Chg">—</span></div>
        </div>
        <div class="tq-chart"><canvas id="qm1Chart" height="132"></canvas></div>
        <div class="tq-spark" id="qm1Spark" style="display:none"></div>
      </div>
      <div class="tq" id="qm2">
        <div class="tq-tabs"><b>外汇牌价</b><a class="on" data-i="0">美元</a><a data-i="1">欧元</a><a data-i="2">日元</a><a data-i="3">港币</a><a data-i="4">英镑</a></div>
        <div class="tq-top">
          <div class="tq-name" id="qm2Name">美元兑人民币 USD/CNY</div>
          <div class="tq-priceline"><span class="tq-price num" id="qm2Price">—</span><span class="tq-unit" id="qm2Unit">人民币</span><span class="tq-chg" id="qm2Chg">—</span></div>
        </div>
        <div class="tq-chart" id="qm2ChartBox" style="display:none"><canvas id="qm2Chart" height="132"></canvas></div>
        <div class="tq-spark" id="qm2Spark"></div>
      </div>
      <div class="tq" id="qm3">
        <div class="tq-tabs"><b>能源化工</b><a class="on" data-i="0">布伦特</a><a data-i="1">WTI</a><a data-i="2">上海原油</a><span class="tq-mode"><a class="on" data-m="0">走势</a><a data-m="1">日K</a></span></div>
        <div class="tq-top">
          <div class="tq-name" id="qm3Name">布伦特原油</div>
          <div class="tq-priceline"><span class="tq-price num" id="qm3Price">—</span><span class="tq-unit" id="qm3Unit">美元/桶</span><span class="tq-chg" id="qm3Chg">—</span></div>
        </div>
        <div class="tq-chart"><canvas id="qm3Chart" height="132"></canvas></div>
        <div class="tq-spark" id="qm3Spark" style="display:none"></div>
      </div>
    </div>
    <div class="ov-strip">
      <span>主力 <b id="ovSge">—</b><span id="ovSgeUnit" style="font-size:10.5px">元/克</span> <span class="hero-chg" id="heroChg">—</span> <i id="ovSgeTime" style="font-style:normal">—</i></span>
      <span>国际金 <b id="hsXau">—</b> 美元/盎司</span>
      <span>国际银 <b id="hsSilver">—</b></span>
      <span>USD/CNY <b id="hsFx">—</b></span>
      <span>国内溢价 <span class="v num up" id="hsPrem">—</span></span>
      <span>今开 <b id="ovOpen">—</b></span>
      <span>最高 <b id="ovHigh">—</b></span>
      <span>最低 <b id="ovLow">—</b></span>
      <span>振幅 <b id="ovRange">—</b></span>
    </div>
  </section>

  <!-- ============ 行情表 ============ -->
  <section class="section" id="quotes">
    <div class="section-head">
      <div><div class="lbl">MARKET QUOTES</div><h2>上海黄金交易所 · 实时行情</h2>
        <p>现货、延期与 100g 合约并列对照，涨跌幅以今开为基准计算。</p></div>
      <div class="side">涨 <span class="up">红</span> / 跌 <span class="down">绿</span> · 单位见每行</div>
    </div>
    <div class="card">
      <div class="card-head"><h3>合约行情</h3>
        <div class="chip-row"><span class="badge">◷ 每小时抓取</span><span class="chip">SGE 官方行情</span></div></div>
      <div class="table-scroll">
      <table class="mega-table">
        <thead><tr><th>品种</th><th>代码</th><th>最新价</th><th>涨跌额</th><th>涨跌幅</th><th>今开</th><th>最高</th><th>最低</th><th>单位</th></tr></thead>
        <tbody id="tbody">{grouped_rows(data)}</tbody>
      </table>
      </div>
      <div class="tfoot">「今开 / 最高 / 最低」为当日（或最近交易时段）区间；「最新价」为最近一笔成交。非交易时段显示最近一次有效报价。日内走势为分时序列迷你图，仅示意节奏，不代表完整逐笔成交。</div>
    </div>
  </section>

  <div class="portal">{side_left('quotes')}
  <div class="portal-main">

  <!-- ============ 多品种溢价 ============ -->
  <section class="section" id="premium">
    <div class="section-head">
      <div><div class="lbl">CROSS-MARKET PREMIUM</div><h2>多品种国内溢价</h2>
        <p>黄金、白银、铂金的境内报价与国际折算价对照，看懂内外价差。</p></div>
      <div class="side">溢价为正 = 境内贵于国际折算</div>
    </div>
    <div class="card">
      <div class="card-head"><h3>溢价对照</h3>
        <div class="chip-row"><span class="chip">Au99.99 ↔ XAU</span><span class="chip">Ag99.99 ↔ XAG</span><span class="chip">Pt99.95 ↔ XPT</span></div></div>
      <table class="mega-table">
        <thead><tr><th>品种</th><th>境内报价 (SGE)</th><th>国际折算</th><th>国内溢价</th><th>口径</th></tr></thead>
        <tbody id="metalsBody">{metals_rows(intl)}</tbody>
      </table>
      <div class="tfoot">国际折算 = 国际美元价 × USD/CNY ÷ 31.1034768（白银为元/千克口径，再 × 1000）。溢价 =（SGE − 折算）÷ 折算 × 100%。注意：境内白银报价含增值税因素，对国际价的溢价天然偏高；各品种口径详见「关于本站」。</div>
    </div>
  </section>

  <!-- ============ 实物金价参考 ============ -->
  <section class="section" id="physical">
    <div class="section-head">
      <div><div class="lbl">PHYSICAL GOLD · RETAIL REFERENCE</div><h2>实物金价参考</h2>
        <p>以 SGE Au99.99 为基准金价，按常见零售加价 / 折价估算投资金条、回收价与首饰金价。所有数字随实时基准自动更新。</p></div>
      <div class="side">基准 = Au99.99 实时价</div>
    </div>
    <div class="card">
      <div class="card-head"><h3>实物金价估算</h3>
        <div class="chip-row"><span class="badge">◷ 随实时基准更新</span><span class="chip">参考估算</span></div></div>
      <div class="assume-row">
        <div class="a-item"><label>金条加价 (元/克)</label><input id="asBar" type="number" step="0.5" value="12"></div>
        <div class="a-item"><label>回收折价 (元/克)</label><input id="asRec" type="number" step="0.5" value="5"></div>
        <div class="a-item"><label>首饰工费 (元/克)</label><input id="asJew" type="number" step="1" value="70"></div>
        <div class="a-item"><label>3D/古法工费 (元/克)</label><input id="as3d" type="number" step="1" value="120"></div>
        <div class="a-item"><label>积存金点差 (%)</label><input id="asAcc" type="number" step="0.1" value="0.5"></div>
        <button class="btn mini" id="asReset" type="button">恢复默认</button>
      </div>
      <div class="phys-grid">
        <div class="phys-card real"><div class="pk"><span class="dot"></span>基准金价（SGE Au99.99）</div>
          <div class="pv" id="physBase">—<span class="pu">元/克</span></div>
          <div class="pn">上海黄金交易所实时现货价</div></div>
        <div class="phys-card"><div class="pk">投资金条（买入）</div>
          <div class="pv" id="physBar">—<span class="pu">元/克</span></div>
          <div class="pn">基准 + 金条加价，银行 / 金店买卖价差小</div></div>
        <div class="phys-card"><div class="pk">金条回收价</div>
          <div class="pv" id="physRec">—<span class="pu">元/克</span></div>
          <div class="pn">基准 − 回收折价，回购通常低于基准</div></div>
        <div class="phys-card"><div class="pk">足金 999 首饰（买入）</div>
          <div class="pv" id="physJew">—<span class="pu">元/克</span></div>
          <div class="pn">基准 + 首饰工费，含加工与品牌溢价</div></div>
        <div class="phys-card"><div class="pk">3D / 古法金（买入）</div>
          <div class="pv" id="phys3d">—<span class="pu">元/克</span></div>
          <div class="pn">基准 + 高工费，工艺溢价更高</div></div>
        <div class="phys-card"><div class="pk">银行积存金</div>
          <div class="pv" id="physAcc">—<span class="pu">元/克</span></div>
          <div class="pn">基准 ×（1 + 点差），可定投赎回</div></div>
        <div class="phys-card"><div class="pk">投资金币（熊猫等）</div>
          <div class="pv" id="physCoin">—<span class="pu">元/克</span></div>
          <div class="pn">基准 + 金币溢价，官方渠道按克＋升水</div></div>
        <div class="phys-card"><div class="pk">纪念/收藏金币</div>
          <div class="pv" id="physCoin2">—<span class="pu">元/克</span></div>
          <div class="pn">基准 + 收藏溢价，题材与发行量影响大</div></div>
        <div class="phys-card"><div class="pk">黄金首饰回收</div>
          <div class="pv" id="physJewRec">—<span class="pu">元/克</span></div>
          <div class="pn">按克计价，折价大于金条（含损耗）</div></div>
        <div class="phys-card"><div class="pk">白银回收</div>
          <div class="pv" id="physAgRec">—<span class="pu">元/千克</span></div>
          <div class="pn">Ag9999 价 × 约 97%（回收扣减）</div></div>
        <div class="phys-card"><div class="pk">铂金 / 钯金回收</div>
          <div class="pv" id="physPtRec">—<span class="pu">元/克</span></div>
          <div class="pn">境内价 × 约 97%（钯金见数据中心）</div></div>
      </div>
      <div class="phys-note"><b>说明：</b>以上为「基准金价 + 行业典型加价 / 折价」的<b>参考估算值</b>，用于理解实物金买卖价差结构，<b>非周大福、老凤祥等品牌实时挂牌价</b>。品牌金价由各家每日公布、含独立工费与促销，需以门店为准。调整上方假设可观察不同加价下的估算结果。</div>
    </div>
  </section>

  <!-- ============ 油价与汇率 ============ -->
  <section class="section" id="energy">
    <div class="section-head">
      <div><div class="lbl">OIL &amp; FX</div><h2>国际油价 · 人民币汇率</h2>
        <p>布伦特、WTI 与上海原油对照；主流货币兑人民币实时汇率。</p></div>
      <div class="side">油价涨红 跌绿 · 汇率为 1 美元折算口径</div>
    </div>
    <div class="charts">
      <div class="card"><div class="card-head"><h3>国际与境内油价</h3>
        <div class="chip-row"><span class="chip">布伦特 Brent</span><span class="chip">WTI</span><span class="chip">上海原油 SC</span></div></div>
        <table class="mega-table">
          <thead><tr><th>品种</th><th>代码</th><th>最新价</th><th>涨跌幅</th><th>单位</th><th>日期</th></tr></thead>
          <tbody id="energyBody">{oil_rows(oil)}</tbody>
        </table>
        <div class="tfoot">布伦特 / WTI 为国际基准原油（美元/桶，前收为基准）；上海原油为上期能源 SC 主力连续（元/桶，昨结为基准）。国内成品油调价与国际油价联动，但存在调控上下限与调价窗口，本表不直接等于加油站价格。</div>
      </div>
      <div class="card"><div class="card-head"><h3>人民币汇率</h3>
        <div class="chip-row"><span class="chip">USD/CNY {fmt(intl.get('usd_cny'), 4)}</span></div></div>
        <table class="mega-table">
          <thead><tr><th>币种</th><th>代码</th><th>兑人民币</th><th>人民币兑</th></tr></thead>
          <tbody id="fxBody">{fx_rows(fx)}</tbody>
        </table>
        <div class="tfoot">汇率取自公开汇率接口的 1 美元折算口径，与银行柜台实时牌价存在点差；日元 / 韩元 / 泰铢按 100 单位展示。</div>
      </div>
    </div>
  </section>

  <!-- ============ 工具计算器 ============ -->
  <section class="section" id="tools">
    <div class="section-head">
      <div><div class="lbl">CALCULATORS · 工具</div><h2>黄金工具计算器</h2>
        <p>纯本地计算，自动读取实时基准金价与汇率。输入即算，不上传任何数据。</p></div>
    </div>
    <div class="tool-grid">
      <div class="tool-card">
        <h3>克 ↔ 金衡盎司</h3>
        <div class="field"><label>克 (g)</label><input id="t1g" type="number" step="0.01" placeholder="1"></div>
        <div class="field"><label>金衡盎司 (oz)</label><input id="t1o" type="number" step="0.0001" placeholder="0.03215"></div>
        <div class="src">1 金衡盎司 = 31.1034768 克（与日常常衡盎司 28.35g 不同）</div>
      </div>
      <div class="tool-card">
        <h3>美元金价 → 人民币金价</h3>
        <div class="field"><label>国际金价 (美元/盎司)</label><input id="t2usd" type="number" step="0.1"></div>
        <div class="field"><label>美元兑人民币</label><input id="t2fx" type="number" step="0.0001"></div>
        <div class="tool-out" id="t2out">—</div>
        <div class="src" id="t2src"></div>
      </div>
      <div class="tool-card">
        <h3>实物金买卖成本估算</h3>
        <div class="field"><label>克重 (g)</label><input id="t3g" type="number" step="0.1" value="10"></div>
        <div class="field"><label>买入价 (元/克)</label><input id="t3b" type="number" step="0.01"></div>
        <div class="field"><label>卖出 / 回收价 (元/克)</label><input id="t3s" type="number" step="0.01"></div>
        <div class="tool-out" id="t3out">—</div>
      </div>
      <div class="tool-card">
        <h3>持仓盈亏计算</h3>
        <div class="field"><label>克重 (g)</label><input id="t4g" type="number" step="0.1" value="10"></div>
        <div class="field"><label>成本价 (元/克)</label><input id="t4b" type="number" step="0.01"></div>
        <div class="field"><label>现价 (元/克)</label><input id="t4n" type="number" step="0.01"></div>
        <div class="tool-out" id="t4out">—</div>
      </div>
    </div>
  </section>

  <!-- ============ 图表 ============ -->
  <section class="section" id="charts">
    <div class="section-head">
      <div><div class="lbl">CHARTS &amp; ANALYSIS</div><h2>走势图表</h2>
        <p>分时、K 线与多品种强弱对比，从不同尺度观察价格行为。</p></div>
    </div>
    <div class="charts">
      <div class="card"><div class="card-head"><h3>{esc(sym)} 分时走势</h3><span class="badge">最近交易时段</span></div>
        <div class="chart-box"><canvas id="lineChart"></canvas></div></div>
      <div class="card"><div class="card-head"><h3>{esc(sym)} K 线</h3><span class="badge">分时聚合</span></div>
        <div class="chart-box"><canvas id="kChart"></canvas></div></div>
      <div class="card full"><div class="card-head"><h3>多品种日内强弱对比</h3>
        <div class="chip-row"><span class="chip">Au99.99 黄金</span><span class="chip">Ag99.99 白银</span><span class="chip">Pt99.95 铂金</span></div></div>
        <div class="chart-box tall"><canvas id="cmpChart"></canvas></div></div>
    </div>
    <div class="tfoot" style="margin-top:12px">K 线由分时序列按固定间隔聚合生成，用于观察日内结构，不等同于交易所日 K 线；对比图以各自时段起点归一化为 0%。</div>
  </section>

  {ad_slot()}

  <!-- ============ 价格提醒 ============ -->
  <section class="section" id="alerts">
    <div class="section-head">
      <div><div class="lbl">PRICE ALERTS</div><h2>价格提醒 · 免费</h2>
        <p>设定目标价，浏览器会在价格触发时通知你。规则只存在本机，不上传。</p></div>
    </div>
    <div class="card">
      <div class="alert-grid">
        <div>
          <div class="card-head" style="margin-bottom:10px"><h3>设置提醒</h3></div>
          <ol class="steps"><li>选择合约与方向（高于 / 低于）</li><li>填写目标价格并添加</li><li>开启浏览器通知权限，保持页面打开即可</li></ol>
          <div class="alert-row">
            <select id="alertSym" aria-label="选择合约">{sym_opts}</select>
            <select id="alertDir" aria-label="提醒方向"><option value="above">≥ 高于</option><option value="below">≤ 低于</option></select>
            <input id="alertVal" type="number" step="0.01" placeholder="目标价格" aria-label="目标价格">
            <button class="btn" id="alertAdd" type="button">添加提醒</button>
            <button class="btn ghost" id="notifyBtn" type="button">开启通知</button>
          </div>
          <button class="btn ghost" id="copyQuote" type="button" style="margin-top:4px">⧉ 复制当前行情摘要</button>
          <div class="hint" id="copyNote">提醒数据保存在浏览器 localStorage；清除浏览器数据会一并删除。页面每 60 秒检查一次最新行情并比对规则。</div>
        </div>
        <div>
          <div class="card-head" style="margin-bottom:10px"><h3>我的提醒</h3></div>
          <ul id="alertList"></ul>
        </div>
      </div>
    </div>
  </section>

</div>{side_right(data)}</div>

  {ad_slot()}

</div>
{footer_html()}
<script id="app-data" type="application/json">{data_json}</script>
<script src="./vendor/chart.umd.min.js"></script>
<script src="./vendor/chartjs-chart-financial.umd.min.js"></script>
<script src="./ads.js"></script>
<script src="./app.js"></script>
</body>
</html>"""


# ---------------------------------------------------------------- 关于页

def page_about(data):
    faq_html = "".join(
        f'<details><summary>{esc(f["q"])}</summary><div class="ans">{esc(f["a"])}</div></details>'
        for f in FAQ)
    return f"""{head_html(
        "关于本站 · 数据来源与指标算法 | 金潮网",
        "金潮网的数据来源、更新机制、国内溢价与国际折算价的计算口径，以及完整免责声明与常见问题。",
        SITE + "about.html")}
<body>
{topbar_html(data)}
{ticker_html(data)}
{nav_html('about')}
{subnav_html('about')}
<div class="wrap"><div class="portal">{side_left('')}<div class="portal-main">
  <div class="page-hero"><span class="eyebrow">ABOUT THIS SITE</span>
    <h1>数据来源与指标说明</h1>
    <p>我们尽可能把每一个数字是怎么来的讲清楚，方便你判断这些数据的适用范围。</p></div>
  <div class="doc">
    <h2 id="source">一、数据来源</h2>
    <p>本站为行情信息聚合展示，不产生原始报价。所有价格均来自以下公开渠道：</p>
    <ul>
      <li><strong>上海黄金交易所（SGE）</strong>：Au99.99、Au99.95、iAu99.99、Ag99.99、Pt99.95、Pd99.95 六个合约的最新价、今开、最高、最低与分时序列，取自交易所官方行情接口。</li>
      <li><strong>国际现货黄金 XAU/USD</strong>：取自公开的贵金属报价接口，单位为美元/金衡盎司。</li>
      <li><strong>美元兑人民币 USD/CNY</strong>：取自公开的汇率接口。</li>
    </ul>
    <p>页面每小时由自动任务抓取一次上述数据并生成静态文件。浏览器每 60 秒检查一次是否有新版本，若发现更新则自动刷新展示。非交易时段（夜间、周末、节假日）显示最近一次有效报价，不会以 0 或空值填充。</p>
    <div class="callout"><p>若某个上游接口临时不可用，系统会回退到上一次成功抓取的数据，并在下一次任务中重试，避免页面出现空白或明显错误的数字。</p></div>

    <h2 id="method">二、指标与算法</h2>
    <h3>国际折算价（元/克）</h3>
    <p>国际现货黄金以「美元 / 金衡盎司」报价，1 金衡盎司 = 31.1034768 克。折算公式为：</p>
    <p><code>国际折算价 = XAU/USD × USD/CNY ÷ 31.1034768</code></p>
    <h3>国内溢价</h3>
    <p>衡量上海黄金交易所 Au99.99 相对国际折算价的偏离程度：</p>
    <p><code>国内溢价 =（SGE Au99.99 − 国际折算价）÷ 国际折算价 × 100%</code></p>
    <p>溢价为正表示国内价格高于国际折算价，为负表示贴水。造成偏离的常见因素包括人民币汇率波动、境内实物供需、跨境流通成本与配额、以及境内外交易时段不同步。</p>
    <h3>涨跌幅</h3>
    <p>行情表中的涨跌幅以「今开」为基准计算：<code>(最新价 − 今开) ÷ 今开 × 100%</code>。按中国市场习惯，上涨以红色表示、下跌以绿色表示。</p>
    <h3>图表口径</h3>
    <p>分时图展示最近一个交易时段采集到的价格序列。K 线由该分时序列按固定间隔聚合为开、高、低、收四价，属于日内结构示意，不等同于交易所发布的日 K 线。多品种对比图把各品种序列以时段起点归一化为 0%，以便在同一坐标系下比较强弱。</p>

    <h2>三、更新与可用性</h2>
    <p>站点托管于 GitHub Pages，采用静态页面 + 定时构建的方式运行，没有后端数据库，也不要求用户登录。行情抓取、页面生成与发布均由自动化任务完成。页面本身可在桌面、平板与手机浏览器中使用，并支持浅色 / 深色主题，主题偏好保存在本机。</p>
    <p>价格提醒功能完全在浏览器本地运行：规则保存在 localStorage，比对在客户端完成，触发时通过浏览器桌面通知提示。我们不会把你的提醒规则、目标价格或任何个人信息上传到服务器。</p>

    <h2 id="faq">四、常见问题</h2>
    <p>以下是读者最常问的几个问题，点击可展开答案。</p>
  </div>
  <div class="faq-list" style="margin-top:16px">{faq_html}</div>

  <h2 style="font-size:18px;margin:34px 0 12px">五、免责声明</h2>
  <div class="doc" style="margin-top:0">
    <p>本站所有内容仅用于行情信息展示与知识科普，<strong>不构成任何投资建议、要约、招揽或交易依据</strong>。黄金及其他贵金属价格波动较大，历史表现不代表未来结果。</p>
    <p>数据可能存在延迟、缺漏或上游口径调整，最终价格请以上海黄金交易所及相关机构官方发布为准。因使用本站信息而产生的任何直接或间接损失，本站不承担责任。</p>
    <p>本页可能展示由第三方（Google AdSense）提供的广告。广告内容由广告主与广告平台决定，不代表本站立场；本站不对广告中的产品、服务或承诺作任何背书。</p>
    <p class="muted">最后更新：2026 年 11 月 · <a href="./privacy.html" style="color:var(--gold)">查看隐私政策 →</a></p>
  </div>
  {ad_slot()}
</div>{side_right(data)}</div></div>
{footer_html()}
<script src="./ads.js"></script>
</body>
</html>"""


# ---------------------------------------------------------------- 隐私页

def page_privacy(data):
    return f"""{head_html(
        "隐私政策 | 金潮网",
        "金潮网的隐私政策：说明本站如何使用 localStorage、浏览器通知、第三方广告 Cookie 以及你的选择权。",
        SITE + "privacy.html")}
<body>
{topbar_html(data)}
{ticker_html(data)}
{nav_html()}
<div class="wrap"><div class="portal">{side_left('')}<div class="portal-main">
  <div class="page-hero"><span class="eyebrow">PRIVACY POLICY</span>
    <h1>隐私政策</h1>
    <p>本站不要求注册、不要求登录，也不会主动收集你的姓名、邮箱、电话等个人身份信息。</p></div>
  <div class="doc">
    <p class="muted">生效日期：2026 年 11 月 11 日 · 最近更新：2026 年 11 月 11 日</p>

    <h2>一、我们收集哪些信息</h2>
    <p><strong>我们不收集可识别个人身份的信息。</strong>本站是纯静态站点，没有用户账户系统，没有服务端数据库，也不提供评论、留言或上传功能。你在本站填写的任何提醒规则都只保存在你自己的浏览器中。</p>
    <p>为了运行基本功能，站点会使用浏览器本地存储（localStorage）保存以下偏好：</p>
    <ul>
      <li>浅色 / 深色主题选择；</li>
      <li>你设置的价格提醒规则（合约、方向、目标价）。</li>
    </ul>
    <p>这些数据仅存在于你当前设备的当前浏览器中，不会上传给我们，也不会被用于跨设备追踪。你可以随时通过清除浏览器站点数据删除它们。</p>

    <h2>二、浏览器通知</h2>
    <p>价格提醒可选择开启浏览器桌面通知。开启时浏览器会向你请求授权，授权状态由浏览器管理，我们无法读取你的身份，也无法在页面关闭后向你推送消息。你可以随时在浏览器设置中撤回该授权。</p>

    <h2>三、Cookie 与第三方广告</h2>
    <p>本站使用 <strong>Google AdSense</strong> 展示广告。Google 及其合作伙伴可能会使用 Cookie 或类似技术，基于你访问本站及其他网站的记录投放个性化广告。</p>
    <ul>
      <li>你可以通过 <a href="https://www.google.com/settings/ads" target="_blank" rel="noopener noreferrer" style="color:var(--gold)">Google 广告设置</a> 选择停用个性化广告；</li>
      <li>也可以访问 <a href="https://www.aboutads.info" target="_blank" rel="noopener noreferrer" style="color:var(--gold)">aboutads.info</a> 停用部分第三方供应商的个性化广告 Cookie；</li>
      <li>使用浏览器自带的「阻止第三方 Cookie」或广告拦截插件，同样可以限制此类数据处理。</li>
    </ul>
    <p>如需了解 Google 如何处理数据，请参阅 <a href="https://policies.google.com/technologies/ads" target="_blank" rel="noopener noreferrer" style="color:var(--gold)">Google 广告技术与隐私说明</a>。本站不对第三方的数据处理行为负责。</p>

    <h2>四、第三方链接与外部数据源</h2>
    <p>本站包含指向上海黄金交易所等外部网站的链接。点击这些链接后，你将受目标站点自身隐私政策约束。本站行情数据来自公开接口，抓取过程不涉及任何个人信息。</p>

    <h2>五、访问日志</h2>
    <p>站点托管在 GitHub Pages 上，托管服务商可能会为安全与运维目的记录标准访问日志（如 IP 地址、请求时间、User-Agent）。这些日志由托管方管理，本站运营者不用于用户画像或营销。详情请参阅 GitHub 的隐私声明。</p>

    <h2>六、儿童隐私</h2>
    <p>本站内容面向一般公众，不针对 13 岁以下儿童，也不会有意收集儿童信息。若你认为儿童向我们提供了个人信息，请通过下述方式联系，我们会及时删除。</p>

    <h2>七、政策变更</h2>
    <p>本政策可能随功能或法律要求调整，更新后会在本页标注新的生效日期。重大变更会在首页提示。</p>

    <h2>八、联系我们</h2>
    <p>如对本隐私政策或本站数据处理有疑问，可通过项目代码仓库的 Issue 功能留言，或查看 <a href="./about.html" style="color:var(--gold)">关于本站</a> 页面了解站点信息。</p>
    <div class="callout"><p>简言之：本站没有账号、没有表单、没有后端数据库；除了浏览器本地保存的主题与提醒规则，以及第三方广告平台的 Cookie，我们不收集你的个人信息。</p></div>
  </div>
  {ad_slot()}
</div>{side_right(data)}</div></div>
{footer_html()}
<script src="./ads.js"></script>
</body>
</html>"""


# ---------------------------------------------------------------- SEO 产物

FAVICON = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
<stop offset="0" stop-color="#e6bd55"/><stop offset="1" stop-color="#b5840f"/></linearGradient></defs>
<rect width="64" height="64" rx="14" fill="url(#g)"/>
<text x="32" y="43" font-family="-apple-system,'Segoe UI',sans-serif" font-size="27" font-weight="800" fill="#231704" text-anchor="middle">Au</text>
</svg>
"""


def sitemap_xml(lastmod):
    urls = [
        (SITE, "hourly", "1.0"),
        (SITE + "data.html", "hourly", "0.9"),
        (SITE + "calendar.html", "weekly", "0.8"),
        (SITE + "news.html", "hourly", "0.8"),
        (SITE + "academy.html", "monthly", "0.7"),
        (SITE + "history.html", "daily", "0.7"),
        (SITE + "about.html", "monthly", "0.5"),
        (SITE + "privacy.html", "yearly", "0.3"),
    ]
    body = "".join(
        f"<url><loc>{loc}</loc><lastmod>{lastmod}</lastmod>"
        f"<changefreq>{freq}</changefreq><priority>{pri}</priority></url>"
        for loc, freq, pri in urls)
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + body + "\n</urlset>\n")


ROBOTS = f"""User-agent: *
Allow: /

Sitemap: {SITE}sitemap.xml
"""

MANIFEST = {
    "name": "金潮网 · 贵金属行情门户",
    "short_name": "金潮网",
    "description": "上海黄金交易所实时行情、国际金价、白银铂金钯金与多品种国内溢价",
    "start_url": "./",
    "scope": "./",
    "display": "standalone",
    "background_color": "#0e1626",
    "theme_color": "#0e1626",
    "icons": [
        {"src": "./favicon.svg", "sizes": "any", "type": "image/svg+xml", "purpose": "any"},
        {"src": "./favicon.svg", "sizes": "any", "type": "image/svg+xml", "purpose": "maskable"},
    ],
}


# IndexNow 推送密钥（Bing/360/搜狗/Yandex 收录协议）：key 文件发布在站点根目录供引擎校验
INDEXNOW_KEY = "7f62035e56707ee1c721b77b11de07f8"


# ---------------------------------------------------------------- 历史数据累积

HIST = os.path.join(DOCS, "history.json")


def update_history(data):
    """把本次行情并入按日累积的 OHLC 历史（docs/history.json 随仓库提交，永久保留）。
    当天首次记录锁定开盘价；后续构建只抬高/降低高低点并更新收盘。"""
    hist = {}
    try:
        with open(HIST, encoding="utf-8") as f:
            hist = json.load(f)
    except Exception:
        pass

    gen = str(data.get("generated_at") or "")
    today = gen[:10] if len(gen) >= 10 else datetime.date.today().isoformat()

    def upd(key, last, series):
        s = [float(x) for x in (series or []) if isinstance(x, (int, float))]
        if not s:
            if last is None:
                return
            s = [float(last)]
        h = hist.setdefault(key, {})
        day = h.get(today)
        if day:
            day["h"] = max(day["h"], max(s))
            day["l"] = min(day["l"], min(s))
            if last is not None:
                day["c"] = float(last)
        else:
            h[today] = {"o": s[0], "h": max(s), "l": min(s),
                        "c": float(last) if last is not None else s[-1]}

    for it in data.get("items") or []:
        if it.get("symbol") and it.get("last") is not None:
            upd("SGE:" + it["symbol"], it.get("last"), it.get("series"))
    intl = data.get("intl") or {}
    if intl.get("xau_usd") is not None:
        upd("INTL:XAU", intl["xau_usd"], [])
    if intl.get("usd_cny") is not None:
        upd("INTL:USDCNY", intl["usd_cny"], [])

    hist["_updated"] = gen or datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(HIST, "w", encoding="utf-8") as f:
        json.dump(hist, f, ensure_ascii=False, indent=2)
    return hist


# ---------------------------------------------------------------- 历史走势页

def history_table_rows(hist, key, limit=30):
    """key 品种的最近 N 天日线（倒序，涨跌相对前一日收盘）。"""
    h = hist.get(key) or {}
    days = sorted(h.keys())[-limit:][::-1]
    rows = []
    prev = None
    for i, day in enumerate(days):
        d = h[day]
        chg = None
        if i < len(days) - 1:
            prev_day = days[i + 1]
            pc = h[prev_day]["c"]
            if pc:
                chg = (d["c"] - pc) / pc * 100
        cls = "up" if (chg or 0) > 0 else "down" if (chg or 0) < 0 else "flat"
        chg_txt = ("—" if chg is None else
                   f'<span class="chg {cls}">{("+" if chg > 0 else "")}{chg:.2f}%</span>')
        rows.append(
            "<tr>"
            f'<td class="num" data-label="日期">{day}</td>'
            f'<td class="num" data-label="开盘">{fmt(d["o"])}</td>'
            f'<td class="num up" data-label="最高">{fmt(d["h"])}</td>'
            f'<td class="num down" data-label="最低">{fmt(d["l"])}</td>'
            f'<td class="num strong" data-label="收盘">{fmt(d["c"])}</td>'
            f'<td data-label="涨跌幅">{chg_txt}</td>'
            "</tr>")
    return "".join(rows), len(days)


def page_history(data, hist):
    au_rows, n_days = history_table_rows(hist, "SGE:Au99.99")
    if not n_days:
        au_rows = '<tr><td colspan="6" class="alert-empty" style="justify-content:center">数据累积中，明日起逐日展示。</td></tr>'
    hist_data = json.dumps({"au": hist.get("SGE:Au99.99") or {}, "xau": hist.get("INTL:XAU") or {}},
                           ensure_ascii=False)
    empty_note = "" if n_days >= 2 else (
        '<div class="callout" style="background:var(--gold-soft);border-left:3px solid var(--gold-2);'
        'padding:14px 18px;margin:14px 0;border-radius:0 10px 10px 0">'
        '<p style="margin:0;color:var(--gold-ink);font-size:13px">历史数据自今日开始逐小时累积，'
        '蜡烛图将在积累 2 天后自动出现；表格每日新增一行，30 天后趋于完整。</p></div>')
    return f"""{head_html(
        "金价历史走势_黄金价格日线历史 | 金潮网",
        "上海黄金交易所 Au99.99 黄金日线历史：每日开高低收与涨跌幅，日线蜡烛图，数据逐日自动累积。",
        SITE + "history.html")}
<body>
{topbar_html(data)}
{ticker_html(data)}
{nav_html('data')}
{subnav_html('data')}
<div class="wrap"><div class="portal">{side_left('data')}<div class="portal-main">
  <div class="page-hero"><span class="eyebrow">HISTORICAL PRICES</span>
    <h1>金价历史走势</h1>
    <p>Au99.99 黄金合约日线：每日开盘、最高、最低、收盘与涨跌幅。数据每小时自动累积，长期保存。</p></div>

  <div class="card">
    <div class="card-head"><h3>Au99.99 日线蜡烛图</h3>
      <div class="chip-row"><span class="badge">日 K · 自动累积</span><span class="chip">涨红 跌绿</span></div></div>
    {empty_note}
    <div class="chart-box tall"><canvas id="histChart"></canvas></div>
  </div>

  <div class="card" style="margin-top:16px">
    <div class="card-head"><h3>最近 30 个交易日</h3>
      <div class="chip-row"><span class="chip">单位 元/克</span></div></div>
    <table class="mega-table">
      <thead><tr><th>日期</th><th>开盘</th><th>最高</th><th>最低</th><th>收盘</th><th>涨跌幅</th></tr></thead>
      <tbody id="histBody">{au_rows}</tbody>
    </table>
    <div class="tfoot">日线由每小时抓取的行情聚合而成（当日首笔为开盘、持续更新高低与收盘）；非交易日不产生新行。本表仅供行情参考，不构成投资建议。</div>
  </div>

  {ad_slot()}
</div>{side_right(data)}</div></div>
{footer_html()}
<script id="hist-data" type="application/json">{hist_data}</script>
<script src="./vendor/chart.umd.min.js"></script>
<script src="./vendor/chartjs-chart-financial.umd.min.js"></script>
<script src="./ads.js"></script>
<script>
(function () {{
  "use strict";
  try {{
    var H = JSON.parse(document.getElementById("hist-data").textContent || "{{}}");
    var au = H.au || {{}};
    var days = Object.keys(au).sort();
    if (days.length < 2 || typeof Chart === "undefined") return;
    var candles = days.map(function (d) {{
      var x = au[d];
      return {{ x: d, o: x.o, h: x.h, l: x.l, c: x.c }};
    }});
    var el = document.getElementById("histChart");
    if (!el) return;
    new Chart(el, {{
      type: "candlestick",
      data: {{ datasets: [{{ label: "Au99.99 日线", data: candles,
        color: {{ up: "#d4380d", down: "#129b63", unchanged: "#8895a8" }} }}] }},
      options: {{
        responsive: true, maintainAspectRatio: false,
        plugins: {{ legend: {{ display: false }} }},
        scales: {{
          x: {{ ticks: {{ color: "#77839a", font: {{ size: 10 }}, maxTicksLimit: 10 }}, grid: {{ display: false }} }},
          y: {{ ticks: {{ color: "#77839a", font: {{ size: 10 }} }}, grid: {{ color: "#eef0f3" }} }}
        }}
      }}
    }});
    if (document.documentElement.classList.contains("dark")) {{
      var cs = Chart.getChart("histChart");
      if (cs) {{
        cs.options.scales.y.grid.color = "#1b2433";
        cs.update();
      }}
    }}
  }} catch (e) {{ /* 历史数据缺失时静默 */ }}
}})();
</script>
</body>
</html>"""


# ---------------------------------------------------------------- 金融快讯
def page_news(data):
    news = data.get("news") or []
    if news:
        items_html = "".join(
            f'<div class="news-item"><div class="n-time">{esc(n.get("time"))}</div>'
            f'<div class="n-body"><div class="n-title">{esc(n.get("title"))}</div>'
            f'<div class="n-text">{esc(n.get("text"))}</div></div>'
            f'<div class="n-src">{esc(n.get("source"))}</div></div>'
            for n in news)
    else:
        items_html = '<div class="news-empty">快讯数据加载中，请稍候刷新。</div>'
    head = head_html(
        "财经快讯 - 7×24 实时金融快讯 - 金潮网",
        "7×24 小时实时财经快讯流，覆盖贵金属、汇率、央行政策、全球宏观。数据来自华尔街见闻公开资讯流。",
        SITE + "news.html")
    body = f"""{topbar_html(data)}
{ticker_html(data)}
{nav_html("news")}
{subnav_html("news")}
<div class="wrap"><div class="portal">{side_left('news')}<div class="portal-main">
  <section class="section" id="live">
    <div class="section-head">
      <div><div class="lbl">NEWS · 金融快讯</div><h2>7×24 实时财经快讯</h2>
        <p>覆盖贵金属、央行政策、汇率与全球宏观。每 30 分钟随数据管道自动更新。</p></div>
      <div class="side">数据源：华尔街见闻</div>
    </div>
    <div class="card">
      <div class="card-head"><h3>最新快讯</h3>
        <div class="chip-row"><span class="badge">◷ 自动更新</span><span class="chip">{len(news)} 条</span></div></div>
      <div class="news-list">{items_html}</div>
    </div>
    <div class="note-strip" style="margin-top:18px">
      <div class="ni">◈</div>
      <div class="nt"><strong>资讯来源说明</strong>
        <span>快讯内容来自华尔街见闻公开资讯流，由本站聚合展示；版权归原发布方所有。本站不对资讯内容作任何投资建议。</span></div>
      <a class="btn ghost" href="./calendar.html">看财经日历 →</a>
    </div>
  </section>
</div>{side_right(data)}</div></div>
{footer_html()}
<script id="app-data" type="application/json">{json.dumps({}, ensure_ascii=False)}</script>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
<script src="https://cdn.jsdelivr.net/npm/chartjs-chart-financial@0.2.1"></script>
<script src="./ads.js"></script>
<script src="./common.js"></script>
<script src="./app.js"></script>
</body></html>"""
    return head + body


# ---------------------------------------------------------------- 财经日历
# 2026 年 FOMC 议息日程（来源：美联储官网 fomccalendars.htm）
FOMC_2026 = [
    ("1月27-28日", "1月28日", False, "1月27-28日议息会议"),
    ("3月17-18日", "3月18日", True, "含经济预测与点阵图"),
    ("4月28-29日", "4月29日", False, "常规议息会议"),
    ("6月16-17日", "6月17日", True, "含经济预测与点阵图"),
    ("7月28-29日", "7月29日", False, "常规议息会议"),
    ("9月15-16日", "9月16日", True, "含经济预测与点阵图"),
    ("10月27-28日", "10月28日", False, "常规议息会议"),
    ("12月8-9日", "12月9日", True, "含经济预测与点阵图"),
]

# 近期重点经济事件（来源：美联储官网 + 交易商公开日历，均经核实；时间均为北京时间）
ECON_EVENTS = [
    ("2026-12-04 周五 21:30", "美国 11 月非农就业人口", "高", "约 +2.9 万（10月）", "美国劳工统计局每月首个周五公布，直接影响美联储政策预期"),
    ("2026-12-08-09 周二三", "美联储 FOMC 议息会议（12月）", "高", "3.75-4.00%（10月）", "12月 8-9 日召开，9 日 03:00 公布利率决议，含经济预测与点阵图"),
    ("2026-12-10 周四 21:30", "美国 11 月 CPI 同比", "高", "3.7%（10月）", "通胀核心指标，直接牵引利率预期与金价"),
    ("2026-12-17 周四", "欧洲央行利率决议", "中", "2.50%", "欧元区政策利率，影响美元指数与金价"),
    ("2026-12-18 周五", "日本央行利率决议", "中", "1.25%", "影响日元汇率与全球套息交易"),
    ("2027-01-22 周五", "日本央行利率决议", "中", "—", "2027 年首次议息"),
    ("2027-01-27-28 周三四", "美联储 FOMC 议息会议（2027年1月）", "高", "—", "2027 年首次议息，含经济预测"),
]

# 各国央行利率决议节奏（来源：各国央行官网公开日历）
CENTRAL_BANKS = [
    ("美联储 FED", "每年 8 次议息（1/3/4/6/7/9/10/12 月）", "3.75-4.00%", "2025-12-10 降 25bp"),
    ("欧洲央行 ECB", "每年约 8 次，通常 1/3/4/6/7/9/10/12 月", "2.50%", "2025-09-10 降 25bp"),
    ("日本央行 BOJ", "每年约 8 次，季度末含展望报告", "1.25%", "2026-09-18 加 25bp"),
    ("中国人民银行 PBOC", "每月 20 日公布 LPR；MLF/逆回购每日操作", "1 年 LPR 3.0%", "2025-05-20 调降"),
    ("英国央行 BOE", "每年 8 次议息", "3.75%", "2025-12-18 降 25bp"),
]


def page_calendar(data):
    events_html = "".join(
        f'<div class="cal-item imp-{"high" if imp=="高" else "mid" if imp=="中" else "low"}">'
        f'<div class="ci-date">◷ {esc(date)}</div>'
        f'<div class="ci-name">{esc(name)}</div>'
        f'<div class="ci-meta">前值 / 现值：{esc(prev)}<br>{esc(desc)}</div>'
        f'<span class="ci-imp">{"★ 高重要性" if imp=="高" else "◆ 中重要性" if imp=="中" else "◇ 低重要性"}</span>'
        f'</div>'
        for date, name, imp, prev, desc in ECON_EVENTS)

    fomc_rows = "".join(
        f'<tr><td><strong>{esc(meet)}</strong></td><td>{esc(dec)}</td>'
        f'<td class="{"star" if star else ""}">{"★ 是" if star else "—"}</td><td>{esc(note)}</td></tr>'
        for meet, dec, star, note in FOMC_2026)

    cb_rows = "".join(
        f'<tr><td><strong>{esc(name)}</strong></td><td>{esc(freq)}</td>'
        f'<td>{esc(rate)}</td><td>{esc(last)}</td></tr>'
        for name, freq, rate, last in CENTRAL_BANKS)

    head = head_html(
        "财经日历 - 美联储议息/非农/CPI 时间表 - 金潮网",
        "2026-2027 年重要财经事件日历：美联储 FOMC 八次议息日程、美国非农与 CPI 公布时间、各国央行利率决议节奏。日期来源为官方公开日程。",
        SITE + "calendar.html")
    body = f"""{topbar_html(data)}
{ticker_html(data)}
{nav_html("calendar")}
{subnav_html("calendar")}
<div class="wrap"><div class="portal">{side_left('calendar')}<div class="portal-main">
  <section class="section" id="events">
    <div class="section-head">
      <div><div class="lbl">CALENDAR · 财经日历</div><h2>重要经济事件日历</h2>
        <p>与金价直接相关的核心事件：非农、CPI、美联储议息、各国央行决议。时间为北京时间。</p></div>
      <div class="side">日期来源：官方公开日程</div>
    </div>
    <div class="cal-grid">{events_html}</div>
    <div class="note-strip" style="margin-top:18px">
      <div class="ni">◈</div>
      <div class="nt"><strong>日历说明</strong>
        <span>非农每月首个周五 21:30（夏令时 20:30）、CPI 每月月中前后公布；具体日期以美国劳工统计局当月公告为准。FOMC 日程来自美联储官网公开议程。</span></div>
    </div>
  </section>

  <section class="section" id="fomc">
    <div class="section-head">
      <div><div class="lbl">FEDERAL RESERVE</div><h2>2026 年 FOMC 议息日程</h2>
        <p>美联储每年召开 8 次议息会议；标注「★」的会议发布经济预测摘要（SEP）与点阵图，通常引发更大波动。</p></div>
      <div class="side">来源：federalreserve.gov</div>
    </div>
    <div class="card">
      <div class="card-head"><h3>2026 年议息会议</h3>
        <div class="chip-row"><span class="chip">8 次会议</span><span class="badge">4 次含点阵图</span></div></div>
      <table class="fomc-table">
        <thead><tr><th>会期</th><th>决议公布日</th><th>点阵图 / SEP</th><th>备注</th></tr></thead>
        <tbody>{fomc_rows}</tbody>
      </table>
      <div class="phys-note" style="margin-top:14px"><b>决议发布时间：</b>美联储在会期第二日美东时间 14:00 发布声明（北京时间次日凌晨 02:00 / 夏令时 03:00），主席新闻会 30 分钟后召开。纪要于会后第三周公布。</div>
    </div>
  </section>

  <section class="section" id="cb">
    <div class="section-head">
      <div><div class="lbl">CENTRAL BANKS</div><h2>各国央行利率决议节奏</h2>
        <p>主要央行的议息频率、当前利率与最近一次变动（截至 2026 年 11 月）。</p></div>
    </div>
    <div class="card">
      <table class="fomc-table">
        <thead><tr><th>央行</th><th>议息节奏</th><th>当前利率</th><th>最近一次变动</th></tr></thead>
        <tbody>{cb_rows}</tbody>
      </table>
    </div>
    <div class="rel-grid" style="margin-top:18px">
      <a class="rel" href="./index.html#charts"><div class="rt">金价走势</div><p>事件前后的价格反应，看走势图表</p></a>
      <a class="rel" href="./news.html"><div class="rt">即时快讯</div><p>事件公布瞬间的市场反应</p></a>
      <a class="rel" href="./academy.html"><div class="rt">投资学院</div><p>非农 / CPI 如何影响金价</p></a>
      <a class="rel" href="./data.html"><div class="rt">数据中心</div><p>利率周期下的金价表现</p></a>
    </div>
  </section>
</div>{side_right(data)}</div></div>
{footer_html()}
<script id="app-data" type="application/json">{json.dumps({}, ensure_ascii=False)}</script>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
<script src="./ads.js"></script>
<script src="./common.js"></script>
<script src="./app.js"></script>
</body></html>"""
    return head + body


# ---------------------------------------------------------------- 投资学院
ACAD_ARTICLES = [
    {"cat": "基础入门", "no": "01", "h": "一克黄金多少钱？金价单位与换算速查",
     "p": ["国内黄金以「元/克」计价，国际黄金以「美元/盎司」计价。1 金衡盎司 = 31.1034768 克。",
           "换算公式：人民币金价 = 美元金价 × 美元兑人民币 ÷ 31.1035。本站的「工具计算」板块可实时换算。"]},
    {"cat": "基础入门", "no": "02", "h": "Au99.99 是什么？SGE 常见合约一览",
     "p": ["Au99.99 指含金量 99.99% 的黄金现货合约，是上海黄金交易所最活跃的现货品种。",
           "Au99.95（99.95%）、Au100g（100 克小金条）、Au(T+D) 延期交收、Ag99.99 白银、Pt99.95 铂金、Pd99.95 钯金。"]},
    {"cat": "基础入门", "no": "03", "h": "国际金价与国内金价为何不一样？",
     "p": ["国际金价以美元/盎司计价，国内金价以人民币/克计价。两者折算后的价差叫「国内溢价」。",
           "溢价为正，说明境内金比国际贵，常见于实物需求旺、进口配额紧；为负称贴水。"]},
    {"cat": "实物黄金", "no": "04", "h": "基础金价和金店价格差在哪里？",
     "p": ["基础金价是 SGE Au99.99 现货报价，是投资金条、积存金与首饰定价的锚点。",
           "金店价格 = 基础金价 + 工费 + 品牌溢价。投资金条约 +8~15 元/克，足金首饰常 +60~120 元/克，3D/古法金更高。"]},
    {"cat": "实物黄金", "no": "05", "h": "黄金首饰怎么回收？回购折价怎么算？",
     "p": ["金店/机构回购实物金时，通常低于基础金价 4~8 元/克。回收按克重计，与你买时的工费无关。",
           "买入到卖出之间必须跨越的折价 + 工费，就是实物金的交易成本。"]},
    {"cat": "实物黄金", "no": "06", "h": "3D 硬金、古法金、K 金怎么选？",
     "p": ["3D 硬金是电铸工艺足金，硬度高、造型立体，按「一口价」卖、克单价远高于基础金价。",
           "K 金是黄金合金，18K≈75% 含金量，硬度高适合镶嵌。回收时都按克重 × 含金量计算。"]},
    {"cat": "投资工具", "no": "07", "h": "黄金 ETF vs 实物金 vs 积存金，怎么选？",
     "p": ["黄金 ETF（如 518880）在证券账户买卖，门槛低、流动性好，跟踪金价。",
           "积存金适合定投，可提实物；实物金条适合长期持有，但有工费与回购折价。"]},
    {"cat": "投资工具", "no": "08", "h": "Au(T+D) 延期合约：杠杆、递延费与风险",
     "p": ["Au(T+D) 是保证金交易（约 8~12 倍杠杆），可多空双向，日内交易活跃。",
           "递延费是多空失衡时一方每日向另一方支付的费用，方向每日可能切换，长期持仓不可忽视。"]},
    {"cat": "投资工具", "no": "09", "h": "黄金价格提醒怎么设置才有效？",
     "p": ["价格提醒应设置在关键价位（如前高前低、整数关口、溢价极值）。",
           "本站的「价格提醒」功能支持设置高于/低于某值通知，浏览器通知免费无门槛。"]},
    {"cat": "宏观分析", "no": "10", "h": "美联储利率如何影响金价？",
     "p": ["利率上升 → 持有黄金的机会成本上升 → 金价承压；利率下降 → 金价获支撑。",
           "实际利率（名义利率 − 通胀）是金价的长期锚：实际利率下行，金价上行。"]},
    {"cat": "宏观分析", "no": "11", "h": "非农、CPI 与金价：交易日历怎么看？",
     "p": ["非农（每月首个周五）与 CPI（每月月中）是美联储决策的核心输入，公布瞬间金价常剧烈波动。",
           "本站「财经日历」板块提供 2026-2027 年完整 FOMC 日程与非农/CPI 时间表。"]},
    {"cat": "宏观分析", "no": "12", "h": "人民币汇率：在岸、离岸与中间价的区别",
     "p": ["中间价由央行每日公布；在岸（CNY）在境内市场波动 ±2%；离岸（CNH）在境外市场自由波动。",
           "人民币贬值时，即使国际金价横盘，以人民币计价的国内金价也会走高——这也是本站同时展示汇率与国内溢价的原因。"]},
    {"cat": "数据指标", "no": "13", "h": "金银比、金油比、金铂比：从比值看相对价值",
     "p": ["金银比 = 金价 ÷ 银价，历史区间约 40~90，比值极高时白银可能补涨。",
           "金油比 = 金价 ÷ 油价，反映避险需求强弱；金铂比类似，用于观察贵金属内部分化。"]},
    {"cat": "数据指标", "no": "14", "h": "国内溢价指标：从溢价看实物需求",
     "p": ["溢价 =（SGE 价 − 国际折算价）÷ 国际折算价 × 100%。",
           "溢价持续为正且扩大，往往对应国内实物需求旺、进口配额紧；溢价转负则可能预示需求走弱。"]},
    {"cat": "数据指标", "no": "15", "h": "通胀保值：黄金是抗通胀资产吗？",
     "p": ["长期看，黄金对恶性通胀有保值作用；但温和通胀时期，实际利率若上升，金价也会承压。",
           "黄金的「抗通胀」属性主要体现在长期（10 年以上）维度，短期波动大，不能简单等同于通胀保值工具。"]},
    {"cat": "风险教育", "no": "16", "h": "杠杆交易的风险：为什么 T+D 容易爆仓",
     "p": ["杠杆放大收益的同时放大亏损。8 倍杠杆下，金价反向波动 12% 即可亏损全部保证金。",
           "控制仓位、设置止损、避免满仓，是杠杆交易的基本纪律。"]},
    {"cat": "风险教育", "no": "17", "h": "警惕「金店回购陷阱」与高溢价销售",
     "p": ["部分「一口价」金饰的克单价远高于基础金价，回收时却按克重计算，价差可达 200+ 元/克。",
           "买前先算克单价，对比基础金价；投资需求优先选按克计价的金条。"]},
    {"cat": "风险教育", "no": "18", "h": "常见黄金投资误区",
     "p": ["误区一：金价只涨不跌——黄金波动率不低，短期回撤 10%+ 常见。",
           "误区二：首饰=投资——首饰含工费，回收折价大，不是好的投资载体。",
           "误区三：看涨就加杠杆——杠杆是工具不是策略，仓位管理才是。"]},
]


def page_academy(data):
    cats = sorted(set(a["cat"] for a in ACAD_ARTICLES))
    cards = "".join(
        f'<article class="acad-card" data-cat="{esc(a["cat"])}">'
        f'<span class="a-tag">{esc(a["cat"])}</span>'
        f'<h3>{esc(a["h"])}</h3>'
        f'<p>{" ".join(esc(x) for x in a["p"])}</p>'
        f'<div class="a-no">GUIDE {esc(a["no"])}</div></article>'
        for a in ACAD_ARTICLES)
    cat_html = "".join(
        f'<button class="acad-cat{"" if i else " sel"}" data-cat="{esc(c)}">{esc(c)}</button>'
        for i, c in enumerate(cats))
    glossary_html = "".join(
        f'<div class="gloss"><h4>{esc(g["t"])}</h4><p>{esc(g["d"])}</p></div>'
        for g in GLOSSARY)
    faq_html = "".join(
        f'<details><summary>{esc(f["q"])}</summary><div class="ans">{esc(f["a"])}</div></details>'
        for f in FAQ)
    head = head_html(
        "投资学院 - 黄金投资入门到进阶 - 金潮网",
        "黄金投资学院：18 篇系统科普（基础入门、实物黄金、投资工具、宏观分析、数据指标、风险教育）+ 15 条术语速查 + 常见问题。",
        SITE + "academy.html")
    body = f"""{topbar_html(data)}
{ticker_html(data)}
{nav_html("academy")}
{subnav_html("academy")}
<div class="wrap"><div class="portal">{side_left('academy')}<div class="portal-main">
  <section class="section" id="articles">
    <div class="section-head">
      <div><div class="lbl">ACADEMY · 投资学院</div><h2>黄金投资系统学习</h2>
        <p>从「一克黄金多少钱」到「美联储利率如何影响金价」，18 篇科普按六大主题分类，零基础也能看懂。</p></div>
      <div class="side">18 篇 · 6 大主题</div>
    </div>
    <div class="acad-cats" id="acadCats">{cat_html}
      <button class="acad-cat sel" data-cat="all">全部</button></div>
    <div class="rel-grid" id="acadGrid" style="grid-template-columns:repeat(3,minmax(0,1fr))">{cards}</div>
    <div class="note-strip" style="margin-top:20px">
      <div class="ni">◈</div>
      <div class="nt"><strong>内容定位</strong>
        <span>全部文章为投资知识科普，不构成任何投资建议。投资有风险，决策需独立判断。</span></div>
    </div>
  </section>

  <section class="section" id="glossary">
    <div class="section-head">
      <div><div class="lbl">GLOSSARY · 术语表</div><h2>黄金 / 贵金属术语速查</h2>
        <p>15 个高频术语，读懂行情表与实物金价背后的口径差异。</p></div>
    </div>
    <div class="glossary">{glossary_html}</div>
  </section>

  <section class="section" id="faq">
    <div class="section-head">
      <div><div class="lbl">FAQ · 常见问题</div><h2>投资常见疑问</h2></div>
    </div>
    <div class="card"><div class="faq-list">{faq_html}</div></div>
    <div class="rel-grid" style="margin-top:18px">
      <a class="rel" href="./index.html#tools"><div class="rt">工具计算</div><p>克↔盎司、人民币金价、盈亏计算</p></a>
      <a class="rel" href="./index.html#physical"><div class="rt">实物金价</div><p>金条 / 回收 / 首饰价格估算</p></a>
      <a class="rel" href="./calendar.html"><div class="rt">财经日历</div><p>非农 / CPI / FOMC 时间表</p></a>
      <a class="rel" href="./data.html"><div class="rt">数据中心</div><p>金银比、溢价等关键指标</p></a>
    </div>
  </section>
</div>{side_right(data)}</div></div>
{footer_html()}
<script id="app-data" type="application/json">{json.dumps({}, ensure_ascii=False)}</script>
<script src="./ads.js"></script>
<script src="./common.js"></script>
<script>
(function(){{
  var cats=document.getElementById('acadCats');
  if(!cats)return;
  cats.addEventListener('click',function(e){{
    var b=e.target.closest('.acad-cat'); if(!b)return;
    cats.querySelectorAll('.acad-cat').forEach(function(x){{x.classList.remove('sel')}});
    b.classList.add('sel');
    var c=b.getAttribute('data-cat');
    document.querySelectorAll('#acadGrid .acad-card').forEach(function(card){{
      card.style.display=(c==='all'||card.getAttribute('data-cat')===c)?'':'none';
    }});
  }});
}})();
</script>
</body></html>"""
    return head + body


# ---------------------------------------------------------------- 数据中心
def page_data(data, hist):
    intl = data.get("intl") or {}
    mets = intl.get("metals") or {}
    gold = mets.get("gold") or {}
    silver = mets.get("silver") or {}
    plat = mets.get("platinum") or {}
    pall = mets.get("palladium") or {}
    oil = data.get("oil") or {}
    fx = data.get("fx") or []

    # 衍生指标
    def ratio(a, b, unit=""):
        try:
            if a and b and float(b) != 0:
                return f"{float(a)/float(b):,.2f}{unit}"
        except Exception:
            pass
        return "—"

    gold_last = gold.get("sge")
    silver_last = silver.get("sge")
    plat_last = plat.get("sge")
    brent_last = (oil.get("brent") or {}).get("last")
    xau_usd = intl.get("xau_usd")
    usd_cny = intl.get("usd_cny")

    gold_silver = ratio(gold_last, (silver_last or 0) / 1000 if silver_last else None)  # 元/克 vs 元/克
    gold_oil = ratio(gold_last, brent_last)
    gold_plat = ratio(gold_last, plat_last)

    ind_cards = (
        f'<div class="ind-card"><div class="ik">金银比 (Au/Ag)</div><div class="iv">{gold_silver}</div><div class="iu">金价 ÷ 银价（克口径）</div></div>'
        f'<div class="ind-card"><div class="ik">金油比 (Au/Brent)</div><div class="iv">{gold_oil}</div><div class="iu">元/克 ÷ 美元/桶</div></div>'
        f'<div class="ind-card"><div class="ik">金铂比 (Au/Pt)</div><div class="iv">{gold_plat}</div><div class="iu">金价 ÷ 铂金价</div></div>'
        f'<div class="ind-card"><div class="ik">美元兑人民币</div><div class="iv">{fmt(usd_cny, 4)}</div><div class="iu">实时汇率</div></div>'
        f'<div class="ind-card"><div class="ik">国际金价 (XAU)</div><div class="iv">{fmt(xau_usd)}</div><div class="iu">美元/盎司</div></div>'
        f'<div class="ind-card"><div class="ik">黄金国内溢价</div><div class="iv {"up" if (gold.get("premium_pct") or 0) >= 0 else "down"}">{fmt(gold.get("premium_pct"))}%</div><div class="iu">SGE vs 国际折算</div></div>'
        f'<div class="ind-card"><div class="ik">白银国内溢价</div><div class="iv {"up" if (silver.get("premium_pct") or 0) >= 0 else "down"}">{fmt(silver.get("premium_pct"))}%</div><div class="iu">Ag99.99 vs 国际折算</div></div>'
        f'<div class="ind-card"><div class="ik">钯金国际价</div><div class="iv">{fmt(pall.get("intl_usd"))}</div><div class="iu">美元/盎司</div></div>'
    )

    # 汇率表（完整）
    fx_rows_html = "".join(
        f'<tr><td class="lbl">{esc(r.get("name"))}</td><td class="sym">{esc(r.get("code"))}</td>'
        f'<td class="num strong">{fmt(r.get("cny"), 4)}</td>'
        f'<td class="num">{fmt(r.get("per_cny"), 4)}</td></tr>'
        for r in fx)

    # 溢价明细
    prem_rows = ""
    for key, label in (("gold", "黄金 Au99.99"), ("silver", "白银 Ag99.99"),
                       ("platinum", "铂金 Pt99.95"), ("palladium", "钯金 Pd99.95")):
        x = mets.get(key) or {}
        if x.get("sge") is None and x.get("premium_pct") is None:
            continue
        cls = "up" if (x.get("premium_pct") or 0) >= 0 else "down"
        prem_rows += (
            f'<tr><td class="lbl">{label}</td><td class="num">{fmt(x.get("sge"))} <span class="unit">{esc(x.get("unit"))}</span></td>'
            f'<td class="num">{fmt(x.get("intl_cny"))}</td>'
            f'<td><span class="chg {cls}">{fmt(x.get("premium_pct"))}%</span></td>'
            f'<td class="unit">{esc(x.get("intl_symbol"))}</td></tr>')

    # 历史数据（Au99.99 最近 15 天）
    au_hist = hist.get("SGE:Au99.99") or {}
    hist_rows, _hist_n = history_table_rows(hist, "SGE:Au99.99", limit=15)

    head = head_html(
        "数据中心 - 金银比/国内溢价/汇率/历史走势 - 金潮网",
        "贵金属数据中心：金银比、金油比、金铂比等关键指标看板，国内溢价明细，11 币种汇率表，Au99.99 历史日线数据。",
        SITE + "data.html")
    body = f"""{topbar_html(data)}
{ticker_html(data)}
{nav_html("data")}
{subnav_html("data")}
<div class="wrap"><div class="portal">{side_left('data')}<div class="portal-main">
  <section class="section" id="indicators">
    <div class="section-head">
      <div><div class="lbl">DATA CENTER · 数据中心</div><h2>关键指标看板</h2>
        <p>金银比、金油比、溢价与汇率——一屏看懂贵金属的相对价值与境内外价差。随数据管道每 30 分钟更新。</p></div>
      <div class="side">数据生成：{esc(data.get("generated_at") or "—")}</div>
    </div>
    <div class="ind-grid">{ind_cards}</div>
  </section>

  <section class="section" id="premium">
    <div class="section-head">
      <div><div class="lbl">PREMIUM</div><h2>多品种国内溢价明细</h2>
        <p>境内 SGE 报价 vs 国际现货折算（国际金价 × 汇率 ÷ 31.1035）。为正=境内贵，为负=贴水。</p></div>
    </div>
    <div class="card">
      <table>
        <thead><tr><th>品种</th><th>境内报价</th><th>国际折算</th><th>国内溢价</th><th>口径</th></tr></thead>
        <tbody>{prem_rows}</tbody>
      </table>
    </div>
  </section>

  <section class="section" id="fx">
    <div class="section-head">
      <div><div class="lbl">FOREX</div><h2>汇率一览（11 币种）</h2>
        <p>美元、欧元、日元、英镑等主流币种兑人民币，以及人民币兑各币种。</p></div>
    </div>
    <div class="card">
      <table>
        <thead><tr><th>币种</th><th>代码</th><th>兑人民币</th><th>人民币兑</th></tr></thead>
        <tbody>{fx_rows_html}</tbody>
      </table>
    </div>
  </section>

  <section class="section" id="history">
    <div class="section-head">
      <div><div class="lbl">HISTORY</div><h2>Au99.99 历史日线（近 15 日）</h2>
        <p>每日开高低收数据，随站点运行逐日累积。</p></div>
      <div class="side"><a class="btn ghost" href="./history.html">看完整走势图 →</a></div>
    </div>
    <div class="card">
      <table>
        <thead><tr><th>日期</th><th>开盘</th><th>最高</th><th>最低</th><th>收盘</th><th>涨跌幅</th></tr></thead>
        <tbody>{hist_rows}</tbody>
      </table>
    </div>
    <div class="rel-grid" style="margin-top:18px">
      <a class="rel" href="./history.html"><div class="rt">历史走势图</div><p>日线蜡烛图与每日开高低收</p></a>
      <a class="rel" href="./index.html#charts"><div class="rt">实时图表</div><p>分时 / K 线 / 多品种对比</p></a>
      <a class="rel" href="./calendar.html"><div class="rt">财经日历</div><p>数据发布日程</p></a>
      <a class="rel" href="./academy.html"><div class="rt">投资学院</div><p>读懂金银比与溢价</p></a>
    </div>
  </section>
</div>{side_right(data)}</div></div>
{footer_html()}
<script id="app-data" type="application/json">{json.dumps({}, ensure_ascii=False)}</script>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
<script src="./ads.js"></script>
<script src="./common.js"></script>
<script src="./app.js"></script>
</body></html>"""
    return head + body


# ---------------------------------------------------------------- 入口

def main():
    data = load_data()
    os.makedirs(DOCS, exist_ok=True)

    hist = update_history(data)

    pages = [
        (os.path.join(DOCS, "index.html"), page_index(data)),
        (os.path.join(DOCS, "data.html"), page_data(data, hist)),
        (os.path.join(DOCS, "calendar.html"), page_calendar(data)),
        (os.path.join(DOCS, "news.html"), page_news(data)),
        (os.path.join(DOCS, "academy.html"), page_academy(data)),
        (os.path.join(DOCS, "about.html"), page_about(data)),
        (os.path.join(DOCS, "privacy.html"), page_privacy(data)),
        (os.path.join(DOCS, "history.html"), page_history(data, hist)),
    ]
    for path, content in pages:
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

    with open(os.path.join(DOCS, "site.css"), "w", encoding="utf-8") as f:
        f.write(CSS)

    # 前端 ./data.json 副本（60s 轮询用）
    with open(os.path.join(DOCS, "data.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    # SEO 三件套 + PWA manifest
    gen = str(data.get("generated_at") or "")
    lastmod = (gen[:10] if len(gen) >= 10 else
               datetime.date.today().isoformat())
    with open(os.path.join(DOCS, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write(sitemap_xml(lastmod))
    with open(os.path.join(DOCS, "robots.txt"), "w", encoding="utf-8") as f:
        f.write(ROBOTS)
    with open(os.path.join(DOCS, "favicon.svg"), "w", encoding="utf-8") as f:
        f.write(FAVICON)
    with open(os.path.join(DOCS, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(MANIFEST, f, ensure_ascii=False, indent=2)

    # IndexNow key 校验文件（必须位于 https://<host>/<key>.txt）
    with open(os.path.join(DOCS, INDEXNOW_KEY + ".txt"), "w", encoding="utf-8") as f:
        f.write(INDEXNOW_KEY)

    print("[ok] 已生成 index/about/privacy/history + sitemap/robots/favicon/manifest "
          f"（{len(data.get('items', []))} 个合约，历史 {sum(1 for k in hist if k.startswith('SGE:'))} 品种）")


if __name__ == "__main__":
    main()
