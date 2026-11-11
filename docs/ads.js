/* 广告位配置 —— 接 AdSense / 百度联盟
 *
 * 1) ADS_LOADER：AdSense 注册时给的"网站代码"（<script async src="...adsbygoogle.js?client=ca-pub-...">）。
 *    会自动注入到 <head>，全站只加载一次，用于账号验证与广告库初始化。改完提交推送即生效。
 *
 * 2) ADS_UNITS：三个广告位的"广告单元代码"（AdSense 后台建单元后给的 <ins class="adsbygoogle" ...> 代码）。
 *    顺序对应：① 顶部通栏 / ② 信息流中插 / ③ 页脚。留空字符串则该位显示占位提示。
 *    三个位可放同一个单元，也可各放不同的。
 *
 * 注意：本文件是静态文件，每小时自动构建（build.py 只重写 index.html / data.json）不会覆盖它。
 */
var ADS_LOADER = '<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-4401257427601930" crossorigin="anonymous"></script>';

var ADS_UNITS = [
  "", // ① 顶部通栏
  "", // ② 信息流 / 内容中插
  ""  // ③ 页脚 / 侧栏
];

(function () {
  "use strict";

  function injectLoader() {
    if (!ADS_LOADER || ADS_LOADER.indexOf("adsbygoogle.js") === -1) return;
    if (document.querySelector('script[src*="adsbygoogle.js"]')) return; // 已存在则跳过，避免重复
    var m = ADS_LOADER.match(/<script[^>]*src="([^"]+)"[^>]*>/i);
    if (!m) return;
    var s = document.createElement("script");
    s.src = m[1];
    s.async = true;
    if (/crossorigin/i.test(ADS_LOADER)) s.crossOrigin = "anonymous";
    document.head.appendChild(s);
  }

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
    injectLoader();
    for (var i = 0; i < slots.length; i++) {
      var slot = slots[i];
      var unit = ADS_UNITS[i] || "";
      if (unit && unit.trim()) {
        slot.classList.add("ad-active");
        fill(slot, unit);
      } else {
        slot.innerHTML = "广告位已接入 AdSense（待在 docs/ads.js 的 ADS_UNITS 填入广告单元代码）";
      }
    }
  }

  if (document.readyState !== "loading") render();
  else document.addEventListener("DOMContentLoaded", render);
})();
