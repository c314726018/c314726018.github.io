#!/usr/bin/env python3
# 任务22(app.js 部分,修正锚点版)
import os
B = "/Users/cuisiqi/WorkBuddy/2026-11-10-16-34-12/gold-site/"
p = B + "docs/app.js"
js = open(p).read()

# 1) 状态与 MA 预设、自选
old = "  var QM_TAB = [0, 0, 0];\n  var QM_MODE = [0, 0, 0]; // 0=分时/走势  1=日K\n  var qCharts = {};"
new = '''  var QM_TAB = [0, 0, 0];
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
  }'''
assert js.count(old) == 1, "step1"
js = js.replace(old, new, 1)

# 2) ema/boll + drawQK 签名
old = "  function drawQK(id, kl, cls) {"
new = '''  function ema(arr, n) {
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
    var periods = maPeriods();'''
assert js.count(old) == 1, "step2"
js = js.replace(old, new, 1)

# 3) drawQK datasets 动态指标
old = '''    var closes = kl.map(function (x) { return x.c; });
    var maLine = function (data, color, label) {
      return { type: "line", label: label, data: data, borderColor: color,
        borderWidth: 1.2, pointRadius: 0, tension: .3 };
    };
    try {
      qCharts[id] = new Chart(cv, {
        type: "candlestick",
        data: { labels: labels, datasets: [
          { label: "K线", data: kl.map(function (x, i) {
              return { x: i + 1, o: x.o, h: x.h, l: x.l, c: x.c }; }),
            color: { up: "#d4380d", down: "#129b63", unchanged: "#999" } },
          maLine(maArr(closes, 5), "#f5a623", "MA5"),
          maLine(maArr(closes, 10), "#4a90e2", "MA10"),
          maLine(maArr(closes, 20), "#b07de8", "MA20")
        ] },'''
new = '''    var closes = kl.map(function (x) { return x.c; });
    var maLine = function (data, color, label) {
      return { type: "line", label: label, data: data, borderColor: color,
        borderWidth: 1.2, pointRadius: 0, tension: .3 };
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
        data: { labels: labels, datasets: datasets },'''
assert js.count(old) == 1, "step3"
js = js.replace(old, new, 1)

# 4) 周期重采样
old = "  function renderQM(d) {"
new = '''  function resample(kl, mode) {
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
  function renderQM(d) {'''
assert js.count(old) == 1, "step4"
js = js.replace(old, new, 1)

# 5) 模块1 分支(精确锚点)
old = '''    if (QM_MODE[0] === 1 || x.klOnly) {
      ok1 = drawQK("qm1Chart", x.kl, cls1);
      if (ok1) _set("qm1Name", x.n + "  ·  日K·" + x.src);
    } else if (x.it) {
      ok1 = drawQChart("qm1Chart", null, x.it.series, cls1);
    }'''
new = '''    var cfg1 = QM_CFG(0);
    if (QM_MODE[0] >= 1 || x.klOnly) {
      var kl1 = resample(x.kl, QM_MODE[0] === 1 ? "d" : QM_MODE[0] === 2 ? "w" : "m");
      ok1 = drawQK("qm1Chart", kl1, cls1, cfg1);
      if (ok1) _set("qm1Name", x.n + "  ·  " + (QM_MODE[0] === 1 ? "日K·" : QM_MODE[0] === 2 ? "周K·" : "月K·") + x.src);
      drawSub("qm1Sub", cfg1.sub, x.kl, cfg1);
    } else if (x.it) {
      ok1 = drawQChart("qm1Chart", null, x.it.series, cls1, true);
      hideSub("qm1SubBox");
    }
    syncTools("qm1Tools", cfg1, QM_MODE[0]);'''
assert js.count(old) == 1, "step5"
js = js.replace(old, new, 1)

# 6) drawQChart 加均价参数
old = '''  function drawQChart(id, labels, data, cls) {
    var cv = $("#" + id); if (!cv || !data || data.length < 3) return false;
    if (typeof Chart === "undefined") return false;
    var c = themeColors();
    var line = cls === "up" ? "#d4380d" : cls === "down" ? "#129b63" : c.gold;
    if (qCharts[id]) { qCharts[id].destroy(); qCharts[id] = null; }
    try {
      qCharts[id] = new Chart(cv, {
        type: "line",
        data: { labels: labels, datasets: [{ data: data, borderColor: line, borderWidth: 1.6,
          pointRadius: 0, tension: .25, fill: true,
          backgroundColor: cls === "up" ? "rgba(212,56,13,.08)" : cls === "down" ? "rgba(18,155,99,.08)" : "rgba(184,134,11,.10)" }] },
        options: qChartOpts(c) });
      return true;
    } catch (e) { return false; }
  }'''
new = '''  function drawQChart(id, labels, data, cls, avg) {
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
  }'''
