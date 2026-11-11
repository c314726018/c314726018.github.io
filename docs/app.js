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
      $("#ovSgeUnit").textContent = it.unit;
      $("#ovSgeTime").textContent = it.update ? "更新 " + it.update : "";
    }
    if (intl.xau_usd != null) $("#ovXau").textContent = fmt(intl.xau_usd);
    if (intl.usd_cny != null) $("#ovFx").textContent = fmt(intl.usd_cny, 4);
    if (intl.premium_pct != null) {
      var el = $("#ovPremium");
      el.textContent = (intl.premium_pct >= 0 ? "+" : "") + fmt(intl.premium_pct) + "%";
      el.className = "ov-val " + (intl.premium_pct >= 0 ? "up" : "down");
    }
    $("#genTime").textContent = "数据生成：" + (d.generated_at || "—");
  }

  // ---------- 行情表 ----------
  function renderTable(d) {
    var tb = $("#tbody");
    if (!tb) return;
    tb.innerHTML = (d.items || []).map(function (it) {
      return "<tr>" +
        '<td class="lbl" data-label="品种">' + it.label + "</td>" +
        '<td class="sym" data-label="合约">' + it.symbol + "</td>" +
        '<td class="num strong" data-label="最新价">' + fmt(it.last) + "</td>" +
        '<td class="num" data-label="今开">' + fmt(it.open) + "</td>" +
        '<td class="num up" data-label="最高">' + fmt(it.max) + "</td>" +
        '<td class="num down" data-label="最低">' + fmt(it.min) + "</td>" +
        '<td class="unit" data-label="单位">' + it.unit + "</td>" +
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
  var FORM_ENDPOINT = ""; // 在此填入 Formspree/自建表单地址可启用邮件订阅；留空则仅本地记录

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
    var fired = [];
    l.forEach(function (a) {
      var cur = bySym[a.sym];
      if (cur == null) return;
      if ((a.dir === "above" && cur >= a.target) || (a.dir === "below" && cur <= a.target)) {
        fired.push(a);
      }
    });
    if (fired.length) {
      fired.forEach(function (a) {
        var msg = a.sym + " 已" + (a.dir === "above" ? "涨破" : "跌破") + " " + fmt(a.target) + "（当前 " + fmt(bySym[a.sym]) + "）";
        if (window.Notification && Notification.permission === "granted") {
          new Notification("金价提醒", { body: msg });
        } else {
          alert("金价提醒：" + msg);
        }
      });
    }
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
    var form = $("#subForm");
    if (form) form.addEventListener("submit", function (e) {
      e.preventDefault();
      var email = $("#subEmail").value.trim();
      if (!email) return;
      if (FORM_ENDPOINT) {
        fetch(FORM_ENDPOINT, {
          method: "POST", headers: { "Content-Type": "application/json", Accept: "application/json" },
          body: JSON.stringify({ email: email, source: "gold-site" })
        }).then(function () { form.reset(); $("#subNote").textContent = "订阅成功，金价异动将邮件通知你。"; })
          .catch(function () { $("#subNote").textContent = "提交失败，请稍后再试。"; });
      } else {
        // 无后端：本地记录，提示可后续接入
        var subs = JSON.parse(localStorage.getItem("gold_subs") || "[]");
        subs.push(email); localStorage.setItem("gold_subs", JSON.stringify(subs));
        form.reset();
        $("#subNote").textContent = "已记录（演示模式）。接入 Formspree 等后可直接邮件推送。";
      }
    });
  }

  // ---------- 主题 ----------
  function bindTheme() {
    var t = localStorage.getItem("gold_theme");
    if (t === "dark" || (!t && window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches)) {
      document.documentElement.classList.add("dark");
    }
    var btn = $("#themeBtn");
    if (btn) btn.addEventListener("click", function () {
      var dark = document.documentElement.classList.toggle("dark");
      localStorage.setItem("gold_theme", dark ? "dark" : "light");
      renderCharts(DATA);
    });
  }

  // ---------- 数据刷新 ----------
  function renderAll(d) {
    DATA = d;
    renderOverview(d);
    renderTable(d);
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
    renderAll(DATA);
    loadData();                 // 拉取最新 baked 数据
    setInterval(loadData, 60000); // 每 60s 检查一次（新构建发布即更新）
  });
})();
