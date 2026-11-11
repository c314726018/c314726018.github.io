# 贵金属实时行情站（SGE）

一个**零依赖、零服务器成本**的贵金属行情网站：从上海黄金交易所（SGE）官方接口实时抓取
黄金 / 白银 / 铂金 / 钯金 价格，免费托管，永不空白（带种子兜底）。

## 两种部署方案

| 方案 | 免费 | 国内速度 | 数据时效 | 适合 |
|---|---|---|---|---|
| **A. Cloudflare Pages（推荐）** | ✅ 无限流量 | 🚀 国内最快 | 访问即实时 | 想要国内快 + 免运维 |
| **B. GitHub Pages（备选）** | ✅ 完全免费 | 🐢 国内偏慢 | 每 2h 定时刷新 | 已有 GitHub 账号、不介意速度 |

> 极狐 GitLab 个人账号不可用，已排除。

---

## 方案 A：Cloudflare Pages（推荐，免定时 CI）

**原理**：用 Cloudflare Pages Functions 在服务端代理 SGE（绕开浏览器 CORS），
访客打开页面时实时拉取最新行情，每个合约边缘缓存 5 分钟，上游挂了自动回退种子数据。
无需任何定时任务，部署一次永久运行。

### 你需要做的（约 5 分钟）

1. 注册 Cloudflare 账号（免费）：https://dash.cloudflare.com/sign-up
2. 左侧 **Workers & Pages** → **Create** → **Pages** → **Connect to Git** → 选你的 GitHub 仓库
3. 构建设置：
   - **Root directory（根目录）**：`gold-site/cf`  ← 关键，只部署 cf 子目录
   - **Framework preset**：`None`
   - **Build command**：留空
   - **Output directory**：`.`
4. 点 **Save and Deploy**，约 1 分钟后获得 `https://<项目名>.pages.dev` 域名。
5. （可选）在 Pages 设置里绑定自定义域名（免费，需自备域名）。

### 目录说明（方案 A）
- `cf/index.html` — 前端页，加载时调用 `/api/quote`
- `cf/functions/api/quote.js` — 服务端代理 SGE（含边缘缓存 + 种子兜底）
- `cf/vendor/chart.umd.min.js` — 本地自托管 Chart.js（不依赖外部 CDN，国内更稳）

### 本地预览（可选）
```bash
cd gold-site/cf
npx wrangler pages dev . --binding
# 打开 http://localhost:8788
```

---

## 方案 B：GitHub Pages（备选，国内偏慢）

### 你需要做的（约 5 分钟）
1. GitHub 新建仓库（如 `gold-price`）。
2. 推送本项目：
   ```bash
   cd gold-site
   git remote add origin https://github.com/<用户名>/<仓库>.git
   git branch -M main
   git push -u origin main
   ```
   > 推送需 GitHub 登录。凭据未配置时用 `gh auth login`，或提前在 GitHub 生成 PAT 后 `git push` 时粘贴。
3. 开启 Pages：仓库 → Settings → Pages → Source 选 **main** 分支、**/docs** 目录 → Save。
4. 开启自动更新：Actions → 左侧 `更新贵金属行情` → 首次点 **Enable workflow**。
   之后每个工作日每 2 小时自动抓取并提交，页面随之刷新。

### 目录说明（方案 B）
- `fetch.py` — 抓取 SGE 行情，写 `data.json`（带退避 + 缓存兜底）
- `build.py` — 读 `data.json` 渲染 `docs/index.html`
- `data.json` — 行情缓存（也是首次部署前的种子数据）
- `.github/workflows/update.yml` — 定时抓取 + 构建 + 提交

---

## 变现入口（按需加）
| 方式 | 怎么接 |
|---|---|
| 展示广告 | 百度联盟 / Google AdSense 代码贴进 `docs/index.html`（方案 B）或 `cf/index.html`（方案 A）模板 |
| 开户返佣 | 对接**持牌期货公司**开户链接，放页面底部（务必合规） |
| 私域/知识星球 | 页面留微信/社群入口 |

## 合规红线
- 本页仅做**行情展示聚合**，不提供任何投资建议、不代客理财。
- 页面已标注「仅供参考，不构成投资建议」。
- 开户返佣必须对接**持牌机构**；外盘/黑平台/客损分成 = 违法，严禁。

## 自定义品种/单位
- 方案 A：编辑 `cf/functions/api/quote.js` 顶部的 `SYMBOLS`。
- 方案 B：编辑 `fetch.py` 顶部的 `SYMBOLS`。
