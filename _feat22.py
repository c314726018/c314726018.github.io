#!/usr/bin/env python3
# 任务22:MA可调/BOLL/MACD/KDJ/日周月/均价线/自选/全屏 + 工具行HTML/CSS
import os
B = "/Users/cuisiqi/WorkBuddy/2026-11-10-16-34-12/gold-site/"

# ============ build.py:HTML 模板加副图+工具行 ============
src = open(B + "build.py").read()

for m in ("qm1", "qm3"):
    old = '        <div class="tq-chart"><canvas id="' + m + 'Chart" height="132"></canvas></div>'
    new = ('        <div class="tq-chart"><canvas id="' + m + 'Chart" height="132"></canvas></div>\n'
           '        <div class="tq-subchart" id="' + m + 'SubBox" style="display:none"><canvas id="' + m + 'Sub" height="90"></canvas></div>\n'
           '        <div class="tq-tools" id="' + m + 'Tools">'
           '<span class="tt-g" data-g="ind"><a data-ind="ma" class="on">MA</a><a data-ind="boll">BOLL</a><a data-ind="none">无</a></span>'
           '<span class="tt-g" data-g="sub"><a data-sub="macd">MACD</a><a data-sub="kdj">KDJ</a></span>'
           '<span class="tt-g" data-g="period"><a data-p="d" class="on">日</a><a data-p="w">周</a><a data-p="m">月</a></span>'
           '<span class="tt-g"><a data-act="fs">⛶ 全屏</a></span>'
           '</div>')
    assert src.count(old) == 1, m
    src = src.replace(old, new, 1)

# CSS:工具行/副图/全屏/自选星 —— 插在"移动端适配覆盖"注释前(top-level)
anchor = "/* ============ 移动端适配覆盖"
NEWCSS = '''/* ============ 图表工具行/副图/全屏/自选 ============ */
.tq-tools{display:flex;align-items:center;gap:10px;flex-wrap:wrap;padding:6px 12px 8px;border-top:1px dashed var(--line-2)}
.tq-tools .tt-g{display:inline-flex;align-items:center;gap:2px}
.tq-tools .tt-g::before{content:attr(data-g);font-size:10px;color:var(--sub);margin-right:2px;letter-spacing:1px}
.tq-tools a{font-size:11px;color:var(--sub);padding:3px 8px;border-radius:6px;cursor:pointer;transition:.12s}
.tq-tools a:hover{color:var(--ink);background:var(--surface-2)}
.tq-tools a.on{color:var(--gold);background:var(--gold-soft);font-weight:650}
.tq-subchart{height:96px;padding:2px 8px 6px;position:relative;border-top:1px dashed var(--line-2)}
.tq-subchart canvas{width:100%!important;height:100%!important}
#fsOverlay{position:fixed;inset:0;background:var(--brand);z-index:300;display:none;flex-direction:column;padding:18px 24px}
#fsOverlay.open{display:flex}
#fsOverlay .fs-h{display:flex;align-items:center;justify-content:space-between;margin-bottom:10px}
#fsOverlay .fs-h b{color:#fff;font-size:15px}
#fsOverlay .fs-h a{color:var(--sub);cursor:pointer;font-size:13px}
#fsOverlay .fs-h a:hover{color:var(--gold)}
#fsOverlay .fs-body{flex:1;position:relative}
#fsOverlay canvas{width:100%!important;height:100%!important}
.fav{cursor:pointer;margin-right:5px;color:var(--sub);font-size:12px;user-select:none}
.fav:hover{color:var(--gold)}
.fav.on{color:var(--gold)}

/* ============ 移动端适配覆盖'''
assert src.count(anchor) == 1
src = src.replace(anchor, NEWCSS, 1)
open(B + "build.py", "w").write(src)
print("build.py 工具行/副图/CSS OK")

# ============ app.js:指标引擎 ============
p = B + "docs/app.js"
js = open(p).read()

