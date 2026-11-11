/* 广告位配置 —— 把广告联盟（百度联盟 / AdSense 等）给你的代码整段粘到 ADS_SNIPPET 即可。
 * 支持含 <script> 的片段：会自动重新执行脚本，确保广告正常加载。
 * 留空则显示占位提示，不影响其他功能。
 * 改完本文件后提交推送即可，每小时重建不会覆盖它（它是静态文件）。
 */
var ADS_SNIPPET = ""; // 例：<ins class="adsbygoogle" ...></ins><script>(adsbygoogle=window.adsbygoogle||[]).push({})</script>

(function () {
  "use strict";
  function fill(slot, html) {
    slot.innerHTML = html;
    // innerHTML 不会执行其中的 <script>，手动重建以触发执行
    var scripts = slot.querySelectorAll("script");
    for (var i = 0; i < scripts.length; i++) {
      var s = scripts[i];
      var ns = document.createElement("script");
      if (s.src) ns.src = s.src; else ns.textContent = s.textContent;
      if (s.parentNode) s.parentNode.replaceChild(ns, s);
    }
  }
  function render() {
    var slots = document.querySelectorAll(".ad-slot");
    if (!slots.length) return;
    if (ADS_SNIPPET && ADS_SNIPPET.trim()) {
      slots.forEach(function (s) {
        s.classList.add("ad-active");
        fill(s, ADS_SNIPPET);
      });
    } else {
      slots.forEach(function (s) {
        s.innerHTML = "广告位（把百度联盟 / AdSense 代码粘贴到 docs/ads.js 的 ADS_SNIPPET）";
      });
    }
  }
  if (document.readyState !== "loading") render();
  else document.addEventListener("DOMContentLoaded", render);
})();
