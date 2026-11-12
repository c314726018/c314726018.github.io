#!/usr/bin/env python3
# app.js 多选+等于提交逻辑
import os
B = "/Users/cuisiqi/WorkBuddy/2026-11-10-16-34-12/gold-site/"
ap = B + "docs/app.js"
js = open(ap).read()

# 1) bindAlerts:多选胶囊绑定 + 提交逻辑重写
old = '''  function bindAlerts() {
    var add = $("#alertAdd"); if (add) add.addEventListener("click", addAlert);
    var ms = $("#mailSubmit");
    if (ms) ms.addEventListener("click", function () {
      var addr = ($("#mailAddr") || {}).value || "";
      var symEl = $("#alertSym"), dirEl = $("#alertDir"), valEl = $("#alertVal");
      var sym = symEl ? symEl.value : "", dir = dirEl ? dirEl.value : "above", val = valEl ? valEl.value : "";
      var note = $("#mailNote");
      if (addr.indexOf("@") < 0 || addr.indexOf(".") < 0) { alert("请填写有效的接收邮箱"); return; }
      if (!val) { alert("请先在上方填写目标价格"); return; }
      var box = DATA && DATA.alert_mail;
      if (!box) {
        if (note) note.innerHTML = '邮件订阅通道即将开放。';
        return;
      }
      var body = "订阅类型:邮件价格提醒(免费 1 年)\\n品种:" + sym +
        "\\n方向:" + (dir === "above" ? "高于" : "低于") + "\\n目标价:" + val +
        "\\n接收邮箱:" + addr + "\\n提交时间:" + new Date().toLocaleString();
      window.location.href = "mailto:" + box + "?subject=" +
        encodeURIComponent("【金潮网】邮件提醒订阅 - " + sym + " " + (dir === "above" ? "高于" : "低于") + " " + val) +
        "&body=" + encodeURIComponent(body);
      if (note) note.innerHTML = '已唤起邮件客户端,请点击发送完成订阅;开通后触发时 30 分钟内自动送达。';
    });
  }'''
new = '''  function bindAlerts() {
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
      var body = "订阅类型:邮件价格提醒(免费 1 年)\\n品种(" + syms.length + "):" + syms.join("、") +
        "\\n方向:" + dirTxt + "\\n目标价:" + val +
        "\\n接收邮箱:" + addr + "\\n提交时间:" + new Date().toLocaleString();
      window.location.href = "mailto:" + boxMail + "?subject=" +
        encodeURIComponent("【金潮网】邮件提醒订阅 - " + syms.length + " 个品种 " + dirTxt + " " + val) +
        "&body=" + encodeURIComponent(body);
      if (note) note.innerHTML = '已唤起邮件客户端,请点击发送完成订阅;开通后触发时 30 分钟内自动送达。';
    });
  }'''
assert js.count(old) == 1, "bindAlerts"
js = js.replace(old, new, 1)
open(ap, "w").write(js)
print("app.js 多选提交 OK")