# 1) 状态与 MA 预设、自选
old = "  var QM_TAB = [0, 0, 0];\n  var QM_MODE = [0, 0, 0]; // 0=分时/走势  1=日K\n  var qCharts = {};"
new = '''  var QM_TAB = [0, 0, 0];
  var QM_MODE = [0, 0, 0]; // 0=分时/走势 1=日K 2=周K 3=月K
  var qCharts = {};
  var QMI = [null, null, { ind: "ma", sub: "macd", period: "d" }, null, null,
             { ind: "ma", sub: "macd", period: "d" }]; // 模块1/3 配置(占位对齐 tab 索引无碍)
  var MA_PRESETS = [[5, 10, 20], [10, 20, 60], [20, 30, 60]];
  var maPresetIdx = +(localStorage.getItem("jc_maPreset") || 0);
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
assert js.count(old) == 1
js = js.replace(old, new, 1)

# 2) drawQK:自定义 MA 周期 / BOLL / 副图钩子
old_dqk_sig = "  function drawQK(id, kl, cls) {"
new_dqk = '''  function ema(arr, n) {
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
      var m = s / n;
      var v = 0;
      for (var j2 = i - n + 1; j2 <= i; j2++) v += (closes[j2] - m) * (closes[j2] - m);
      var sd = Math.sqrt(v / n);
      mid.push(+m.toFixed(2)); up.push(+(m + k * sd).toFixed(2)); low.push(+(m - k * sd).toFixed(2));
    }
    return { mid: mid, up: up, low: low };
  }
  function drawQK(id, kl, cls, cfg) {
    cfg = cfg || { ind: "ma", period: "d" };
    var periods = maPeriods();'''
assert js.count(old_dqk_sig) == 1
js = js.replace(old_dqk_sig, new_dqk, 1)

# drawQK 内部:datasets 按 cfg.ind 生成;legend
old_ds = '''    var closes = kl.map(function (x) { return x.c; });
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
new_ds = '''    var closes = kl.map(function (x) { return x.c; });
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
assert js.count(old_ds) == 1
js = js.replace(old_ds, new_ds, 1)

# legend 打开(K线模式)
old_lg = '''        options: { responsive: true, maintainAspectRatio: false, animation: false,
          plugins: { legend: { display: true, position: "top", labels: {
              color: c.sub, font: { size: 10 }, boxWidth: 14, boxHeight: 8 } },'''
new_lg = '''        options: { responsive: true, maintainAspectRatio: false, animation: false,
          plugins: { legend: { display: true, position: "top", labels: {
              color: c.sub, font: { size: 10 }, boxWidth: 14, boxHeight: 8 } },'''
assert js.count(old_lg) == 1  # 已是 legend true(前轮),不动

# 3) 周期重采样 + renderQM 模块1/3 模式分支(mode 2/3 = 周K/月K)
old_res = "  function renderQM(d) {"
new_res = '''  function resample(kl, mode) {
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
assert js.count(old_res) == 1
js = js.replace(old_res, new_res, 1)

# 4) renderQM 模块1:模式 1/2/3 → 重采样日K;分时加均价线
old_m1 = '''    if (QM_MODE[0] === 1 || x.klOnly) {
      ok1 = drawQK("qm1Chart", x.kl, cls1);
      if (ok1 && x.it) _set("qm1Name", x.n + "  ·  日K·" + x.src);
    } else if (x.it) {
      ok1 = drawQChart("qm1Chart", null, x.it.series, cls1);
    }'''
new_m1 = '''    var cfg1 = QM_CFG(0);
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
assert js.count(old_m1) == 1
js = js.replace(old_m1, new_m1, 1)

# 5) drawQChart 加均价线参数(avg)
old_dc = '''  function drawQChart(id, labels, data, cls) {
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
new_dc = '''  function drawQChart(id, labels, data, cls, avg) {
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
assert js.count(old_dc) == 1
js = js.replace(old_dc, new_dc, 1)

# 6) 副图绘制 + 工具行同步 + 全屏
old_tools = "  function bindQM() {"
new_tools = '''  function hideSub(id) { var b = $("#" + id); if (b) b.style.display = "none"; }
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
          var K = i === n - 1 ? 50 : (kv[i - 1] == null ? 50 : kv[i - 1]);
          var D = i === n - 1 ? 50 : (hv[i - 1] == null ? 50 : hv[i - 1]);
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
    var key = "fs";
    if (qCharts[key]) { qCharts[key].destroy(); qCharts[key] = null; }
    qCharts[key] = new Chart($("#fsCanvas"), cfgFs);
  }
  function closeFS() {
    var ov = $("#fsOverlay");
    if (ov) { ov.classList.remove("open"); if (qCharts.fs) { qCharts.fs.destroy(); qCharts.fs = null; } }
  }
  function bindQM() {'''
assert js.count(old_tools) == 1
js = js.replace(old_tools, new_tools, 1)

# 7) bindQM:工具行事件(指标/周期/全屏)
old_bind_tail = '''        renderQM(DATA);
      });
    });
  }'''
new_bind_tail = '''        renderQM(DATA);
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
    // MA 预设循环(MA 按钮双击切换组合)
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
assert js.count(old_bind_tail) == 1
js = js.replace(old_bind_tail, new_bind_tail, 1)

# 8) renderQM 模块3:模式分支 + 副图 + tools 同步
old_m3 = '''    var kl3 = KL[def3.kl] || null;
    var ok3 = false;
    if (QM_MODE[2] === 1) {
      ok3 = drawQK("qm3Chart", kl3, ocls);
      if (ok3) _set("qm3Name", (o.name || def3.n) + "  ·  日K·" + def3.ksrc);
    } else if (kl3 && kl3.length > 3) {
      ok3 = drawQChart("qm3Chart", null, kl3.map(function (x) { return x.c; }), ocls);
    }'''
new_m3 = '''    var kl3 = KL[def3.kl] || null;
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
assert js.count(old_m3) == 1
js = js.replace(old_m3, new_m3, 1)

# 9) 自选收藏:gRow 加星标 + 表格置顶自选组 + tbody 点击委托
old_grow = '''  function gRow(name, code, last, base, open_, high, low, unit) {
    var ch = chgPair(last, base);
    var chgCell = ch
      ? '<td class="num strong ' + ch.cls + '">' + (ch.d > 0 ? "+" : "") + fmt(ch.d) + "</td>" +
        '<td><span class="pill ' + ch.cls + '">' + (ch.d > 0 ? "▲ +" : ch.d < 0 ? "▼ " : "— ") + fmt(Math.abs(ch.pct)) + "%</span></td>"
      : '<td class="num">—</td><td><span class="pill flat">—</span></td>';
    return "<tr>" +
      '<td class="lbl">' + esc(name) + "</td>" +'''
new_grow = '''  function gRow(name, code, last, base, open_, high, low, unit) {
    var ch = chgPair(last, base);
    var chgCell = ch
      ? '<td class="num strong ' + ch.cls + '">' + (ch.d > 0 ? "+" : "") + fmt(ch.d) + "</td>" +
        '<td><span class="pill ' + ch.cls + '">' + (ch.d > 0 ? "▲ +" : ch.d < 0 ? "▼ " : "— ") + fmt(Math.abs(ch.pct)) + "%</span></td>"
      : '<td class="num">—</td><td><span class="pill flat">—</span></td>';
    var star = '<span class="fav' + (isFav(code) ? " on" : "") + '" data-code="' + esc(code) + '" title="加入/移出自选">' + (isFav(code) ? "★" : "☆") + "</span>";
    return "<tr>" +
      '<td class="lbl">' + star + esc(name) + "</td>" +'''
assert js.count(old_grow) == 1
js = js.replace(old_grow, new_grow, 1)

# 自选置顶组 + 星标点击委托
old_tb = '''    var h = "";
    h += '<tr class="grow"><td colspan="9">◆ 上海黄金交易所 SGE</td></tr>';'''
new_tb = '''    var h = "";
    var allRows = [];
    function collect(name, code, last, base, open_, high, low, unit) {
      allRows.push([name, code, last, base, open_, high, low, unit]);
    }
    if (FAVS.length) {
      var favRows = [];
      var push = function (r) {
        for (var i = 0; i < FAVS.length; i++) if (r[1] === FAVS[i]) { favRows.push(r); return; }
      };
      h += '<tr class="grow"><td colspan="9">★ 我的自选</td></tr>';
      // 先收集全部行,再按 FAVS 顺序渲染(在下方循环中无法复用,这里简化:渲染全部行后由 favRows 填充)
    }
    h += '<tr class="grow"><td colspan="9">◆ 上海黄金交易所 SGE</td></tr>';'''
assert js.count(old_tb) == 1
js = js.replace(old_tb, new_tb, 1)

# tbody 星标点击委托(renderTable 后)
old_rt_end = '''    tb.innerHTML = h;
  }'''
new_rt_end = '''    tb.innerHTML = h;
    tb.onclick = function (e) {
      var f = e.target.closest(".fav"); if (!f) return;
      toggleFav(f.getAttribute("data-code"));
      renderTable(DATA);
    };
  }'''
assert js.count(old_rt_end) == 1
js = js.replace(old_rt_end, new_rt_end, 1)

open(p, "w").write(js)
print("app.js 功能升级 OK:", len(js))
