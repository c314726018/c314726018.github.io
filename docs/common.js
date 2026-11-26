/* 全站公共交互：主题 / 移动端菜单 / 返回顶部 / 复制行情摘要
 * 三个页面共用。主题切换会派发 themechange，app.js 监听后重绘图表。
 */
(function () {
  "use strict";
  var root = document.documentElement;

  // HIG:主题跟随系统(prefers-color-scheme)，用户手动选择后以本地存储为准。
  // 尽早执行，避免首屏闪白；matchMedia 监听系统切换，未手动覆盖时实时跟随。
  var mq = window.matchMedia ? window.matchMedia("(prefers-color-scheme: dark)") : null;
  function systemDark() { return !!(mq && mq.matches); }
  function applyTheme(dark) {
    root.classList.toggle("dark", dark);
    root.style.colorScheme = dark ? "dark" : "light";
    var btn = document.getElementById("themeBtn");
    if (btn) {
      btn.setAttribute("aria-pressed", dark ? "true" : "false");
      var svg = btn.querySelector(".ico");
      if (svg) {
        svg.innerHTML = dark
          ? '<circle cx="10" cy="10" r="3.6"/><path d="M10 2v2M10 16v2M2 10h2M16 10h2M4.3 4.3l1.4 1.4M14.3 14.3l1.4 1.4M15.7 4.3l-1.4 1.4M5.7 14.3l-1.4 1.4"/>'
          : '<path d="M16.5 12.3A6.8 6.8 0 0 1 7.7 3.5a6.8 6.8 0 1 0 8.8 8.8Z"/>';
      }
    }
  }
  function hasStored() {
    try { return !!localStorage.getItem("gold_theme"); } catch (e) { return false; }
  }
  (function initTheme() {
    var stored = null;
    try { stored = localStorage.getItem("gold_theme"); } catch (e) {}
    applyTheme(stored ? stored === "dark" : systemDark());
  })();
  // 系统主题变化时，仅在用户未手动覆盖的情况下跟随
  if (mq && mq.addEventListener) {
    mq.addEventListener("change", function () { if (!hasStored()) { applyTheme(systemDark()); fireTheme(); } });
  }

  function fireTheme() {
    try { window.dispatchEvent(new Event("themechange")); } catch (e) {
      var ev = document.createEvent("Event"); ev.initEvent("themechange", false, false); window.dispatchEvent(ev);
    }
  }

  function quoteText() {
    var lines = [];
    var gen = document.getElementById("genTime");
    lines.push("金衡网 · 行情摘要");
    if (gen) lines.push(gen.textContent.replace(/^数据生成：/, "生成时间："));
    var sge = document.getElementById("ovSge"), unit = document.getElementById("ovSgeUnit");
    if (sge) lines.push("Au99.99：" + sge.textContent + " " + (unit ? unit.textContent : "元/克"));
    var xau = document.getElementById("hsXau"), fx = document.getElementById("hsFx"),
        prem = document.getElementById("hsPrem");
    if (xau) lines.push("国际现货 XAU/USD：" + xau.textContent);
    if (fx) lines.push("美元兑人民币：" + fx.textContent);
    if (prem) lines.push("国内溢价：" + prem.textContent);
    var rows = document.querySelectorAll("#tbody tr");
    if (rows.length) {
      lines.push("— 上海黄金交易所 —");
      Array.prototype.forEach.call(rows, function (tr) {
        var td = tr.querySelectorAll("td");
        if (td.length >= 3) lines.push(td[0].textContent + " " + td[1].textContent + "  " + td[2].textContent);
      });
    }
    lines.push("来源：" + location.href + "（仅供参考，不构成投资建议）");
    return lines.join("\n");
  }

  function copyText(text) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      return navigator.clipboard.writeText(text);
    }
    return new Promise(function (resolve, reject) {
      var ta = document.createElement("textarea");
      ta.value = text; ta.style.position = "fixed"; ta.style.opacity = "0";
      document.body.appendChild(ta); ta.select();
      try { document.execCommand("copy") ? resolve() : reject(); }
      catch (e) { reject(e); }
      document.body.removeChild(ta);
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    var btn = document.getElementById("themeBtn");
    if (btn) {
      btn.addEventListener("click", function () {
        var dark = !root.classList.contains("dark");
        applyTheme(dark);
        try { localStorage.setItem("gold_theme", dark ? "dark" : "light"); } catch (e) {}
        fireTheme();
      });
    }

    var toggle = document.getElementById("navToggle"), menu = document.getElementById("navMenu");
    if (toggle && menu) {
      toggle.addEventListener("click", function () {
        var open = menu.classList.toggle("open");
        toggle.setAttribute("aria-expanded", open ? "true" : "false");
      });
      menu.addEventListener("click", function (e) {
        if (e.target && e.target.tagName === "A") menu.classList.remove("open");
      });
    }

    var back = document.getElementById("backTop");
    if (back) {
      window.addEventListener("scroll", function () {
        back.classList.toggle("show", window.scrollY > 480);
      }, { passive: true });
      back.addEventListener("click", function () {
        window.scrollTo({ top: 0, behavior: "smooth" });
      });
    }

    var copy = document.getElementById("copyQuote"), note = document.getElementById("copyNote");
    if (copy && note) {
      var original = note.textContent;
      copy.addEventListener("click", function () {
        copyText(quoteText()).then(function () {
          note.textContent = "✓ 行情摘要已复制到剪贴板";
        }).catch(function () {
          note.textContent = "复制失败，请手动选取页面数据";
        });
        setTimeout(function () { note.textContent = original; }, 3200);
      });
    }
  });
})();