assert js.count(old) == 1, "step6"
js = js.replace(old, new, 1)

# 7) 副图/工具同步/全屏 函数(插在 bindQM 前)
old = "  function bindQM() {"
new = '''  function hideSub(id) { var b = $("#" + id); if (b) b.style.display = "none"; }
  function drawSub(boxId, type, kl, cfg) {
    var box = $("#" + boxId); if (!box) return;
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
        ds = [
          { type: "bar", label: "MACD", data: hist, backgroundColor: hist.map(function (v) { return v >= 0 ? "rgba(212,56,13,.6)" : "rgba(18,155,99,.6)"; }) },
          { type: "line", label: "DIF", data: dif, borderColor: "#f5a623", borderWidth: 1, pointRadius: 0, tension: .3 },
          { type: "line", label: "DEA", data: dea, borderColor: "#4a90e2", borderWidth: 1, pointRadius: 0, tension: .3 }
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
        ds = [
          { type: "line", label: "K", data: kv, borderColor: "#f5a623", borderWidth: 1, pointRadius: 0, tension: .3 },
          { type: "line", label: "D", data: hv, borderColor: "#4a90e2", borderWidth: 1, pointRadius: 0, tension: .3 },
          { type: "line", label: "J", data: lv2, borderColor: "#b07de8", borderWidth: 1, pointRadius: 0, tension: .3 }
        ];
      }
      qCharts[key] = new Chart(cv, {
        type: "line",
        data: { labels: labels, datasets: ds },
        options: { responsive: true, maintainAspectRatio: false, animation: false,
          plugins: { legend: { display: true, position: "top", labels: { color: c.sub, font: { size: 9 }, boxWidth: 10 } } },
          scales: { x: { display: false }, y: { position: "right", ticks: { maxTicksLimit: 3, color: c.sub, font: { size: 8 } }, grid: { color: c.grid } } } }
      });
    } catch (e) { box.style.display = "none"; }
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
  function bindQM() {'''
assert js.count(old) == 1, "step7"
js = js.replace(old, new, 1)

# 8) bindQM 工具行事件
old = '''        renderQM(DATA);
      });
    });
  }'''
new = '''        renderQM(DATA);
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
  }'''
assert js.count(old) == 1, "step8"
js = js.replace(old, new, 1)

# 9) 模块3 分支
old = '''    var kl3 = KL[def3.kl] || null;
    var ok3 = false;
    if (QM_MODE[2] === 1) {
      ok3 = drawQK("qm3Chart", kl3, ocls);
      if (ok3) _set("qm3Name", (o.name || def3.n) + "  ·  日K·" + def3.ksrc);
    } else if (kl3 && kl3.length > 3) {
      ok3 = drawQChart("qm3Chart", null, kl3.map(function (x) { return x.c; }), ocls);
    }'''
new = '''    var kl3 = KL[def3.kl] || null;
    var ok3 = false;
    var cfg3 = QM_CFG(2);
    if (QM_MODE[2] >= 1) {
      var kl3r = resample(kl3, QM_MODE[2] === 1 ? "d" : QM_MODE[2] === 2 ? "w" : "m");
      ok3 = drawQK("qm3Chart", kl3r, ocls, cfg3);
      if (ok3) _set("qm3Name", (o.name || def3.n) + "  ·  " + (QM_MODE[2] === 1 ? "日K·" : QM_MODE[2] === 2 ? "周K·" : "月K·") + def3.ksrc);
      drawSub("qm3Sub", cfg3.sub, kl3, cfg3);
    } else if (kl3 && kl3.length > 3) {
      ok3 = drawQChart("qm3Chart", null, kl3.map(function (x) { return x.c; }), ocls);
      hideSub("qm3SubBox");
    }
    syncTools("qm3Tools", cfg3, QM_MODE[2]);'''
assert js.count(old) == 1, "step9"
js = js.replace(old, new, 1)

# 10) 自选星标 + 委托
old = '''    return "<tr>" +
      '<td class="lbl">' + esc(name) + "</td>" +'''
new = '''    var star = '<span class="fav' + (isFav(code) ? " on" : "") + '" data-code="' + esc(code) + '" title="加入/移出自选">' + (isFav(code) ? "★" : "☆") + "</span>";
    return "<tr>" +
      '<td class="lbl">' + star + esc(name) + "</td>" +'''
assert js.count(old) == 1, "step10"
js = js.replace(old, new, 1)

old = '''    tb.innerHTML = h;
  }'''
new = '''    tb.innerHTML = h;
    tb.onclick = function (e) {
      var f = e.target.closest(".fav"); if (!f) return;
      toggleFav(f.getAttribute("data-code"));
      renderTable(DATA);
    };
  }'''
assert js.count(old) == 1, "step11"
js = js.replace(old, new, 1)

open(p, "w").write(js)
print("app.js 功能升级 OK:", len(js))
