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
.wrap{max-width:1180px;margin:0 auto;padding:0 24px}
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
.foot-grid{display:grid;grid-template-columns:1.6fr 1fr 1fr 1.2fr;gap:32px;padding:44px 0 34px}
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
  .foot-grid{grid-template-columns:1.4fr 1fr 1fr;gap:24px}
  .foot-grid .foot-col:last-child{grid-column:1/-1}
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
  .foot-grid{grid-template-columns:1fr 1fr;gap:24px;padding:34px 0 26px}
  .foot-brand{grid-column:1/-1}
  .foot-grid .foot-col:last-child{grid-column:1/-1}
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
  .foot-grid{grid-template-columns:1fr}
  .topbar .tb-r{width:100%;margin-left:0;padding-bottom:6px}
}
@media(max-width:360px){
  .hero-side{grid-template-columns:1fr}
}
@media(prefers-reduced-motion:reduce){
  *{animation-duration:.001ms!important;transition-duration:.001ms!important}
  html{scroll-behavior:auto}
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
<meta name="keywords" content="今日金价,黄金价格,实时金价,上海黄金交易所,Au99.99,国际金价,国内溢价,白银价格,铂金价格,黄金走势">
<meta name="author" content="今日金价">
<meta name="robots" content="index,follow">
<meta property="og:site_name" content="今日金价 · REAL-TIME GOLD MARKET">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:type" content="website">
<meta property="og:url" content="{esc(canonical)}">
<link rel="canonical" href="{esc(canonical)}">
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
    if not chips:
        chips = ['<div class="tk"><span class="tk-n">行情加载中</span></div>']
    track = "".join(chips + chips)  # 复制一份实现无缝滚动
    return ('<div class="ticker"><div class="ticker-inner">'
            '<div class="ticker-label">◈ 实时行情</div>'
            f'<div class="ticker-view"><div class="ticker-track">{track}</div></div>'
            '</div></div>')


def nav_html(active=""):
    links = [
        ("overview", "./index.html#overview", "行情概览"),
        ("quotes", "./index.html#quotes", "实时行情"),
        ("charts", "./index.html#charts", "走势图表"),
        ("alerts", "./index.html#alerts", "价格提醒"),
        ("learn", "./index.html#learn", "黄金百科"),
        ("about", "./about.html", "关于本站"),
    ]
    parts = []
    for key, url, text in links:
        cls = "active" if key == active else ""
        parts.append(f'<a href="{url}" class="{cls}">{text}</a>')
    a = "".join(parts)
    return f"""<header class="nav"><div class="wrap">
  <a class="brand" href="./index.html" aria-label="今日金价 首页">
    <span class="brand-mark">Au</span>
    <span class="brand-txt"><strong>今日金价</strong><small>Real-time Gold Market</small></span>
  </a>
  <nav class="nav-menu" id="navMenu">{a}</nav>
  <div class="nav-act">
    <button class="icon-btn" id="themeBtn" type="button" aria-label="切换深浅色">🌓 <span>主题</span></button>
    <button class="nav-toggle" id="navToggle" type="button" aria-label="打开菜单">☰</button>
  </div>
</div></header>"""


def footer_html():
    return f"""<footer class="site">
  <div class="wrap foot-grid">
    <div class="foot-brand">
      <a class="brand" href="./index.html" style="margin-bottom:6px">
        <span class="brand-mark">Au</span>
        <span class="brand-txt"><strong>今日金价</strong><small>Real-time Gold Market</small></span>
      </a>
      <p>一屏看懂国内金价、国际金价、汇率与国内溢价。数据聚合展示，仅供参考，不构成投资建议。</p>
    </div>
    <div class="foot-col"><h4>行情</h4>
      <a href="./index.html#overview">行情概览</a><a href="./index.html#quotes">实时行情表</a>
      <a href="./index.html#charts">走势图表</a><a href="./index.html#alerts">价格提醒</a></div>
    <div class="foot-col"><h4>知识</h4>
      <a href="./index.html#learn">黄金百科</a><a href="./about.html#method">指标与算法</a>
      <a href="./about.html#source">数据来源</a><a href="./about.html#faq">常见问题</a></div>
    <div class="foot-col"><h4>站点</h4>
      <a href="./about.html">关于本站</a><a href="./privacy.html">隐私政策</a>
      <a href="https://www.sge.com.cn/" target="_blank" rel="noopener noreferrer">上海黄金交易所 ↗</a>
      <a href="{SITE}">返回首页</a></div>
  </div>
  <div class="wrap foot-bottom">
    <strong>免责声明：</strong>本站为行情信息聚合展示，价格以上海黄金交易所及相应机构官方发布为准。
    所有内容仅供信息参考，不构成任何投资建议、要约或交易依据。黄金价格波动较大，投资需自行判断并承担风险。<br>
    数据更新：每小时自动抓取 · 浏览器每 60 秒检查更新 · 非交易时段显示最近一次有效报价<br>
    © 2026 今日金价 · 页面含第三方广告（Google AdSense），广告内容由第三方提供，与本站点立场无关。
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

    website_ld = json.dumps({
        "@context": "https://schema.org", "@type": "WebSite", "name": "今日金价",
        "url": SITE, "description": "实时黄金价格、上海黄金交易所行情、国际金价与国内溢价",
        "inLanguage": "zh-CN"}, ensure_ascii=False)
    ld = (f'<script type="application/ld+json">{faq_ld(FAQ)}</script>\n'
          f'<script type="application/ld+json">{website_ld}</script>')

    prem = intl.get("premium_pct")
    prem_cls = "up" if (prem or 0) >= 0 else "down"
    prem_txt = f"{prem:+.2f}%" if prem is not None else "—"

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
        "今日金价_实时黄金价格_上海黄金交易所行情 | 国内溢价",
        "实时黄金价格：上海黄金交易所 Au99.99 等合约最新价、国际现货黄金 XAU/USD、美元兑人民币汇率及国内溢价测算，附分时走势、K 线与黄金知识百科。",
        SITE, ld)}
<body>
{topbar_html(data)}
{ticker_html(data)}
{nav_html('overview')}

<div class="wrap">

  <!-- ============ HERO ============ -->
  <section class="hero-wrap" id="overview">
    <div class="hero">
      <div class="hero-grid">
        <div>
          <span class="eyebrow">SHANGHAI GOLD EXCHANGE · LIVE</span>
          <h1>今日金价，一屏看懂</h1>
          <p class="lead">国内现货 · 国际金价 · 汇率 · 国内溢价，四个维度同步对照，不再只看一个孤立的数字。</p>
          <div class="hero-price-box">
            <span class="hero-price" id="ovSge">—</span>
            <span class="hero-unit" id="ovSgeUnit">元/克</span>
            <span class="hero-chg" id="heroChg">—</span>
          </div>
          <div class="hero-meta">
            <span>◷ <i id="ovSgeTime" style="font-style:normal">更新 —</i></span>
            <span>◈ 主力合约 {esc(sym)}</span>
            <span>↻ 每小时自动更新</span>
          </div>
        </div>
        <div class="hero-side">
          <div class="hs"><div class="k">◈ 国际现货黄金</div><div class="v num" id="hsXau">{fmt(intl.get('xau_usd'))}</div><div class="t">XAU/USD · 美元/盎司</div></div>
          <div class="hs"><div class="k">⇄ 美元兑人民币</div><div class="v num" id="hsFx">{fmt(intl.get('usd_cny'), 4)}</div><div class="t">USD/CNY</div></div>
          <div class="hs"><div class="k">≋ 国际折算价</div><div class="v num" id="hsCny">{fmt(intl.get('intl_cny_per_g'))}</div><div class="t">元/克（含金衡盎司换算）</div></div>
          <div class="hs"><div class="k">◐ 国内溢价</div><div class="v num {prem_cls}" id="hsPrem">{prem_txt}</div><div class="t">SGE 较国际折算</div></div>
        </div>
      </div>
    </div>

    <div class="ov-grid">
      <div class="ov"><div class="k">主力今开 <span class="ic">◷</span></div>
        <div class="ov-val num" id="ovOpen">{ov_open}</div><div class="t">Au99.99 · 元/克</div></div>
      <div class="ov"><div class="k">日内最高 <span class="ic">▲</span></div>
        <div class="ov-val num" id="ovHigh">{ov_high}</div><div class="t">最近交易时段</div></div>
      <div class="ov"><div class="k">日内最低 <span class="ic">▼</span></div>
        <div class="ov-val num" id="ovLow">{ov_low}</div><div class="t">最近交易时段</div></div>
      <div class="ov"><div class="k">日内振幅 <span class="ic">≋</span></div>
        <div class="ov-val num" id="ovRange">{ov_range}</div><div class="t">(最高 − 最低) ÷ 今开</div></div>
    </div>
  </section>

  {ad_slot()}

  <!-- ============ 行情表 ============ -->
  <section class="section" id="quotes">
    <div class="section-head">
      <div><div class="lbl">MARKET QUOTES</div><h2>上海黄金交易所 · 实时行情</h2>
        <p>六大常用合约并列对照，涨跌幅以今开为基准计算。</p></div>
      <div class="side">涨 <span class="up">红</span> / 跌 <span class="down">绿</span> · 单位见每行</div>
    </div>
    <div class="card">
      <div class="card-head"><h3>合约行情</h3>
        <div class="chip-row"><span class="badge">◷ 每小时抓取</span><span class="chip">SGE 官方行情</span></div></div>
      <table>
        <thead><tr><th>品种</th><th>合约</th><th>最新价</th><th>涨跌幅</th><th>今开</th><th>最高</th><th>最低</th><th>日内走势</th><th>单位</th></tr></thead>
        <tbody id="tbody"></tbody>
      </table>
      <div class="tfoot">「今开 / 最高 / 最低」为当日（或最近交易时段）区间；「最新价」为最近一笔成交。非交易时段显示最近一次有效报价。日内走势为分时序列迷你图，仅示意节奏，不代表完整逐笔成交。</div>
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

  <!-- ============ 黄金百科 ============ -->
  <section class="section" id="learn">
    <div class="section-head">
      <div><div class="lbl">GOLD KNOWLEDGE</div><h2>黄金知识百科</h2>
        <p>从合约代码到溢价成因，用六篇短文把金价读懂。</p></div>
    </div>
    <div class="prose-grid">{article_html}</div>
    <div class="faq-list">{faq_html}</div>
  </section>

  <div class="note-strip">
    <div class="ni">◈</div>
    <div class="nt"><strong>数据透明，来源可查</strong>
      <span>所有指标的计算口径与数据源都在「关于本站」中公开说明；上游失败时自动回退到上一次有效数据，不会显示空白或错误数字。</span></div>
    <a class="btn ghost" href="./about.html">查看数据说明 →</a>
  </div>

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
        "关于本站 · 数据来源与指标算法 | 今日金价",
        "今日金价的数据来源、更新机制、国内溢价与国际折算价的计算口径，以及完整免责声明与常见问题。",
        SITE + "about.html")}
<body>
{topbar_html(data)}
{ticker_html(data)}
{nav_html('about')}
<div class="wrap">
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
</div>
{footer_html()}
<script src="./ads.js"></script>
</body>
</html>"""


# ---------------------------------------------------------------- 隐私页

def page_privacy(data):
    return f"""{head_html(
        "隐私政策 | 今日金价",
        "今日金价的隐私政策：说明本站如何使用 localStorage、浏览器通知、第三方广告 Cookie 以及你的选择权。",
        SITE + "privacy.html")}
<body>
{topbar_html(data)}
{ticker_html(data)}
{nav_html()}
<div class="wrap">
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
</div>
{footer_html()}
<script src="./ads.js"></script>
</body>
</html>"""


# ---------------------------------------------------------------- 入口

def main():
    data = load_data()
    os.makedirs(DOCS, exist_ok=True)

    pages = [
        (os.path.join(DOCS, "index.html"), page_index(data)),
        (os.path.join(DOCS, "about.html"), page_about(data)),
        (os.path.join(DOCS, "privacy.html"), page_privacy(data)),
    ]
    for path, content in pages:
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

    with open(os.path.join(DOCS, "site.css"), "w", encoding="utf-8") as f:
        f.write(CSS)

    # 前端 ./data.json 副本（60s 轮询用）
    with open(os.path.join(DOCS, "data.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print("[ok] 已生成 index.html / about.html / privacy.html / site.css / data.json "
          f"（{len(data.get('items', []))} 个合约）")


if __name__ == "__main__":
    main()
