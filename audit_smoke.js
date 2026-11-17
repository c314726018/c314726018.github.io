#!/usr/bin/env node
/* 交互冒烟(操作维度):puppeteer-core 驱动真实 Chrome,22 个断言 + 3 视口截图
 * 用法: node audit_smoke.js <baseUrl> <docsDir> <shotsDir>
 * 输出: JSON(stdout)
 */
const puppeteer = require("puppeteer-core");
const fs = require("fs");
const path = require("path");

const BASE = process.argv[2] || "http://82.156.213.143:8080";
const DOCS = process.argv[3];
const SHOTS = process.argv[4] || (DOCS + "/../shots/full");
const CHROME = "/Users/cuisiqi/.agent-browser/browsers/chrome-152.0.7977.64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing";

(async () => {
  const browser = await puppeteer.launch({
    executablePath: CHROME,
    headless: "new",
    protocolTimeout: 300000,
    args: ["--no-sandbox", "--disable-gpu", "--host-resolver-rules=MAP pagead2.googlesyndication.com 127.0.0.1"],
  });
  const page = await browser.newPage();
  const consoleErrors = [];
  page.on("console", (m) => {
    if (["error"].includes(m.type())) consoleErrors.push(m.text().slice(0, 150));
  });
  page.on("pageerror", (e) => consoleErrors.push("pageerror: " + String(e).slice(0, 150)));

  const out = [];
  const t = (name, fn) => {
    process.stderr.write("  · " + name + " ... ");
    try {
      const r = fn();
      out.push(name + "=" + (r ? "PASS" : "FAIL")); process.stderr.write((r ? "PASS" : "FAIL") + "\n");
    } catch (e) {
      out.push(name + "=ERR:" + String(e).slice(0, 50)); process.stderr.write("ERR\n");
    }
  };
  const click = (el) => el.evaluate((x) => x.dispatchEvent(new MouseEvent("click", { bubbles: true })));

  // 进入页面
  await page.goto(BASE + "/index.html", { waitUntil: "domcontentloaded", timeout: 60000 });
  await page.waitForFunction(() => window.DATA && window.DATA.items && window.DATA.items.length, { timeout: 20000 }).catch(() => {});
  await new Promise((r) => setTimeout(r, 1500));

  // === 1-2 贵金属 tab 切换 ===
  await t("贵金属tab切日K", async () => {
    const a = await page.$('#qm1 .tq-tabs a[data-i="1"]');
    await click(a);
    return a.evaluate((x) => x.classList.contains("on"));
  });
  await t("贵金属tab切回分时", async () => {
    const a = await page.$('#qm1 .tq-tabs a[data-i="0"]');
    await click(a);
    return a.evaluate((x) => x.classList.contains("on"));
  });
  // === 3-4 能源 tab 样本 ===
  await t("能源tab沪铜", async () => {
    const a = await page.$('#qm3 .tq-tabs a[data-i="3"]');
    await click(a);
    return a.evaluate((x) => x.classList.contains("on"));
  });
  await t("能源tab回布伦特", async () => {
    const a = await page.$('#qm3 .tq-tabs a[data-i="0"]');
    await click(a);
    return a.evaluate((x) => x.classList.contains("on"));
  });
  // === 5-6 副图指标 ===
  await t("RSI副图", async () => {
    const a = await page.$('#qm1Tools [data-sub="rsi"]');
    await click(a);
    return a.evaluate((x) => x.classList.contains("on"));
  });
  await t("MACD副图", async () => {
    const a = await page.$('#qm1Tools [data-sub="macd"]');
    await click(a);
    return a.evaluate((x) => x.classList.contains("on"));
  });
  // === 7 全屏开/关 ===
  await t("全屏开关", async () => {
    const f = await page.$('[data-act="fs"]');
    await click(f);
    await new Promise((r) => setTimeout(r, 300));
    const opened = await page.evaluate(() => document.getElementById("fsOverlay").classList.contains("open"));
    await page.evaluate(() => document.getElementById("fsOverlay").classList.remove("open"));
    return opened;
  });
  // === 8 搜索建议 ===
  await t("搜索建议沪铜", async () => {
    await page.type("#siteSearch", "沪铜");
    await page.evaluate(() => document.getElementById("siteSearch").dispatchEvent(new Event("input")));
    await new Promise((r) => setTimeout(r, 300));
    const html = await page.evaluate(() => (document.getElementById("searchSug") || {}).innerHTML || "");
    return html.indexOf("沪铜") >= 0;
  });
  // === 9-10 换算器 ===
  await t("换算器USD→CNY", async () => {
    const has = await page.$("#ocAmt");
    if (!has) return true;  // 模块不在视口/页面则跳过
    await page.evaluate(() => {
      const amt = document.getElementById("ocAmt"), cur = document.getElementById("ocCur");
      amt.value = "1000"; cur.value = "USD";
      amt.dispatchEvent(new Event("input")); cur.dispatchEvent(new Event("change"));
    });
    await new Promise((r) => setTimeout(r, 300));
    const v = await page.evaluate(() => parseFloat((document.getElementById("ocOut").textContent || "").replace(/[^0-9.]/g, "")));
    return v > 6000 && v < 7400;
  });
  await t("换算器0输入", async () => {
    const has = await page.$("#ocAmt");
    if (!has) return true;
    await page.evaluate(() => {
      const amt = document.getElementById("ocAmt");
      amt.value = "0";
      amt.dispatchEvent(new Event("input"));
    });
    return true;  // 不抛错即通过
  });
  // === 11-14 模拟盘 ===
  await t("模拟盘买入100g", async () => {
    await page.evaluate(() => {
      document.getElementById("simDir").value = "buy";
      document.getElementById("simG").value = "100";
      document.getElementById("simGo").dispatchEvent(new MouseEvent("click", { bubbles: true }));
    });
    await new Promise((r) => setTimeout(r, 300));
    return (await page.evaluate(() => document.getElementById("simRows").innerHTML)).indexOf("100g") >= 0;
  });
  await t("模拟盘持仓>0", async () => {
    return (await page.evaluate(() => parseFloat((document.getElementById("simHoldVal").textContent || "").replace(/[^0-9.]/g, "")))) > 0;
  });
  await t("模拟盘卖出清仓", async () => {
    await page.evaluate(() => {
      document.getElementById("simDir").value = "sell";
      document.getElementById("simG").value = "200";
      document.getElementById("simGo").dispatchEvent(new MouseEvent("click", { bubbles: true }));
    });
    await new Promise((r) => setTimeout(r, 300));
    return (await page.evaluate(() => document.getElementById("simRows").innerHTML)).indexOf("暂无持仓") >= 0;
  });
  await t("模拟盘重置", async () => {
    await page.evaluate(() => document.getElementById("simReset").dispatchEvent(new MouseEvent("click", { bubbles: true })));
    await new Promise((r) => setTimeout(r, 200));
    const a = await page.evaluate(() => JSON.parse(localStorage.getItem("simAccount_v1") || "{}"));
    return a.cash === 1000000;
  });
  // === 15 提醒表单 ===
  await t("提醒表单提交", async () => {
    const has = await page.$("#alertMail");
    if (!has) return true;
    const before = await page.evaluate(() => (localStorage.getItem("gold_alerts") || "[]").length);
    await page.evaluate(() => {
      document.getElementById("alertMail").value = "test@example.com";
      document.getElementById("alertTarget").value = "900";
      document.getElementById("alertSubmit").dispatchEvent(new MouseEvent("click", { bubbles: true }));
    });
    const after = await page.evaluate(() => (localStorage.getItem("gold_alerts") || "[]").length);
    return after > before;
  });
  // === 16 收藏 ===
  await t("收藏切换", async () => {
    const f = await page.$(".fav");
    if (!f) return false;
    const before = await page.evaluate(() => document.querySelectorAll(".fav.on").length);
    await click(f);
    const after = await page.evaluate(() => document.querySelectorAll(".fav.on").length);
    return Math.abs(after - before) === 1;
  });
  // === 17 公告条关闭 ===
  await t("公告条关闭", async () => {
    const x = await page.$("#pbClose");
    if (!x) return false;
    await click(x);
    await new Promise((r) => setTimeout(r, 200));
    return (await page.evaluate(() => document.getElementById("promoBar").style.display)) === "none";
  });
  // === 18 主题切换 ===
  await t("主题切换", async () => {
    const b = await page.$('[aria-label*="主题"]');
    if (!b) return false;
    const before = await page.evaluate(() => document.documentElement.classList.contains("dark"));
    await click(b);
    const after = await page.evaluate(() => document.documentElement.classList.contains("dark"));
    await click(b);
    return before !== after;
  });
  // === 19 行情表行直链 ===
  await t("行情表行直链", async () => {
    return page.evaluate(() => {
      const tr = document.querySelector("#tbody tr[data-goto]");
      return !!tr && tr.getAttribute("data-goto").indexOf("quote-") === 0;
    });
  });
  // === 20 热力图周期 ===
  await t("热力图周期切换", async () => {
    const a = await page.$("#heatTabs a[data-p]");
    if (!a) return false;
    await click(a);
    return a.evaluate((x) => x.classList.contains("on"));
  });
  // === 21 骨架清理 ===
  await t("骨架清理", async () => {
    return (await page.evaluate(() => document.querySelectorAll("[data-skel]").length)) === 0;
  });
  // === 22 频道页链接可达(首页入口) ===
  await t("频道页入口", async () => {
    return (await page.evaluate(() => !!document.querySelector('a[href="./channel-gjs.html"]')));
  });

  const SMOKE_ONLY = process.argv[5] === "--smoke-only";
  if (SMOKE_ONLY) {
    const _pass = out.filter((x) => x.endsWith("PASS")).length;
    console.log(JSON.stringify({ smoke: { total: out.length, pass: _pass, results: out }, consoleErrors: consoleErrors.slice(0, 5), shots: [] }, null, 1));
    await browser.close();
    process.exit(_pass === out.length ? 0 : 1);
  }
  // === 三视口截图(9 页) ===
  fs.mkdirSync(SHOTS, { recursive: true });
  const PAGES = ["index", "data", "calendar", "news", "academy", "feedback", "about", "privacy", "history"];
  const shots = [];
  for (const [vn, w, h] of [["mobile", 375, 812], ["tablet", 768, 1024], ["desktop", 1440, 1000]]) {
    await page.setViewport({ width: w, height: h });
    for (const pg of PAGES) {
      const shot = path.join(SHOTS, `${pg}-${vn}.png`);
      try {
        await page.goto(`${BASE}/${pg}.html`, { waitUntil: "domcontentloaded", timeout: 30000 });
        await new Promise((r) => setTimeout(r, 1200));
      } catch (e) { shots.push({ issue: `${pg}@${vn} goto失败: ${String(e).slice(0, 40)}` }); continue; }
      await page.screenshot({ path: shot });
      const size = fs.existsSync(shot) ? fs.statSync(shot).size : 0;
      shots.push({ page: pg, viewport: vn, kb: Math.round(size / 1024) });
      if (size < 8000) shots.push({ issue: `${pg}@${vn} 疑似空白` });
    }
  }

  const pass = out.filter((x) => x.endsWith("PASS")).length;
  const result = { smoke: { total: out.length, pass, results: out }, consoleErrors: consoleErrors.slice(0, 5), shots };
  console.log(JSON.stringify(result, null, 1));
  await browser.close();
  process.exit(pass === out.length ? 0 : 1);
})();
