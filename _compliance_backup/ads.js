/* 广告位配置 —— Google AdSense
 *
 * loader（adsbygoogle.js?client=ca-pub-4401257427601930）已由 build.py 直接写入每个页面
 * 的 <head>，用于账号验证与广告库初始化，本文件不再注入，避免重复加载。
 *
 * ADS_UNITS：三个广告位的「广告单元代码」（AdSense 后台建单元后给的
 *   <ins class="adsbygoogle" ...></ins><script>(adsbygoogle=...).push({})</script>）。
 * 顺序对应：① 顶部通栏 / ② 内容中插 / ③ 页脚。
 * 留空字符串的槽位会自动隐藏 —— 审核期间页面不会出现空的广告框，更利于通过。
 *
 * 本文件是静态文件，每小时自动构建（build.py 只重写 index.html / about.html /
 * privacy.html / site.css / data.json）不会覆盖它。
 */
var ADS_UNITS = [
  "", // ① 顶部通栏
  "", // ② 信息流 / 内容中插
  ""  // ③ 页脚 / 侧栏
];

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
    for (var i = 0; i < slots.length; i++) {
      var slot = slots[i];
      var unit = ADS_UNITS[i] || "";
      if (unit && unit.trim()) {
        slot.style.display = "";
        slot.classList.add("ad-active");
        fill(slot, unit);
      } else {
        slot.style.display = "none";
      }
    }
  }

  if (document.readyState !== "loading") render();
  else document.addEventListener("DOMContentLoaded", render);
})();
