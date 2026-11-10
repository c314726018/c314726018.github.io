# 贵金属实时行情站（SGE）

一个**零依赖、零服务器成本**的贵金属行情网站：每天自动从上海黄金交易所（SGE）官方接口抓取
黄金 / 白银 / 铂金 / 钯金 实时价格，生成静态页，托管在 GitHub Pages，永不空白（带本地缓存兜底）。

## 你需要做的事（约 5 分钟）

整个项目已经做好，你只负责「上线」这最后一步：

### 1. 建仓库（GitHub 上点 New repository，名字随便，如 `gold-price`）
### 2. 把本项目推上去
```bash
cd gold-site
git init
git add .
git commit -m "init"
git remote add origin https://github.com/<你的用户名>/<仓库名>.git
git branch -M main
git push -u origin main
```
> 提示：推送需要 GitHub 登录。若未配置凭据，用 `gh auth login` 或先在 GitHub 设好 PAT。

### 3. 开启 Pages
仓库 → Settings → Pages → Source 选 **main** 分支、**/docs** 目录 → Save。
约 1 分钟后访问 `https://<用户名>.github.io/<仓库名>/` 即可。

### 4. 开启自动更新
Actions 页 → 左侧 `更新贵金属行情` → 第一次需点 **Enable workflow**。
之后每个工作日每 2 小时自动抓取并提交，页面随之刷新。也可在 Actions 里手动 **Run workflow** 立即更新。

## 你可选做的事
- **自定义域名**（¥50–100/年）：在 Pages 里填域名并按提示加 DNS CNAME。不用也行，白嫖 `*.github.io`。
- **加广告/返佣**（变现）：在 `docs/index.html` 模板里塞入广告联盟代码或期货公司开户链接即可（见下）。
- **改品种/单位**：编辑 `fetch.py` 顶部的 `SYMBOLS` 列表。

## 变现入口（按需加）
| 方式 | 怎么接 |
|---|---|
| 展示广告 | 百度联盟 / Google AdSense 代码贴进 `build.py` 的模板 |
| 开户返佣 | 对接**持牌期货公司**的开户链接，放页面底部（务必合规，勿碰外盘/黑平台） |
| 私域/知识星球 | 页面留微信/社群入口 |

## 合规红线
- 本页仅做**行情展示聚合**，不提供任何投资建议、不代客理财。
- 页面已标注「仅供参考，不构成投资建议」。
- 开户返佣必须对接**持牌机构**；外盘/黑平台/客损分成 = 违法，严禁。

## 文件说明
- `fetch.py` — 抓取 SGE 行情，写 `data.json`（带退避+缓存兜底）
- `build.py` — 读 `data.json` 渲染 `docs/index.html`
- `data.json` — 行情缓存（也是首次部署前的种子数据）
- `.github/workflows/update.yml` — 定时抓取+构建+提交
