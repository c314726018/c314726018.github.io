/* 贵金属行情站 —— 前端逻辑
 * - 渲染概览卡片 / 行情表 / 图表
 * - 价格提醒（localStorage + 浏览器通知），每 60s 拉取最新 data.json 评估
 * - 暗色模式 + 响应式（手机/平板/桌面）
 * 仅做行情展示，不构成投资建议。
 */
(function () {
  "use strict";

  var DATA = {};
  try {
    DATA = JSON.parse(document.getElementById("app-data").textContent || "{}");
  } catch (e) { DATA = {}; }

  var GRAMS_PER_OZ = 31.1034768;
  var charts = {};

  // ---------- 工具 ----------
  function fmt(v, d) {
    d = d == null ? 2 : d;
    if (v === null || v === undefined || v === "") return "—";
    var n = Number(v);
    if (isNaN(n)) return "—";
    return n.toLocaleString("zh-CN", { minimumFractionDigits: d, maximumFractionDigits: d });
  }
  function $(s, r) { return (r || document).querySelector(s); }
  function $all(s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); }
  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }
  function changeOf(it) {
    var o = Number(it.open), l = Number(it.last);
    if (!o || isNaN(o) || isNaN(l)) return null;
    return { d: l - o, pct: (l - o) / o * 100, cls: l > o ? "up" : l < o ? "down" : "flat" };
  }
  // 分时序列迷你走势图（内联 SVG，无依赖）
  function spark(series, cls) {
    var s = (series || []).filter(function (v) { return typeof v === "number" && isFinite(v); });
    if (s.length < 3) return '<span class="flat" style="font-size:11px">—</span>';
    var step = Math.max(1, Math.floor(s.length / 34));
    var pts = [];
    for (var i = 0; i < s.length; i += step) pts.push(s[i]);
    if (pts[pts.length - 1] !== s[s.length - 1]) pts.push(s[s.length - 1]);
    var lo = Math.min.apply(null, pts), hi = Math.max.apply(null, pts), span = hi - lo || 1;
    var w = 76, h = 26, pad = 2;
    var d = pts.map(function (v, i) {
      var x = pad + i * (w - pad * 2) / (pts.length - 1);
      var y = pad + (1 - (v - lo) / span) * (h - pad * 2);
      return (i ? "L" : "M") + x.toFixed(1) + " " + y.toFixed(1);
    }).join(" ");
    var color = cls === "up" ? "#d4380d" : cls === "down" ? "#129b63" : "#8895a8";
    return '<svg class="spark" viewBox="0 0 ' + w + ' ' + h + '" preserveAspectRatio="none" aria-hidden="true">' +
      '<path d="' + d + '" fill="none" stroke="' + color + '" stroke-width="1.6" ' +
      'stroke-linejoin="round" stroke-linecap="round" vector-effect="non-scaling-stroke"/></svg>';
  }

  function isDark() {
    return document.documentElement.classList.contains("dark");
  }
  function themeColors() {
    return isDark()
      ? { ink: "#e5e7eb", sub: "#9aa3af", grid: "rgba(255,255,255,.08)", gold: "#e0b341" }
      : { ink: "#1f2329", sub: "#6b7280", grid: "#eef0f3", gold: "#b8860b" };
  }

  // ---------- 概览卡片 ----------
  function renderOverview(d) {
    var it = (d.items || []).filter(function (x) { return x.symbol === "Au99.99"; })[0];
    var intl = d.intl || {};
    if (it) {
      $("#ovSge").textContent = fmt(it.last);
      $("#ovSgeUnit").textContent = it.unit || "元/克";
      $("#ovSgeTime").textContent = it.update ? "更新 " + it.update : "更新 —";
      // 概览卡：主力日内区间
      $("#ovOpen").textContent = fmt(it.open);
      $("#ovHigh").textContent = fmt(it.max);
      $("#ovLow").textContent = fmt(it.min);
      var amp = (Number(it.max) - Number(it.min)) / Number(it.open) * 100;
      $("#ovRange").textContent = isFinite(amp) ? fmt(amp) + "%" : "—";
      var ch = changeOf(it);
      var hc = $("#heroChg");
      if (hc && ch) {
        hc.className = "hero-chg " + ch.cls;
        var arrow = ch.d > 0 ? "▲ +" : ch.d < 0 ? "▼ " : "— ";
        hc.textContent = arrow + fmt(Math.abs(ch.d)) + "  (" +
          (ch.pct >= 0 ? "+" : "") + fmt(ch.pct) + "%)";
      } else if (hc) { hc.className = "hero-chg"; hc.textContent = "—"; }
    }
    // Hero 右侧：国际维度（每 60s 数据刷新时同步）
    if (intl.xau_usd != null) $("#hsXau").textContent = fmt(intl.xau_usd);
    var mets = intl.metals || {};
    if (mets.silver && mets.silver.intl_usd != null) $("#hsSilver").textContent = fmt(mets.silver.intl_usd);
    if (intl.usd_cny != null) $("#hsFx").textContent = fmt(intl.usd_cny, 4);
    if (intl.premium_pct != null) {
      var el = $("#hsPrem");
      el.textContent = (intl.premium_pct >= 0 ? "+" : "") + fmt(intl.premium_pct) + "%";
      el.className = "v num " + (intl.premium_pct >= 0 ? "up" : "down");
    }
    var gt = $("#genTime");
    if (gt) gt.textContent = "数据生成：" + (d.generated_at || "—");
  }

  // ---------- 全宽大行情表(分组,金投网式) ----------
  function chgPair(last, base) {
    var l = Number(last), b = Number(base);
    if (!isFinite(l) || !isFinite(b) || !b) return null;
    var dd = l - b, pct = dd / b * 100;
    return { d: dd, pct: pct, cls: dd > 0 ? "up" : dd < 0 ? "down" : "flat" };
  }
  function gRow(name, code, last, base, open_, high, low, unit) {
    var ch = chgPair(last, base);
    var chgCell = ch
      ? '<td class="num strong ' + ch.cls + '">' + (ch.d > 0 ? "+" : "") + fmt(ch.d) + "</td>" +
        '<td><span class="pill ' + ch.cls + '">' + (ch.d > 0 ? "▲ +" : ch.d < 0 ? "▼ " : "— ") + fmt(Math.abs(ch.pct)) + "%</span></td>"
      : '<td class="num">—</td><td><span class="pill flat">—</span></td>';
    return "<tr>" +
      '<td class="lbl">' + esc(name) + "</td>" +
      '<td class="sym">' + esc(code) + "</td>" +
      '<td class="num strong">' + fmt(last) + "</td>" + chgCell +
      '<td class="num">' + fmt(open_) + "</td>" +
      '<td class="num up">' + fmt(high) + "</td>" +
      '<td class="num down">' + fmt(low) + "</td>" +
      '<td class="unit">' + esc(unit) + "</td></tr>";
  }
  function renderTable(d) {
    var tb = $("#tbody");
    if (!tb) return;
    var h = "";
    h += '<tr class="grow"><td colspan="9">◆ 上海黄金交易所 SGE</td></tr>';
    (d.items || []).forEach(function (it) {
      h += gRow(it.label, it.symbol, it.last, it.open, it.open, it.max, it.min, it.unit);
    });
    var ex = d.extra || {};
    if ((ex.futures || []).length) {
      h += '<tr class="grow"><td colspan="9">◆ 国内期货主力 · 上期所 / 上期能源</td></tr>';
      ex.futures.forEach(function (x) {
        h += gRow(x.name, x.code, x.last, x.prev, x.open, x.high, x.low, x.unit);
      });
    }
    if ((ex.indices || []).length) {
      h += '<tr class="grow"><td colspan="9">◆ 全球股指</td></tr>';
      ex.indices.forEach(function (x) {
        h += gRow(x.name, x.code, x.last, x.prev, x.open, x.high, x.low, x.unit || "点");
      });
    }
    if ((ex.intl || []).length || ex.dxy) {
      h += '<tr class="grow"><td colspan="9">◆ 国际现货 · 能源 · 美元指数</td></tr>';
      (ex.intl || []).forEach(function (x) {
        h += gRow(x.name, x.code, x.last, x.prev, x.open, x.high, x.low, x.unit);
      });
      if (ex.dxy) {
        var D = ex.dxy;
        h += gRow(D.name, "USD Index", D.last, D.prev, D.open, D.high, D.low, D.unit || "点");
      }
    }
    tb.innerHTML = h;
  }

  // ---------- 实物金价参考 ----------
  var PHYS_BASE = null;
  function _numVal(sel, def) {
    var el = $(sel); if (!el) return def;
    var v = parseFloat(el.value); return isFinite(v) ? v : def;
  }
  function _setPhys(sel, v) {
    var el = $(sel); if (el) el.innerHTML = fmt(v) + '<span class="pu">元/克</span>';
  }
  function computePhysical() {
    if (PHYS_BASE == null) return;
    var baseEl = $("#physBase"); if (baseEl) baseEl.innerHTML = fmt(PHYS_BASE) + '<span class="pu">元/克</span>';
    var bar = _numVal("#asBar", 12), rec = _numVal("#asRec", 5),
        jew = _numVal("#asJew", 70), d3 = _numVal("#as3d", 120),
        acc = _numVal("#asAcc", 0.5);
    _setPhys("#physBar", PHYS_BASE + bar);
    _setPhys("#physRec", PHYS_BASE - rec);
    _setPhys("#physJew", PHYS_BASE + jew);
    _setPhys("#phys3d", PHYS_BASE + d3);
    _setPhys("#physAcc", PHYS_BASE * (1 + acc / 100));
    // 扩展类别(固定典型假设,格内注明口径):金币 / 回收
    _setPhys("#physCoin", PHYS_BASE + 30);   // 投资金币:基准+30 升水
    _setPhys("#physCoin2", PHYS_BASE + 80);  // 纪念金币:基准+80 收藏溢价
    _setPhys("#physJewRec", PHYS_BASE - 12); // 首饰回收:折价大于金条
    // 贵金属回收:Ag 元/千克;Pt/Pd 元/克,均按 97% 计价
    var mets = (DATA.intl || {}).metals || {};
    var ag = (mets.silver || {}).intl_cny || null;   // 元/千克
    var pt = (mets.platinum || {}).sge || (mets.platinum || {}).intl_cny;
    var pd = (mets.palladium || {}).sge || (mets.palladium || {}).intl_cny;
    var agEl = $("#physAgRec");
    if (agEl) agEl.innerHTML = (ag ? fmt(ag * 0.97) : "—") + '<span class="pu">元/千克</span>';
    var ptEl = $("#physPtRec");
    if (ptEl) ptEl.innerHTML = (pt ? fmt(pt * 0.97) : "—") + '<span class="pu">元/克</span>' +
      (pd ? ' <span class="pu" style="opacity:.7">钯 ' + fmt(pd * 0.97) + "</span>" : "");
  }
  function renderPhysical(d) {
    var it = (d.items || []).filter(function (x) { return x.symbol === "Au99.99"; })[0];
    PHYS_BASE = it ? Number(it.last) : null;
    computePhysical();
  }
  function bindPhysical() {
    ["#asBar", "#asRec", "#asJew", "#as3d", "#asAcc"].forEach(function (s) {
      var el = $(s); if (el) el.addEventListener("input", computePhysical);
    });
    var r = $("#asReset");
    if (r) r.addEventListener("click", function () {
      if ($("#asBar")) $("#asBar").value = 12;
      if ($("#asRec")) $("#asRec").value = 5;
      if ($("#asJew")) $("#asJew").value = 70;
      if ($("#as3d")) $("#as3d").value = 120;
      if ($("#asAcc")) $("#asAcc").value = 0.5;
      computePhysical();
    });
  }

  // ---------- 工具计算器 ----------
  function computeT2() {
    if (!$("#t2usd") || !$("#t2fx")) return;
    var u = parseFloat($("#t2usd").value), f = parseFloat($("#t2fx").value);
    var out = $("#t2out"), src = $("#t2src");
    if (!out) return;
    if (!isFinite(u) || !isFinite(f)) { out.textContent = "请输入金价与汇率"; if (src) src.textContent = ""; return; }
    var cnyg = u * f / GRAMS_PER_OZ;
    out.innerHTML = "人民币金价：<b>" + fmt(cnyg) + "</b> 元/克";
    if (src) src.textContent = u + " × " + f + " ÷ 31.1035 = " + fmt(cnyg) + " 元/克";
  }
  function computeT3() {
    if (!$("#t3g") || !$("#t3b") || !$("#t3s")) return;
    var g = parseFloat($("#t3g").value), b = parseFloat($("#t3b").value), s = parseFloat($("#t3s").value);
    var out = $("#t3out"); if (!out) return;
    if (!isFinite(g) || !isFinite(b) || !isFinite(s)) { out.textContent = "—"; return; }
    var buy = g * b, sell = g * s, diff = sell - buy, pct = buy ? diff / buy * 100 : 0;
    out.innerHTML = "买入总额 <b>" + fmt(buy) + "</b> 元 · 卖出总额 <b>" + fmt(sell) + "</b> 元<br>价差 " +
      fmt(diff) + " 元 (" + (pct >= 0 ? "+" : "") + fmt(pct) + "%)";
  }
  function computeT4() {
    if (!$("#t4g") || !$("#t4b") || !$("#t4n")) return;
    var g = parseFloat($("#t4g").value), b = parseFloat($("#t4b").value), n = parseFloat($("#t4n").value);
    var out = $("#t4out"); if (!out) return;
    if (!isFinite(g) || !isFinite(b) || !isFinite(n)) { out.textContent = "—"; return; }
    var now = g * n, cost = g * b, p = n - b, pct = b ? p / b * 100 : 0;
    out.innerHTML = "现总值 <b>" + fmt(now) + "</b> 元 · 成本 <b>" + fmt(cost) + "</b> 元<br>盈亏 " +
      fmt(p * g) + " 元 (" + (pct >= 0 ? "+" : "") + fmt(pct) + "%)";
  }
  function bindTools() {
    var g = $("#t1g"), o = $("#t1o");
    if (g && o) {
      g.addEventListener("input", function () { var v = parseFloat(g.value); o.value = isFinite(v) ? (v / GRAMS_PER_OZ).toFixed(6) : ""; });
      o.addEventListener("input", function () { var v = parseFloat(o.value); g.value = isFinite(v) ? (v * GRAMS_PER_OZ).toFixed(4) : ""; });
    }
    ["#t2usd", "#t2fx"].forEach(function (s) { var e = $(s); if (e) e.addEventListener("input", computeT2); });
    ["#t3g", "#t3b", "#t3s"].forEach(function (s) { var e = $(s); if (e) e.addEventListener("input", computeT3); });
    ["#t4g", "#t4b", "#t4n"].forEach(function (s) { var e = $(s); if (e) e.addEventListener("input", computeT4); });
    // 用实时数据预填空字段（不覆盖用户已输入的值；用原始数值避免千分位逗号破坏 parseFloat）
    var it = (DATA.items || []).filter(function (x) { return x.symbol === "Au99.99"; })[0];
    var xau = (DATA.intl || {}).xau_usd, fx = (DATA.intl || {}).usd_cny;
    if (it) {
      if ($("#t3b") && !$("#t3b").value) $("#t3b").value = it.last;
      if ($("#t4b") && !$("#t4b").value) $("#t4b").value = it.last;
      if ($("#t4n") && !$("#t4n").value) $("#t4n").value = it.last;
    }
    if (xau && $("#t2usd") && !$("#t2usd").value) $("#t2usd").value = xau;
    if (fx && $("#t2fx") && !$("#t2fx").value) $("#t2fx").value = fx;
    computeT2(); computeT3(); computeT4();
  }

  // ---------- 多品种溢价对照 ----------
  var METAL_DEFS = [["gold", "黄金", "Au99.99"], ["silver", "白银", "Ag99.99"],
                    ["platinum", "铂金", "Pt99.95"], ["palladium", "钯金", "Pd99.95"]];

  function renderMetals(d) {
    var tb = $("#metalsBody");
    if (!tb) return;
    var m = (d.intl || {}).metals || {};
    tb.innerHTML = METAL_DEFS.map(function (def) {
      var x = m[def[0]] || {};
      if (x.sge == null && x.premium_pct == null) return "";  // 境内无报价则隐藏该行
      var prem = x.premium_pct;
      var cls = prem == null ? "flat" : (prem >= 0 ? "up" : "down");
      var premTxt = prem == null ? "—" : (prem >= 0 ? "+" : "") + fmt(prem) + "%";
      var unit = esc(x.unit || "");
      return "<tr>" +
        '<td class="lbl" data-label="品种">' + def[1] + ' <span class="sym">' + def[2] + "</span></td>" +
        '<td class="num" data-label="境内报价">' + fmt(x.sge) + ' <span class="unit">' + unit + "</span></td>" +
        '<td class="num" data-label="国际折算">' + fmt(x.intl_cny) + ' <span class="unit">' + unit + "</span></td>" +
        '<td data-label="国内溢价"><span class="chg ' + cls + '">' + premTxt + "</span></td>" +
        '<td class="unit" data-label="口径">' + esc(x.intl_symbol || "") + " × USD/CNY</td>" +
        "</tr>";
    }).join("");
  }

  // ---------- 油价与汇率 ----------
  function renderEnergy(d) {
    var tb = $("#energyBody");
    if (!tb) return;
    var oil = d.oil || {};
    tb.innerHTML = ["brent", "wti", "sc"].map(function (key) {
      var x = oil[key] || {};
      if (x.last == null) return "";
      var prev = x.prev_close || x.prev_settle;
      var chgHtml = '<span class="pill flat">—</span>';
      if (prev) {
        var pct = (x.last - prev) / prev * 100;
        var cls = pct > 0 ? "up" : pct < 0 ? "down" : "flat";
        chgHtml = '<span class="pill ' + cls + '">' + (pct > 0 ? "▲ +" : pct < 0 ? "▼ " : "— ") +
          fmt(Math.abs(pct)) + "%</span>";
      }
      return "<tr>" +
        '<td class="lbl" data-label="品种">' + esc(x.name) + "</td>" +
        '<td class="sym" data-label="代码">' + esc(x.symbol) + "</td>" +
        '<td class="num strong" data-label="最新价">' + fmt(x.last) + "</td>" +
        '<td data-label="涨跌幅">' + chgHtml + "</td>" +
        '<td class="unit" data-label="单位">' + esc(x.unit || "") + "</td>" +
        '<td class="unit" data-label="日期">' + esc(x.date || "—") + "</td>" +
        "</tr>";
    }).join("");
  }

  function renderFx(d) {
    var tb = $("#fxBody");
    if (!tb) return;
    tb.innerHTML = (d.fx || []).map(function (r) {
      var unitNote = r.unit === 100 ? "100" : "1";
      return "<tr>" +
        '<td class="lbl" data-label="币种">' + esc(r.name) + "</td>" +
        '<td class="sym" data-label="代码">' + esc(r.code) + "</td>" +
        '<td class="num strong" data-label="兑人民币">' + unitNote + " " + esc(r.code) + " = " + fmt(r.cny, 4) + "</td>" +
        '<td class="num" data-label="人民币兑">1 CNY = ' + fmt(r.per_cny, 4) + "</td>" +
        "</tr>";
    }).join("");
  }

  // ---------- 图表 ----------
  function bucketCandles(series, k) {
    k = k || 12;
    var out = [];
    for (var i = 0; i < series.length; i += k) {
      var slice = series.slice(i, i + k);
      if (!slice.length) continue;
      out.push({
        x: i / k + 1,
        o: slice[0], h: Math.max.apply(null, slice),
        l: Math.min.apply(null, slice), c: slice[slice.length - 1]
      });
    }
    return out;
  }

  function destroyChart(id) { if (charts[id]) { charts[id].destroy(); charts[id] = null; } }

  function renderCharts(d) {
    if (typeof Chart === "undefined") return;
    var c = themeColors();
    var primary = d.primary || {};
    var series = primary.series || [];

    // 分时
    destroyChart("line");
    var lc = $("#lineChart");
    if (lc && series.length) {
      charts.line = new Chart(lc, {
        type: "line",
        data: { labels: (primary.time && primary.time.length ? primary.time : series.map(function (_, i) { return i + 1; })),
          datasets: [{ label: primary.symbol || "主力", data: series, borderColor: c.gold,
            backgroundColor: "rgba(184,134,11,.10)", borderWidth: 1.6, pointRadius: 0, tension: .25, fill: true }] },
        options: baseOpts(c, false)
      });
    }

    // K线
    destroyChart("k");
    var kc = $("#kChart");
    if (kc && series.length >= 4) {
      try {
        var candles = bucketCandles(series, Math.max(2, Math.ceil(series.length / 24)));
        charts.k = new Chart(kc, {
          type: "candlestick",
          data: { datasets: [{ label: primary.symbol || "主力", data: candles,
            color: { up: "#d4380d", down: "#389e0d", unchanged: "#999" } }] },
          options: baseOpts(c, true)
        });
      } catch (e) {
        // 插件缺失时降级为折线
        charts.k = new Chart(kc, {
          type: "line",
          data: { labels: series.map(function (_, i) { return i + 1; }),
            datasets: [{ label: primary.symbol || "主力", data: series, borderColor: c.gold, borderWidth: 1.6, pointRadius: 0 }] },
          options: baseOpts(c, false)
        });
      }
    }

    // 多品种对比（归一化）
    destroyChart("cmp");
    var cc = $("#cmpChart");
    if (cc) {
      var cmpSyms = ["Au99.99", "Ag99.99", "Pt99.95"];
      var ds = cmpSyms.map(function (sym, idx) {
        var item = (d.items || []).filter(function (x) { return x.symbol === sym; })[0];
        var s = item ? item.series : [];
        var base = s[0];
        var norm = base ? s.map(function (v) { return (v / base - 1) * 100; }) : [];
        var colors = ["#b8860b", "#2f6fed", "#7c3aed"];
        return { label: sym, data: norm, borderColor: colors[idx], borderWidth: 1.6, pointRadius: 0, tension: .2 };
      }).filter(function (x) { return x.data.length; });
      if (ds.length) {
        charts.cmp = new Chart(cc, {
          type: "line",
          data: { labels: ds[0].data.map(function (_, i) { return i + 1; }), datasets: ds },
          options: cmpOpts(c)
        });
      }
    }
  }

  function baseOpts(c, xcat) {
    return {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false }, tooltip: { mode: "index" } },
      scales: {
        x: { type: xcat ? "category" : "category", ticks: { maxTicksLimit: 8, color: c.sub, font: { size: 10 } }, grid: { display: false } },
        y: { ticks: { color: c.sub, font: { size: 10 } }, grid: { color: c.grid } }
      }
    };
  }
  function cmpOpts(c) {
    return {
      responsive: true, maintainAspectRatio: false,
      interaction: { mode: "index", intersect: false },
      plugins: { legend: { display: true, labels: { color: c.ink, font: { size: 11 } } } },
      scales: {
        x: { ticks: { maxTicksLimit: 8, color: c.sub, font: { size: 10 } }, grid: { display: false } },
        y: { ticks: { color: c.sub, font: { size: 10 }, callback: function (v) { return v + "%"; } }, grid: { color: c.grid } }
      }
    };
  }

  // ---------- 价格提醒 ----------
  var ALERT_KEY = "gold_alerts_v1";
  var notified = {}; // 本次页面会话内同一规则只提醒一次，避免每 60s 反复弹窗

  function getAlerts() {
    try { return JSON.parse(localStorage.getItem(ALERT_KEY) || "[]"); } catch (e) { return []; }
  }
  function saveAlerts(a) { localStorage.setItem(ALERT_KEY, JSON.stringify(a)); }

  function renderAlerts() {
    var box = $("#alertList");
    if (!box) return;
    var list = getAlerts();
    if (!list.length) {
      box.innerHTML = '<li class="alert-empty">还没有提醒。在上方设置「价格 高于/低于 某值」时通知我。</li>';
    } else {
      box.innerHTML = list.map(function (a, i) {
        return '<li><span class="a-sym">' + a.sym + '</span> ' +
          '<span class="a-cond">' + (a.dir === "above" ? "≥" : "≤") + "</span> " +
          '<span class="a-val">' + fmt(a.target) + "</span>" +
          '<button class="a-del" data-i="' + i + '" aria-label="删除">✕</button></li>';
      }).join("");
    }
    $all(".a-del").forEach(function (b) {
      b.addEventListener("click", function () {
        var i = +b.getAttribute("data-i");
        var l = getAlerts(); l.splice(i, 1); saveAlerts(l); renderAlerts();
      });
    });
  }

  function addAlert() {
    var sym = $("#alertSym").value;
    var dir = $("#alertDir").value;
    var target = parseFloat($("#alertVal").value);
    if (!sym || isNaN(target)) { alert("请填写有效的合约与目标价格"); return; }
    var l = getAlerts();
    l.push({ sym: sym, dir: dir, target: target });
    saveAlerts(l); renderAlerts();
    $("#alertVal").value = "";
  }

  function checkAlerts(d) {
    var l = getAlerts();
    if (!l.length) return;
    var bySym = {};
    (d.items || []).forEach(function (it) { bySym[it.symbol] = it.last; });
    l.forEach(function (a) {
      var cur = bySym[a.sym];
      if (cur == null) return;
      var key = a.sym + "|" + a.dir + "|" + a.target;
      var hit = (a.dir === "above" && cur >= a.target) || (a.dir === "below" && cur <= a.target);
      if (!hit) { delete notified[key]; return; }  // 价格回到区间内后可再次提醒
      if (notified[key]) return;
      notified[key] = true;
      var msg = a.sym + " 已" + (a.dir === "above" ? "涨破" : "跌破") + " " + fmt(a.target) + "（当前 " + fmt(cur) + "）";
      if (window.Notification && Notification.permission === "granted") {
        try { new Notification("金价提醒", { body: msg }); } catch (e) { /* 忽略 */ }
      } else if (document.visibilityState === "visible") {
        // 未授权桌面通知时只在页面可见时提示，避免后台反复 alert
        window.alert("金价提醒：" + msg);
      }
    });
  }

  function bindAlerts() {
    var add = $("#alertAdd"); if (add) add.addEventListener("click", addAlert);
    renderAlerts();
    var nb = $("#notifyBtn");
    if (nb) nb.addEventListener("click", function () {
      if (!("Notification" in window)) { alert("当前浏览器不支持桌面通知"); return; }
      Notification.requestPermission().then(function (p) {
        nb.textContent = p === "granted" ? "通知已开启 ✓" : "通知未授权";
      });
    });
  }

  // ---------- 三大报价模块（金投网式,tab 切换品种 + 分时/日K 大图） ----------
  var QM_TAB = [0, 0, 0];
  var QM_MODE = [0, 0, 0]; // 0=分时/走势  1=日K
  var qCharts = {};
  function _set(id, txt) { var el = $("#" + id); if (el) el.textContent = txt; }
  function _pick(items, sym) {
    return (items || []).filter(function (x) { return x.symbol === sym; })[0];
  }
  function _chgHtml(ch) {
    if (!ch) return '<span class="flat">—</span>';
    var arrow = ch.d > 0 ? "▲" : ch.d < 0 ? "▼" : "—";
    return '<span class="' + ch.cls + '">' + arrow + " " + fmt(Math.abs(ch.d)) +
      "  (" + (ch.pct >= 0 ? "+" : "") + fmt(ch.pct) + "%)</span>";
  }
  function qChartOpts(c) {
    return { responsive: true, maintainAspectRatio: false,
      animation: { duration: 220 },
      plugins: { legend: { display: false }, tooltip: { intersect: false, mode: "index" } },
      scales: {
        x: { ticks: { maxTicksLimit: 6, color: c.sub, font: { size: 9 }, maxRotation: 0 }, grid: { display: false } },
        y: { position: "right", ticks: { maxTicksLimit: 4, color: c.sub, font: { size: 9 } }, grid: { color: c.grid } }
      } };
  }
  function drawQChart(id, labels, data, cls) {
    var cv = $("#" + id); if (!cv || !data || data.length < 3) return false;
    if (typeof Chart === "undefined") return false;
    var c = themeColors();
    var line = cls === "up" ? "#d4380d" : cls === "down" ? "#129b63" : c.gold;
    if (qCharts[id]) { qCharts[id].destroy(); qCharts[id] = null; }
    qCharts[id] = new Chart(cv, {
      type: "line",
      data: { labels: labels, datasets: [{ data: data, borderColor: line, borderWidth: 1.6,
        pointRadius: 0, tension: .25, fill: true,
        backgroundColor: cls === "up" ? "rgba(212,56,13,.08)" : cls === "down" ? "rgba(18,155,99,.08)" : "rgba(184,134,11,.10)" }] },
      options: qChartOpts(c) });
    return true;
  }
  // 日K（candlestick,真实 OHLC;插件缺失降级收盘折线）
  function drawQK(id, kl, cls) {
    var cv = $("#" + id); if (!cv || !kl || kl.length < 3) return false;
    if (typeof Chart === "undefined") return false;
    if (qCharts[id]) { qCharts[id].destroy(); qCharts[id] = null; }
    var labels = kl.map(function (x) { return (x.d || "").slice(5); });
    try {
      qCharts[id] = new Chart(cv, {
        type: "candlestick",
        data: { labels: labels, datasets: [{ data: kl.map(function (x, i) {
          return { x: i + 1, o: x.o, h: x.h, l: x.l, c: x.c }; }),
          color: { up: "#d4380d", down: "#129b63", unchanged: "#999" } }] },
        options: { responsive: true, maintainAspectRatio: false, animation: { duration: 200 },
          plugins: { legend: { display: false }, tooltip: { intersect: false, mode: "index",
            callbacks: { label: function (ctx) {
              var v = (ctx.raw && ctx.raw.o != null) ? ctx.raw : null;
              return v ? ["开 " + fmt(v.o), "高 " + fmt(v.h), "低 " + fmt(v.l), "收 " + fmt(v.c)] : ""; } } } },
          scales: { x: { ticks: { maxTicksLimit: 6, color: c.sub, font: { size: 9 }, maxRotation: 0 }, grid: { display: false } },
            y: { position: "right", ticks: { maxTicksLimit: 4, color: c.sub, font: { size: 9 } }, grid: { color: c.grid } } } }
      });
      return true;
    } catch (e) {
      return drawQChart(id, labels, kl.map(function (x) { return x.c; }), cls);
    }
  }
  function renderQM(d) {
    var KL = (d.klines || {});
    // 模块1 贵金属:分时=SGE 序列;日K=沪金主力 AU0(白银 tab 用沪银 AG0,国际板金 tab 用伦敦金 XAU)
    var defs1 = [
      { n: "现货黄金 Au99.99", u: "元/克", it: _pick(d.items, "Au99.99"), kl: KL.AU0, src: "沪金主力 AU0" },
      { n: "黄金延期 Au(T+D)", u: "元/克", it: _pick(d.items, "Au(T+D)"), kl: KL.AU0, src: "沪金主力 AU0" },
      { n: "国际板金 iAu99.99", u: "元/克", it: _pick(d.items, "iAu99.99"), kl: KL.XAU, src: "伦敦金 XAU·美元/盎司" },
      { n: "现货白银 Ag99.99", u: "元/千克", it: _pick(d.items, "Ag99.99"), kl: KL.AG0, src: "沪银主力 AG0" }
    ];
    var x = defs1[QM_TAB[0]] || defs1[0];
    _set("qm1Name", x.n); _set("qm1Unit", x.u);
    _set("qm1Price", fmt(x.it ? x.it.last : x.v));
    var ch1 = $("#qm1Chg"), sp1 = $("#qm1Spark");
    var ok1 = false, cls1 = "flat";
    if (x.it) {
      var ch = changeOf(x.it);
      cls1 = ch ? ch.cls : "flat";
      if (ch1) ch1.innerHTML = _chgHtml(ch);
    }
    if (QM_MODE[0] === 1) {
      ok1 = drawQK("qm1Chart", x.kl, cls1);
      if (ok1 && x.it) _set("qm1Name", x.n + "  ·  日K·" + x.src);
    } else if (x.it) {
      ok1 = drawQChart("qm1Chart", null, x.it.series, cls1);
    }
    if (sp1) {
      var showSpark = !ok1 && x.it;
      sp1.style.display = showSpark ? "" : "none";
      if (showSpark) sp1.innerHTML = spark(x.it.series, cls1);
    }
    // 模块2 外汇牌价(无K线源,图区显示美元指数块)
    var defs2 = [["USD", "美元兑人民币 USD/CNY"], ["EUR", "欧元兑人民币 EUR/CNY"],
                 ["JPY", "日元兑人民币 JPY/CNY(100)"], ["HKD", "港币兑人民币 HKD/CNY"],
                 ["GBP", "英镑兑人民币 GBP/CNY"]];
    var def2 = defs2[QM_TAB[1]] || defs2[0];
    var fx = (d.fx || []).filter(function (r) { return r.code === def2[0]; })[0];
    _set("qm2Name", def2[1]);
    if (fx) {
      _set("qm2Price", fmt(fx.cny, 4));
      _set("qm2Unit", fx.unit === 100 ? "人民币/100外币" : "人民币");
      var ch2 = $("#qm2Chg");
      if (ch2) ch2.innerHTML = '<span class="flat">1 CNY = ' + fmt(fx.per_cny, 4) + " " + fx.code + "</span>";
    }
    var dxy = ((d.extra || {}).dxy) || null;
    var sp2 = $("#qm2Spark");
    if (sp2) {
      if (dxy) {
        var dch = chgPair(dxy.last, dxy.prev);
        var dcls = dch ? dch.cls : "flat";
        sp2.innerHTML = '<div class="tq-sub" style="text-align:left">美元指数&nbsp;&nbsp;<b style="font-size:16px">' +
          fmt(dxy.last) + '</b> <span class="' + dcls + '">' +
          (dch ? (dch.d > 0 ? "▲ +" : "▼ ") + fmt(dch.pct) + "%" : "—") +
          '</span><br><span style="opacity:.7">高 ' + fmt(dxy.high) + " · 低 " + fmt(dxy.low) + "</span></div>";
      } else {
        sp2.innerHTML = "";
      }
    }
    // 模块3 能源:走势=30日收盘线;日K=真实 OHLC(OIL/CL/SC0)
    var defs3 = [["brent", "布伦特原油 OIL", "OIL", "布伦特连续"], ["wti", "WTI原油 CL", "CL", "WTI连续"],
                 ["sc", "上海原油 SC", "SC0", "沪原油连续"]];
    var def3 = defs3[QM_TAB[2]] || defs3[0];
    var o = (d.oil || {})[def3[0]] || {};
    _set("qm3Name", o.name || def3[1]);
    _set("qm3Price", fmt(o.last));
    _set("qm3Unit", o.unit || "");
    var ch3 = $("#qm3Chg");
    var prev = o.prev_close || o.prev_settle;
    var ocls = "flat";
    if (prev && o.last != null) {
      var pct = (o.last - prev) / prev * 100;
      ocls = pct > 0 ? "up" : pct < 0 ? "down" : "flat";
      var arrow = pct > 0 ? "▲" : pct < 0 ? "▼" : "—";
      if (ch3) ch3.innerHTML = '<span class="' + ocls + '">' + arrow + " " + fmt(Math.abs(o.last - prev)) +
        "  (" + fmt(Math.abs(pct)) + "%)</span>";
    } else if (ch3) {
      ch3.innerHTML = '<span class="flat">—</span>';
    }
    var ok3 = false;
    if (QM_MODE[2] === 1) {
      ok3 = drawQK("qm3Chart", KL[def3[2]], ocls);
      if (ok3) _set("qm3Name", (o.name || def3[1]) + "  ·  日K·" + def3[3]);
    } else if (o.hist && o.hist.length > 3) {
      ok3 = drawQChart("qm3Chart", null, o.hist, ocls);
    }
    var sp3 = $("#qm3Spark");
    if (sp3) {
      sp3.style.display = ok3 ? "none" : "";
      sp3.innerHTML = (!ok3 && o.date) ? '<span class="tq-sub">交易日 ' + esc(o.date) + "</span>" : "";
    }
  }
  function bindQM() {
    [["qm1", 0], ["qm2", 1], ["qm3", 2]].forEach(function (p) {
      var box = $("#" + p[0]); if (!box) return;
      box.addEventListener("click", function (e) {
        var a = e.target.closest(".tq-tabs a"); if (!a) return;
        var mi = a.getAttribute("data-m");
        if (mi != null) {
          QM_MODE[p[1]] = +mi;
          box.querySelectorAll(".tq-mode a").forEach(function (t) {
            t.classList.toggle("on", +t.getAttribute("data-m") === +mi);
          });
        } else {
          var idx = +a.getAttribute("data-i");
          QM_TAB[p[1]] = idx;
          box.querySelectorAll(".tq-tabs a[data-i]").forEach(function (t) {
            t.classList.toggle("on", +t.getAttribute("data-i") === idx);
          });
        }
        renderQM(DATA);
      });
    });
  }
  // ---------- 主题 ----------
  function bindTheme() {
    // 主题初始化与按钮交互由 common.js 统一处理；这里只负责主题变化时重绘图表配色
    window.addEventListener("themechange", function () {
      if (typeof Chart !== "undefined") renderCharts(DATA);
    });
  }

  // ---------- 数据刷新 ----------
  function renderAll(d) {
    DATA = d;
    renderOverview(d);
    renderQM(d);
    renderTable(d);
    renderMetals(d);
    renderEnergy(d);
    renderFx(d);
    renderPhysical(d);
    renderCharts(d);
    checkAlerts(d);
  }

  function loadData() {
    fetch("./data.json", { cache: "no-store" })
      .then(function (r) { return r.json(); })
      .then(function (d) { renderAll(d); })
      .catch(function () { renderAll(DATA); });
  }

  // ---------- 启动 ----------
  document.addEventListener("DOMContentLoaded", function () {
    bindTheme();
    bindAlerts();
    bindPhysical();
    bindTools();
    bindQM();
    renderAll(DATA);
    loadData();                 // 拉取最新 baked 数据
    setInterval(loadData, 60000); // 每 60s 检查一次（新构建发布即更新）
  });
})();
