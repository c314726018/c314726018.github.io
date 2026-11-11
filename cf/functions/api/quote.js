/**
 * Cloudflare Pages Function —— 服务端代理上海黄金交易所(SGE)行情。
 *
 * 为什么需要它：SGE 接口不返回 CORS 头，浏览器无法直接 fetch。
 * 本函数在 Cloudflare 边缘节点「服务端」请求 SGE，再回传给前端，绕开 CORS。
 *
 * 路径：GET /api/quote  →  返回聚合 JSON
 * 特性：
 *   - 每个合约响应边缘缓存 300s，降低对 SGE 的请求频率（礼貌 + 防 403）
 *   - 上游失败/超时 → 回退到内置种子数据，整站永不空白
 *   - 过滤 -2.0 占位符（非交易时段无报价）
 *
 * 仅做行情展示，不构成任何投资建议。
 */

const SGE_BASE = "https://www.sge.com.cn/graph/quotations";
const HEADERS = {
  "User-Agent":
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 " +
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36",
  Referer: "https://www.sge.com.cn/sjzx/mrhq",
  Accept: "application/json, text/plain, */*",
};

// [中文品种, 合约代码, 计价单位]
const SYMBOLS = [
  ["黄金", "Au99.99", "元/克"],
  ["黄金", "Au99.95", "元/克"],
  ["国际板金", "iAu99.99", "元/克"],
  ["白银", "Ag99.99", "元/千克"],
  ["铂金", "Pt99.95", "元/克"],
  ["钯金", "Pd99.95", "元/克"],
];
const PRIMARY = "Au99.99";

// 上游不可用时的兜底种子（真实采集值，仅作展示占位，非实时）
const SEED = {
  items: [
    { label: "黄金", symbol: "Au99.99", unit: "元/克", last: 883.0, open: 884.5, min: 880.0, max: 888.0, update: "", time: [], series: [] },
    { label: "黄金", symbol: "Au99.95", unit: "元/克", last: 881.0, open: 882.0, min: 879.0, max: 886.0, update: "", time: [], series: [] },
    { label: "国际板金", symbol: "iAu99.99", unit: "元/克", last: 884.01, open: 885.0, min: 881.0, max: 889.0, update: "", time: [], series: [] },
    { label: "白银", symbol: "Ag99.99", unit: "元/千克", last: 12760.0, open: 12780.0, min: 12650.0, max: 12820.0, update: "", time: [], series: [] },
    { label: "铂金", symbol: "Pt99.95", unit: "元/克", last: 389.59, open: 390.2, min: 387.0, max: 392.5, update: "", time: [], series: [] },
  ],
  primary: {
    times: ["09:00", "09:30", "10:00", "10:30", "11:00", "13:30", "14:00", "14:30", "15:00", "15:30"],
    series: [884.5, 885.1, 883.8, 882.4, 881.9, 882.6, 883.2, 884.0, 883.4, 883.0],
    update: "",
    symbol: "Au99.99",
  },
};

function cleanFloats(seq) {
  const out = [];
  for (const x of seq || []) {
    if (x === null || x === "" || x === "-2.0" || x === -2.0) continue;
    const n = parseFloat(x);
    if (!isNaN(n)) out.push(n);
  }
  return out;
}

// 带边缘缓存的单个合约抓取（缓存 300s）
async function fetchSymbol(sym) {
  const apiUrl = `${SGE_BASE}?instid=${encodeURIComponent(sym)}`;
  const req = new Request(apiUrl, { headers: HEADERS });
  const cache = caches.default;
  try {
    const hit = await cache.match(req);
    if (hit) return hit;
  } catch (e) {
    /* ignore */
  }
  let res;
  try {
    res = await fetch(req, { redirect: "follow" });
  } catch (e) {
    return null;
  }
  if (res && res.ok) {
    const body = await res.text();
    const cached = new Response(body, {
      status: 200,
      headers: {
        "content-type": "application/json; charset=utf-8",
        "cache-control": "public, max-age=300",
      },
    });
    try {
      await cache.put(req, cached.clone());
    } catch (e) {
      /* ignore */
    }
    return cached;
  }
  return null;
}

async function fetchAll() {
  const items = [];
  let primary = null;
  let liveCount = 0;

  for (const [label, sym, unit] of SYMBOLS) {
    let entry = null;
    const res = await fetchSymbol(sym);
    if (res) {
      try {
        const d = await res.json();
        const series = cleanFloats(d.data);
        if (series.length) {
          entry = {
            label,
            symbol: sym,
            unit,
            last: series[series.length - 1],
            open: series[0],
            min: d.min != null && d.min !== "" ? parseFloat(d.min) : Math.min(...series),
            max: d.max != null && d.max !== "" ? parseFloat(d.max) : Math.max(...series),
            update: d.delaystr || d.now || "",
            time: d.times || [],
            series,
          };
          liveCount++;
        }
      } catch (e) {
        /* parse failed → 走种子兜底 */
      }
    }
    if (!entry) {
      const s = SEED.items.find((x) => x.symbol === sym);
      if (s) entry = { ...s };
    }
    if (entry) {
      items.push(entry);
      if (sym === PRIMARY) {
        primary = { times: entry.time, series: entry.series, update: entry.update, symbol: sym };
      }
    }
  }

  return {
    generated_at: new Date().toISOString(),
    source: "上海黄金交易所 (SGE)",
    live: liveCount, // 实时合约数，便于前端提示
    items,
    primary,
  };
}

export const onRequest = async ({ request }) => {
  if (request.method !== "GET") {
    return new Response("Method Not Allowed", { status: 405 });
  }
  try {
    const data = await fetchAll();
    return new Response(JSON.stringify(data), {
      headers: {
        "content-type": "application/json; charset=utf-8",
        "cache-control": "public, max-age=120, s-maxage=300",
        "access-control-allow-origin": "*",
      },
    });
  } catch (e) {
    // 极端兜底：整条链路失败，返回种子，保证站点不空白
    return new Response(
      JSON.stringify({
        generated_at: new Date().toISOString(),
        source: "上海黄金交易所 (SGE) · 兜底缓存",
        live: 0,
        items: SEED.items,
        primary: SEED.primary,
        note: String(e),
      }),
      {
        headers: {
          "content-type": "application/json; charset=utf-8",
          "access-control-allow-origin": "*",
        },
      }
    );
  }
};
