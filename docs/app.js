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

  // ---------- 行情表 ----------
  function renderTable(d) {
    var tb = $("#tbody");
    if (!tb) return;
    tb.innerHTML = (d.items || []).map(function (it) {
      var ch = changeOf(it);
      var chgCell = ch
        ? '<span class="chg ' + ch.cls + '">' + (ch.d > 0 ? "▲ +" : ch.d < 0 ? "▼ " : "— ") +
          fmt(Math.abs(ch.d)) + " (" + (ch.pct >= 0 ? "+" : "") + fmt(ch.pct) + "%)</span>"
        : '<span class="flat">—</span>';
      var amp = (Number(it.max) - Number(it.min)) / Number(it.open) * 100;
      var ampTxt = isFinite(amp) ? fmt(amp) + "%" : "—";
      var dCell = ch
        ? '<span class="num strong ' + ch.cls + '">' + (ch.d > 0 ? "+" : "") + fmt(ch.d) + "</span>"
        : '<span class="flat">—</span>';
      return "<tr>" +
        '<td class="lbl" data-label="品种">' + esc(it.label) + "</td>" +
        '<td class="sym" data-label="合约">' + esc(it.symbol) + "</td>" +
        '<td class="num strong" data-label="最新价">' + fmt(it.last) + "</td>" +
        '<td data-label="涨跌幅">' + chgCell + "</td>" +
        '<td data-label="涨跌额">' + dCell + "</td>" +
        '<td class="num" data-label="今开">' + fmt(it.open) + "</td>" +
        '<td class="num up" data-label="最高">' + fmt(it.max) + "</td>" +
        '<td class="num down" data-label="最低">' + fmt(it.min) + "</td>" +
        '<td class="num" data-label="振幅">' + ampTxt + "</td>" +
        '<td data-label="日内走势">' + spark(it.series, ch ? ch.cls : "flat") + "</td>" +
        '<td class="unit" data-label="单位">' + esc(it.unit) + "</td>" +
        "</tr>";
    }).join("");
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
      var chgHtml = '<span class="flat">—</span>';
      if (prev) {
        var pct = (x.last - prev) / prev * 100;
        var cls = pct > 0 ? "up" : pct < 0 ? "down" : "flat";
        chgHtml = '<span class="chg ' + cls + '">' + (pct > 0 ? "▲" : pct < 0 ? "▼" : "—") +
          " " + fmt(Math.abs(pct)) + "%</span>";
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
    renderAll(DATA);
    loadData();                 // 拉取最新 baked 数据
    setInterval(loadData, 60000); // 每 60s 检查一次（新构建发布即更新）
  });
})();
