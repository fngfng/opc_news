# OPC News

开源项目内容聚合仓库，收录各类开源热点追踪、信息整合工具。

---

## 子项目

### 🔥 [github_news](./github_news/) — GitHub 热门项目追踪

每日自动抓取真实 GitHub Trending 榜单，AI 生成中文解读，支持每周趋势深度分析。

**在线访问：** 部署到 GitHub Pages 后可直接浏览（见下方部署说明）

#### 功能特性

| 功能 | 说明 |
|------|------|
| 每日热门 | 爬取 github.com/trending，展示今日新增星标 |
| AI 项目解读 | DeepSeek-V4-Pro 生成"做了什么 / 干什么用 / 应用场景" |
| AI 今日总结 | 对当天热榜生成一段趋势洞察 |
| 每周精选 | 7 天数据聚合，含 Top10、语言分布、热门话题 |
| 每周趋势分析 | AI 分析最热方向 / 语言趋势 / 重点项目 |
| 手动刷新 | 本地服务支持一键刷新，当日已有数据直接读缓存 |
| 历史记录 | 每日快照存入 `data/history/`，支持回溯 |

#### 技术栈

- **前端**：纯静态 HTML + CSS + JS（无框架）
- **数据管道**：Python 3.9+，爬虫 + AI 解读
- **AI 模型**：硅基流动 `deepseek-ai/DeepSeek-V4-Pro`
- **自动化**：GitHub Actions 每日 08:00（北京时间）自动运行
- **部署**：GitHub Pages

#### 快速开始（本地运行）

```bash
# 1. 克隆仓库
git clone https://github.com/<你的用户名>/<仓库名>.git
cd <仓库名>

# 2. 安装依赖
pip install -r github_news/requirements.txt

# 3. 配置 API Key（从 siliconflow.cn 获取）
cp github_news/.env.example github_news/.env
# 编辑 .env，填入 DEEPSEEK_API_KEY

# 4. 运行数据管道（生成 data/daily.json 和 data/weekly.json）
cd github_news/pipeline
python run.py

# 5. 启动本地服务
cd ../..
python github_news/server.py
# 浏览器访问 http://localhost:8888
```

#### 设置每日自动运行（Mac 本地）

```bash
# 编辑 crontab，每天 08:00 自动更新
crontab -e
# 添加以下一行：
0 8 * * * cd /path/to/opc_news && python github_news/pipeline/run.py >> /tmp/trending.log 2>&1
```

#### GitHub Actions 自动部署

1. 在 GitHub 仓库 **Settings → Secrets → Actions** 添加 Secret：
   - `DEEPSEEK_API_KEY`：你的硅基流动 API Key

2. 在 **Settings → Pages** 中：
   - Source 选择 **GitHub Actions**

3. 推送代码后，Actions 会自动每日运行并部署到 Pages

---

## 目录结构

```
opc_news/
├── README.md                  # 本文件
├── .gitignore
├── .github/
│   └── workflows/
│       └── daily.yml          # 每日自动更新 + Pages 部署
└── github_news/               # GitHub 热门追踪项目
    ├── index.html             # 前端页面
    ├── server.py              # 本地开发服务器
    ├── requirements.txt
    ├── .env.example
    ├── pipeline/              # 数据抓取与 AI 解读
    │   ├── run.py
    │   ├── fetch_trending.py
    │   ├── ai_summary.py
    │   └── build_data.py
    ├── data/                  # 每日生成数据（自动提交）
    │   ├── daily.json
    │   ├── weekly.json
    │   └── history/
    └── doc/                   # 项目文档
        ├── README.md
        ├── ISSUES.md
        └── 2026-06-05-architecture-design.md
```

---

## License

MIT
