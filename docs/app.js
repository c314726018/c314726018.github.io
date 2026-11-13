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
    var star = '<span class="fav' + (isFav(code) ? " on" : "") + '" data-code="' + esc(code) + '" title="加入/移出自选">' + (isFav(code) ? "★" : "☆") + "</span>";
    return "<tr>" +
      '<td class="lbl">' + star + esc(name) + "</td>" +
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
    tb.onclick = function (e) {
      var f = e.target.closest(".fav"); if (!f) return;
      toggleFav(f.getAttribute("data-code"));
      renderTable(DATA);
    };
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
        '<td class="unit" data-label="计价单位">' + unitNote + " 外币</td>" +
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
          data: { labels: candles.map(function (_, i) { return "K" + (i + 1); }),
            datasets: [{ label: primary.symbol || "主力", data: candles.map(function (x, i) {
              return { x: i + 1, o: x.o, h: x.h, l: x.l, c: x.c }; }),
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
  function bindFuel() {
    var sel = $("#fuelProv");
    if (!sel) return;
    var nr = (DATA && DATA.oil_retail && DATA.oil_retail.national) || {};
    var pv = (DATA && DATA.oil_retail && DATA.oil_retail.provinces) || {};
    function render() {
      var p = sel.value || "全国平均";
      var row = pv[p] || {};
      [["92", "fp92", "fd92"], ["95", "fp95", "fd95"], ["98", "fp98", "fd98"], ["0", "fp0", "fd0"]].forEach(function (t) {
        var k = t[0], pe = $("#" + t[1]), de = $("#" + t[2]);
        var v = row[k];
        if (pe) pe.textContent = v ? fmt(v) + " 元/升" : "—";
        if (de && v && nr[k]) {
          var dd = v - nr[k];
          var cls = dd > 0.005 ? "up" : dd < -0.005 ? "down" : "flat";
          de.innerHTML = '<span class="' + cls + '">' + (dd > 0 ? "+" : "") + fmt(dd) + "</span>";
        } else if (de) de.textContent = "—";
      });
    }
    sel.addEventListener("change", render);
    render();
  }
  function bindAlerts() {
    var box = $("#alertSymBox");
    if (box) box.addEventListener("click", function (e) {
      var p = e.target.closest(".sp"); if (!p) return;
      p.classList.toggle("on");
    });
    var ms = $("#mailSubmit");
    if (ms) ms.addEventListener("click", function () {
      var addr = ($("#mailAddr") || {}).value || "";
      var dirEl = $("#alertDir"), valEl = $("#alertVal");
      var dir = dirEl ? dirEl.value : "above", val = valEl ? valEl.value : "";
      var note = $("#mailNote");
      var syms = box ? $all(".sp.on", box).map(function (x) { return x.getAttribute("data-v"); }) : [];
      if (!syms.length) { alert("请至少选择一个品种"); return; }
      if (addr.indexOf("@") < 0 || addr.indexOf(".") < 0) { alert("请填写有效的接收邮箱"); return; }
      if (!val) { alert("请先填写目标价格"); return; }
      var boxMail = DATA && DATA.alert_mail;
      if (!boxMail) {
        if (note) note.innerHTML = '邮件订阅通道即将开放。';
        return;
      }
      var dirTxt = dir === "above" ? "高于" : dir === "below" ? "低于" : "等于";
      var body = "订阅类型:邮件价格提醒(免费 1 年)\n品种(" + syms.length + "):" + syms.join("、") +
        "\n方向:" + dirTxt + "\n目标价:" + val +
        "\n接收邮箱:" + addr + "\n提交时间:" + new Date().toLocaleString();
      window.location.href = "mailto:" + boxMail + "?subject=" +
        encodeURIComponent("【金潮网】邮件提醒订阅 - " + syms.length + " 个品种 " + dirTxt + " " + val) +
        "&body=" + encodeURIComponent(body);
      if (note) note.innerHTML = '已唤起邮件客户端,请点击发送完成订阅;开通后触发时 30 分钟内自动送达。';
    });
  }

  // ---------- 三大报价模块（金投网式,tab 切换品种 + 分时/日K 大图） ----------
  var QM_TAB = [0, 0, 0];
  var QM_MODE = [0, 0, 0]; // 0=分时/走势 1=日K 2=周K 3=月K
  var qCharts = {};
  var MA_PRESETS = [[5, 10, 20], [10, 20, 60], [20, 30, 60]];
  var maPresetIdx = +(localStorage.getItem("jc_maPreset") || 0);
  var QMI = {};
  function QM_CFG(m) { if (!QMI[m]) QMI[m] = { ind: "ma", sub: "macd", period: "d" }; return QMI[m]; }
  function maPeriods() { return MA_PRESETS[maPresetIdx]; }
  var FAVS = [];
  try { FAVS = JSON.parse(localStorage.getItem("jc_favs") || "[]"); } catch (e) { FAVS = []; }
  function saveFavs() { localStorage.setItem("jc_favs", JSON.stringify(FAVS)); }
  function isFav(code) { return FAVS.indexOf(code) >= 0; }
  function toggleFav(code) {
    var i = FAVS.indexOf(code);
    if (i >= 0) FAVS.splice(i, 1); else FAVS.push(code);
    saveFavs();
  }
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
      animation: false,
      plugins: { legend: { display: false }, tooltip: { intersect: false, mode: "index" } },
      scales: {
        x: { ticks: { maxTicksLimit: 6, color: c.sub, font: { size: 9 }, maxRotation: 0 }, grid: { display: false } },
        y: { position: "right", ticks: { maxTicksLimit: 4, color: c.sub, font: { size: 9 } }, grid: { color: c.grid } }
      } };
  }
  function drawQChart(id, labels, data, cls, avg) {
    var cv = $("#" + id); if (!cv || !data || data.length < 3) return false;
    if (typeof Chart === "undefined") return false;
    var c = themeColors();
    var line = cls === "up" ? "#d4380d" : cls === "down" ? "#129b63" : c.gold;
    if (qCharts[id]) { qCharts[id].destroy(); qCharts[id] = null; }
    var datasets = [{ data: data, borderColor: line, borderWidth: 1.6,
      pointRadius: 0, tension: .25, fill: true,
      backgroundColor: cls === "up" ? "rgba(212,56,13,.08)" : cls === "down" ? "rgba(18,155,99,.08)" : "rgba(184,134,11,.10)" }];
    if (avg) {
      var s = 0, av = [];
      for (var i = 0; i < data.length; i++) { s += data[i]; av.push(+(s / (i + 1)).toFixed(2)); }
      datasets.push({ data: av, borderColor: c.gold, borderWidth: 1, pointRadius: 0, tension: .2, fill: false, label: "均价" });
    }
    try {
      qCharts[id] = new Chart(cv, {
        type: "line",
        data: { labels: labels, datasets: datasets },
        options: qChartOpts(c) });
      return true;
    } catch (e) { return false; }
  }
  // 日K（candlestick + MA5/10/20 均线;插件缺失降级收盘折线）
  function maArr(closes, n) {
    var out = [];
    for (var i = 0; i < closes.length; i++) {
      if (i < n - 1) { out.push(null); continue; }
      var s = 0;
      for (var j = i - n + 1; j <= i; j++) s += closes[j];
      out.push(+(s / n).toFixed(2));
    }
    return out;
  }
  function ema(arr, n) {
    var k = 2 / (n + 1), out = [], prev;
    for (var i = 0; i < arr.length; i++) {
      prev = i ? prev : arr[0];
      prev = arr[i] * k + prev * (1 - k);
      out.push(+prev.toFixed(4));
    }
    return out;
  }
  function bollArr(closes, n, k) {
    var mid = [], up = [], low = [];
    for (var i = 0; i < closes.length; i++) {
      if (i < n - 1) { mid.push(null); up.push(null); low.push(null); continue; }
      var s = 0;
      for (var j = i - n + 1; j <= i; j++) s += closes[j];
      var m = s / n, v = 0;
      for (var j2 = i - n + 1; j2 <= i; j2++) v += (closes[j2] - m) * (closes[j2] - m);
      var sd = Math.sqrt(v / n);
      mid.push(+m.toFixed(2)); up.push(+(m + k * sd).toFixed(2)); low.push(+(m - k * sd).toFixed(2));
    }
    return { mid: mid, up: up, low: low };
  }
  function drawQK(id, kl, cls, cfg) {
    cfg = cfg || { ind: "ma", period: "d" };
    var periods = maPeriods();
    var cv = $("#" + id); if (!cv || !kl || kl.length < 3) return false;
    if (typeof Chart === "undefined") return false;
    var c = themeColors();
    if (qCharts[id]) { qCharts[id].destroy(); qCharts[id] = null; }
    var labels = kl.map(function (x) { return (x.d || "").slice(5); });
    var closes = kl.map(function (x) { return x.c; });
    var maLine = function (data, color, label) {
      // {x,y} 对象格式:y=null 合法跳过,避免混合 candlestick 时 null.x 崩溃(3.x 解析器行为)
      return { type: "line", label: label, data: data.map(function (v, i) { return { x: i + 1, y: v }; }),
        borderColor: color, borderWidth: 1.2, pointRadius: 0, tension: .3 };
    };
    var datasets = [
      { label: "K线", data: kl.map(function (x, i) {
          return { x: i + 1, o: x.o, h: x.h, l: x.l, c: x.c }; }),
        color: { up: "#d4380d", down: "#129b63", unchanged: "#999" } }
    ];
    var indName = "";
    if (cfg.ind === "boll") {
      var b = bollArr(closes, 20, 2);
      datasets.push(maLine(b.mid, "#f5a623", "BOLL中轨(20,2)"));
      datasets.push(maLine(b.up, "#4a90e2", "BOLL上轨"));
      datasets.push(maLine(b.low, "#4a90e2", "BOLL下轨"));
      indName = "BOLL(20,2)";
    } else if (cfg.ind === "ma") {
      var names = ["MA" + periods[0], "MA" + periods[1], "MA" + periods[2]];
      var cols = ["#f5a623", "#4a90e2", "#b07de8"];
      for (var mi = 0; mi < 3; mi++)
        datasets.push(maLine(maArr(closes, periods[mi]), cols[mi], names[mi]));
      indName = names.join("/");
    }
    try {
      qCharts[id] = new Chart(cv, {
        type: "candlestick",
        data: { labels: labels, datasets: datasets },
        options: { responsive: true, maintainAspectRatio: false, animation: false,
          plugins: { legend: { display: true, position: "top", labels: {
              color: c.sub, font: { size: 10 }, boxWidth: 14, boxHeight: 8 } },
            tooltip: { intersect: false, mode: "index",
              callbacks: { label: function (ctx) {
                if (ctx.dataset.type === "line") return ctx.dataset.label + " " + fmt(ctx.parsed.y);
                var v = (ctx.raw && ctx.raw.o != null) ? ctx.raw : null;
                return v ? ["开 " + fmt(v.o), "高 " + fmt(v.h), "低 " + fmt(v.l), "收 " + fmt(v.c)] : ""; } } } },
          scales: { x: { type: "category", ticks: { maxTicksLimit: 6, color: c.sub, font: { size: 9 }, maxRotation: 0 }, grid: { display: false } },
            y: { position: "right", ticks: { maxTicksLimit: 4, color: c.sub, font: { size: 9 } }, grid: { color: c.grid } } } }
      });
      return true;
    } catch (e) {
      console.error("drawQK FAIL", id, e.message);
      return drawQChart(id, labels, closes, cls);
    }
  }
  function resample(kl, mode) {
    if (mode === "d" || !kl || kl.length < 3) return kl;
    var groups = {}, order = [];
    for (var i = 0; i < kl.length; i++) {
      var d = kl[i].d || "";
      var key;
      if (mode === "m") key = d.slice(0, 7);
      else {
        var dt = new Date(d);
        if (isNaN(dt)) key = d.slice(0, 7);
        else {
          var onejan = new Date(dt.getFullYear(), 0, 1);
          var wk = Math.ceil((((dt - onejan) / 86400000) + onejan.getDay() + 1) / 7);
          key = d.slice(0, 4) + "-W" + (wk < 10 ? "0" + wk : wk);
        }
      }
      if (!groups[key]) { groups[key] = { d: d, o: kl[i].o, h: kl[i].h, l: kl[i].l, c: kl[i].c, v: kl[i].v || 0 }; order.push(key); }
      else {
        var g = groups[key];
        g.h = Math.max(g.h, kl[i].h); g.l = Math.min(g.l, kl[i].l);
        g.c = kl[i].c; g.d = d; g.v = (g.v || 0) + (kl[i].v || 0);
      }
    }
    return order.map(function (k) { return groups[k]; });
  }
  function renderQM(d) {
    var KL = (d.klines || {});
    // 模块1 贵金属:分时=SGE 序列;日K=沪金主力 AU0(白银 AG0,国际板金 XAU,COMEX=GC/SI)
    var INTL = ((d.extra || {}).intl) || [];
    function pickIntl(code) {
      return INTL.filter(function (x) { return x.code === code; })[0] || null;
    }
    var defs1 = [
      { n: "现货黄金 Au99.99", u: "元/克", it: _pick(d.items, "Au99.99"), kl: KL.AU0, src: "沪金主力 AU0" },
      { n: "黄金延期 Au(T+D)", u: "元/克", it: _pick(d.items, "Au(T+D)"), kl: KL.AU0, src: "沪金主力 AU0" },
      { n: "国际板金 iAu99.99", u: "元/克", it: _pick(d.items, "iAu99.99"), kl: KL.XAU, src: "伦敦金 XAU·美元/盎司" },
      { n: "现货白银 Ag99.99", u: "元/千克", it: _pick(d.items, "Ag99.99"), kl: KL.AG0, src: "沪银主力 AG0" },
      { n: "COMEX黄金 GC", u: "美元/盎司", px: pickIntl("hf_GC"), kl: KL.GC, src: "COMEX GC", klOnly: true },
      { n: "COMEX白银 SI", u: "美元/盎司", px: pickIntl("hf_SI"), kl: KL.SI, src: "COMEX SI", klOnly: true }
    ];
    var x = defs1[QM_TAB[0]] || defs1[0];
    _set("qm1Name", x.n); _set("qm1Unit", x.u);
    var px = x.px || null;
    _set("qm1Price", fmt(x.it ? x.it.last : (px ? px.last : x.v)));
    var ch1 = $("#qm1Chg"), sp1 = $("#qm1Spark");
    var ok1 = false, cls1 = "flat";
    if (x.it) {
      var ch = changeOf(x.it);
      cls1 = ch ? ch.cls : "flat";
      if (ch1) ch1.innerHTML = _chgHtml(ch);
    } else if (px) {
      var pch = chgPair(px.last, px.prev);
      cls1 = pch ? pch.cls : "flat";
      if (ch1) ch1.innerHTML = _chgHtml(pch);
    }
    var cfg1 = QM_CFG(0);
    if (QM_MODE[0] >= 1 || x.klOnly) {
      var kl1 = resample(x.kl, QM_MODE[0] === 1 ? "d" : QM_MODE[0] === 2 ? "w" : "m");
      ok1 = drawQK("qm1Chart", kl1, cls1, cfg1);
      if (ok1) _set("qm1Name", x.n + "  ·  " + (QM_MODE[0] === 1 ? "日K·" : QM_MODE[0] === 2 ? "周K·" : "月K·") + x.src);
      drawSub("qm1Sub", cfg1.sub, x.kl, cfg1);
    } else if (x.it) {
      ok1 = drawQChart("qm1Chart", x.it.series.map(function (_, i) { return i + 1; }), x.it.series, cls1, true);
      hideSub("qm1SubBox");
    }
    syncTools("qm1Tools", cfg1, QM_MODE[0]);
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
    var dE = $("#qm2Dxy"), cE = $("#qm2DxyChg"), hE = $("#qm2DxyH"), lE = $("#qm2DxyL");
    if (dxy && dE) {
      _set("qm2Dxy", fmt(dxy.last));
      var dch = chgPair(dxy.last, dxy.prev);
      if (cE) {
        cE.className = "fxchg " + (dch ? dch.cls : "flat");
        cE.textContent = dch ? (dch.d > 0 ? "▲ +" : "▼ ") + fmt(dch.pct) + "%" : "—";
      }
      _set("qm2DxyH", fmt(dxy.high)); _set("qm2DxyL", fmt(dxy.low));
    }
    var inv = $("#qm2Inv");
    if (inv && fx) inv.textContent = fmt(fx.per_cny, 4);
    // 模块3 能源与商品:走势=收盘折线;日K=真实 OHLC+均线
    var FUT = ((d.extra || {}).futures) || [];
    function pickFut(code) {
      return FUT.filter(function (x) { return x.code === code; })[0] || null;
    }
    var defs3 = [
      { key: "brent", n: "布伦特原油 OIL", kl: "OIL", ksrc: "布伦特连续", oil: true },
      { key: "wti", n: "WTI原油 CL", kl: "CL", ksrc: "WTI连续", oil: true },
      { key: "sc", n: "上海原油 SC", kl: "SC0", ksrc: "沪原油连续", oil: true },
      { key: "cu", n: "沪铜主力 CU", kl: "CU0", ksrc: "沪铜连续", fut: "nf_CU0" },
      { key: "rb", n: "螺纹钢主力 RB", kl: "RB0", ksrc: "螺纹钢连续", fut: "nf_RB0" }
    ];
    var def3 = defs3[QM_TAB[2]] || defs3[0];
    var o = def3.oil ? ((d.oil || {})[def3.key] || {}) : (pickFut(def3.fut) || {});
    if (!o.name) o.name = def3.n;
    var prev = o.prev_close || o.prev || o.prev_settle;
    _set("qm3Name", o.name || def3.n);
    _set("qm3Price", fmt(o.last));
    _set("qm3Unit", o.unit || "");
    var ch3 = $("#qm3Chg");
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
    var kl3 = KL[def3.kl] || null;
    var ok3 = false;
    var cfg3 = QM_CFG(2);
    if (QM_MODE[2] >= 1) {
      var kl3r = resample(kl3, QM_MODE[2] === 1 ? "d" : QM_MODE[2] === 2 ? "w" : "m");
      ok3 = drawQK("qm3Chart", kl3r, ocls, cfg3);
      if (ok3) _set("qm3Name", (o.name || def3.n) + "  ·  " + (QM_MODE[2] === 1 ? "日K·" : QM_MODE[2] === 2 ? "周K·" : "月K·") + def3.ksrc);
      drawSub("qm3Sub", cfg3.sub, kl3, cfg3);
    } else if (kl3 && kl3.length > 3) {
      ok3 = drawQChart("qm3Chart", kl3.map(function (x) { return (x.d || "").slice(5); }), kl3.map(function (x) { return x.c; }), ocls);
      hideSub("qm3SubBox");
    }
    syncTools("qm3Tools", cfg3, QM_MODE[2]);
    var sp3 = $("#qm3Spark");
    if (sp3) {
      sp3.style.display = ok3 ? "none" : "";
      sp3.innerHTML = (!ok3 && o.date) ? '<span class="tq-sub">交易日 ' + esc(o.date) + "</span>" : "";
    }
  }
  function hideSub(id) { var b = $("#" + id); if (b) b.style.display = "none"; }
  function drawSub(boxId, type, kl, cfg) {
    var box = $("#" + boxId); if (!box) return;
    console.log("drawSub", boxId, "type=" + type, "kl=" + (kl ? kl.length : "null"));
    if (type === "none" || !kl || kl.length < 10 || typeof Chart === "undefined") { box.style.display = "none"; return; }
    box.style.display = "";
    var cid = boxId.replace("Box", "");
    var cv = $("#" + cid); if (!cv) return;
    var key = "sub_" + boxId;
    if (qCharts[key]) { qCharts[key].destroy(); qCharts[key] = null; }
    var c = themeColors();
    var closes = kl.map(function (x) { return x.c; });
    var labels = kl.map(function (x) { return (x.d || "").slice(5); });
    var ds = [];
    try {
      if (type === "macd") {
        var e12 = ema(closes, 12), e26 = ema(closes, 26);
        var dif = closes.map(function (_, i) { return +(e12[i] - e26[i]).toFixed(3); });
        var dea = ema(dif, 9);
        var hist = dif.map(function (v, i) { return +((v - dea[i]) * 2).toFixed(3); });
        var xy = function (arr) { return arr.map(function (v, i) { return { x: i + 1, y: v }; }); };
        ds = [
          { type: "bar", label: "MACD", data: xy(hist), backgroundColor: hist.map(function (v) { return v >= 0 ? "rgba(212,56,13,.6)" : "rgba(18,155,99,.6)"; }) },
          { type: "line", label: "DIF", data: xy(dif), borderColor: "#f5a623", borderWidth: 1, pointRadius: 0, tension: .3 },
          { type: "line", label: "DEA", data: xy(dea), borderColor: "#4a90e2", borderWidth: 1, pointRadius: 0, tension: .3 }
        ];
      } else {
        var n = 9, kv = [], hv = [], lv2 = [];
        for (var i = 0; i < closes.length; i++) {
          if (i < n - 1) { kv.push(null); hv.push(null); lv2.push(null); continue; }
          var hh = -Infinity, ll = Infinity;
          for (var j = i - n + 1; j <= i; j++) { hh = Math.max(hh, kl[j].h); ll = Math.min(ll, kl[j].l); }
          var rsv = hh === ll ? 50 : (closes[i] - ll) / (hh - ll) * 100;
          var K = kv[i - 1] == null ? 50 : kv[i - 1];
          var D = hv[i - 1] == null ? 50 : hv[i - 1];
          K = (2 * K + rsv) / 3; D = (2 * D + K) / 3;
          kv.push(+K.toFixed(2)); hv.push(+D.toFixed(2)); lv2.push(+(3 * K - 2 * D).toFixed(2));
        }
        var xy2 = function (arr) { return arr.map(function (v, i) { return { x: i + 1, y: v }; }); };
        ds = [
          { type: "line", label: "K", data: xy2(kv), borderColor: "#f5a623", borderWidth: 1, pointRadius: 0, tension: .3 },
          { type: "line", label: "D", data: xy2(hv), borderColor: "#4a90e2", borderWidth: 1, pointRadius: 0, tension: .3 },
          { type: "line", label: "J", data: xy2(lv2), borderColor: "#b07de8", borderWidth: 1, pointRadius: 0, tension: .3 }
        ];
      }
      qCharts[key] = new Chart(cv, {
        type: "line",
        data: { labels: labels, datasets: ds },
        options: { responsive: true, maintainAspectRatio: false, animation: false,
          plugins: { legend: { display: true, position: "top", labels: { color: c.sub, font: { size: 9 }, boxWidth: 10 } } },
          scales: { x: { display: false }, y: { position: "right", ticks: { maxTicksLimit: 3, color: c.sub, font: { size: 8 } }, grid: { color: c.grid } } } }
      });
    } catch (e) { console.error("drawSub FAIL", boxId, e.message); box.style.display = "none"; }
  }
  function syncTools(boxId, cfg, mode) {
    var box = $("#" + boxId); if (!box) return;
    box.querySelectorAll('.tt-g[data-g="ind"] a').forEach(function (a) {
      a.classList.toggle("on", a.getAttribute("data-ind") === cfg.ind);
    });
    box.querySelectorAll('.tt-g[data-g="sub"] a').forEach(function (a) {
      a.classList.toggle("on", a.getAttribute("data-sub") === cfg.sub);
    });
    box.querySelectorAll('.tt-g[data-g="period"] a').forEach(function (a) {
      a.classList.toggle("on", a.getAttribute("data-p") === (mode === 1 ? "d" : mode === 2 ? "w" : mode === 3 ? "m" : "d"));
    });
  }
  function openFS(modId, chartId, title) {
    var ov = $("#fsOverlay");
    if (!ov) {
      ov = document.createElement("div");
      ov.id = "fsOverlay";
      ov.innerHTML = '<div class="fs-h"><b></b><a>✕ 关闭 (Esc)</a></div><div class="fs-body"><canvas id="fsCanvas"></canvas></div>';
      document.body.appendChild(ov);
      ov.addEventListener("click", function (e) {
        if (e.target === ov || e.target.closest(".fs-h a")) closeFS();
      });
      document.addEventListener("keydown", function (e) { if (e.key === "Escape") closeFS(); });
    }
    ov.querySelector(".fs-h b").textContent = title;
    ov.classList.add("open");
    var inst = qCharts[chartId];
    if (!inst || typeof Chart === "undefined") return;
    var cfgFs = JSON.parse(JSON.stringify(inst.config));
    cfgFs.options = cfgFs.options || {};
    cfgFs.options.responsive = true; cfgFs.options.maintainAspectRatio = false;
    if (qCharts.fs) { qCharts.fs.destroy(); qCharts.fs = null; }
    qCharts.fs = new Chart($("#fsCanvas"), cfgFs);
  }
  function closeFS() {
    var ov = $("#fsOverlay");
    if (ov) { ov.classList.remove("open"); if (qCharts.fs) { qCharts.fs.destroy(); qCharts.fs = null; } }
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
      var tools = $("#" + p[0] + "Tools");
      if (tools) tools.addEventListener("click", function (e) {
        var a = e.target.closest("a"); if (!a) return;
        var cfg = QM_CFG(p[1]);
        var ind = a.getAttribute("data-ind");
        var sub = a.getAttribute("data-sub");
        var pd = a.getAttribute("data-p");
        if (ind) { cfg.ind = ind; }
        else if (sub) { cfg.sub = (cfg.sub === sub ? "none" : sub); }
        else if (pd) { QM_MODE[p[1]] = pd === "d" ? 1 : pd === "w" ? 2 : 3; }
        else if (a.getAttribute("data-act") === "fs") {
          var names = { qm1: "贵金属行情", qm3: "能源与商品行情" };
          openFS(p[0], p[1] === 0 ? "qm1Chart" : "qm3Chart", names[p[0]] || "行情图");
          return;
        }
        syncTools(p[0] + "Tools", cfg, QM_MODE[p[1]]);
        renderQM(DATA);
      });
    });
    ["qm1Tools", "qm3Tools"].forEach(function (tid) {
      var t = $("#" + tid); if (!t) return;
      t.addEventListener("dblclick", function (e) {
        if (!e.target.closest('.tt-g[data-g="ind"] a[data-ind="ma"]')) return;
        maPresetIdx = (maPresetIdx + 1) % MA_PRESETS.length;
        localStorage.setItem("jc_maPreset", maPresetIdx);
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
  function renderDeriv(d) {
    var intl = d.intl || {};
    var xau = intl.xau_usd, xag = (intl.metals || {}).silver || {}, xpt = (intl.metals || {}).platinum || {};
    var oil = ((d.oil || {}).brent || {}).last;
    var g1 = $("#drGoldSilver"), g2 = $("#drGoldOil"), g3 = $("#drGoldPlat");
    if (g1 && xau && xag.intl_usd) g1.textContent = fmt(xau / xag.intl_usd, 1);
    if (g2 && xau && oil) g2.textContent = fmt(xau / oil, 1);
    if (g3 && xau && xpt.intl_usd) g3.textContent = fmt(xau / xpt.intl_usd, 1);
  }
  function renderAll(d) {
    DATA = d;
    renderOverview(d);
    renderQM(d);
    renderDeriv(d);
    renderTable(d);
    renderMetals(d);
    renderEnergy(d);
    renderFx(d);
    renderPhysical(d);
    renderCharts(d);
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
    bindFuel();
    renderAll(DATA);
    loadData();                 // 拉取最新 baked 数据
    setInterval(loadData, 60000); // 每 60s 检查一次（新构建发布即更新）
  });
})();
