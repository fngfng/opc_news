# GitHub Trending Hub — 架构设计规格

**日期**：2026-06-05  
**版本**：v1.0  
**状态**：已确认，开始实现

---

## 一、整体架构

```
┌─────────────────────────────────────────────────────┐
│              数据管道（每日定时执行一次）                  │
│                                                      │
│  pipeline/fetch_trending.py                          │
│     ├─► github-trending-api.de（主数据源）             │
│     └─► 爬取 github.com/trending（兜底）               │
│                       ↓                              │
│  pipeline/ai_summary.py                              │
│     └─► DeepSeek API 批量生成中文解读                   │
│                       ↓                              │
│  pipeline/build_data.py                              │
│     ├─► data/daily.json                              │
│     ├─► data/weekly.json（近7天 history/ 聚合）        │
│     └─► data/history/YYYY-MM-DD.json                │
└─────────────────────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────┐
│                前端（纯静态 HTML）                       │
│  index.html  ← fetch('data/daily.json')             │
│  功能：卡片展示 / 语言筛选 / 周报 / 历史回溯 / 弹窗详情      │
└─────────────────────────────────────────────────────┘
```

**触发方式：**
- 当前：Mac `cron` / `launchd` 每日 08:00 执行 `python pipeline/run.py`
- 后期：`.github/workflows/daily.yml` 接管（代码零改动）

---

## 二、目录结构

```
github_news/
├── index.html                    # 前端单页面（读取 data/*.json）
├── data/                         # pipeline 输出，不手动编辑
│   ├── daily.json                # 今日热门 + AI 解读
│   ├── weekly.json               # 近7天汇总
│   └── history/
│       └── YYYY-MM-DD.json       # 每日历史快照
├── pipeline/
│   ├── run.py                    # 入口：串联所有步骤
│   ├── fetch_trending.py         # 数据抓取（双源容灾）
│   ├── ai_summary.py             # DeepSeek AI 批量解读
│   └── build_data.py             # 组装最终 JSON 输出
├── .github/
│   └── workflows/
│       └── daily.yml             # GitHub Actions（后期启用）
├── doc/
│   ├── README.md
│   ├── ISSUES.md
│   └── 2026-06-05-architecture-design.md（本文件）
├── .env.example                  # 配置模板
├── .env                          # 本地真实配置（gitignore）
└── requirements.txt
```

---

## 三、数据格式

### data/daily.json

```json
{
  "generated_at": "2026-06-05T08:00:00+08:00",
  "period": "daily",
  "source": "github-trending-api.de",
  "repos": [
    {
      "rank": 1,
      "name": "repo-name",
      "owner": "author",
      "url": "https://github.com/author/repo-name",
      "description": "原始英文描述",
      "stars": 12400,
      "forks": 830,
      "stars_today": 423,
      "language": "Python",
      "topics": ["ai", "agent"],
      "summary": {
        "what": "作者做了什么（AI 生成）",
        "purpose": "方便干什么（AI 生成）",
        "scene": "应用场景（AI 生成）"
      }
    }
  ]
}
```

### data/weekly.json

```json
{
  "generated_at": "2026-06-05T08:00:00+08:00",
  "week_range": "2026-05-30 ~ 2026-06-05",
  "total_projects": 25,
  "total_stars_today": 18500,
  "top_languages": [["Python", 8], ["TypeScript", 6]],
  "trending_topics": [["ai", 12], ["agent", 7]],
  "top_picks": [...],
  "insights": "AI 生成的本周洞察文字"
}
```

---

## 四、Pipeline 模块说明

### fetch_trending.py

| 步骤 | 说明 |
|------|------|
| 1 | 请求 `https://github-trending-api.de/repositories?language=&since=daily` |
| 2 | 解析返回 JSON，提取核心字段 |
| 3 | 若第三方 API 失败（超时/429），降级爬取 `github.com/trending` |
| 4 | 返回标准化 repo 列表（最多 25 个） |

### ai_summary.py

| 步骤 | 说明 |
|------|------|
| 1 | 读取 repo 列表，已有缓存的跳过（用 history 比对避免重复调用） |
| 2 | 按批次（5个/次）调用 DeepSeek API |
| 3 | Prompt 固定输出三段 JSON：what / purpose / scene |
| 4 | 失败单项保留 fallback 模板，不中断整体流程 |

### build_data.py

| 步骤 | 说明 |
|------|------|
| 1 | 合并 fetch + summary 结果，输出 `data/daily.json` |
| 2 | 保存 `data/history/YYYY-MM-DD.json` |
| 3 | 读取近 7 天 history 文件，聚合生成 `data/weekly.json` |
| 4 | 调用 DeepSeek 生成 weekly insights（每周一次，有缓存则跳过） |

---

## 五、AI Prompt 设计

```
你是一个技术项目分析师，请用中文简洁分析以下 GitHub 项目：

项目名：{owner}/{name}
描述：{description}
主要语言：{language}
话题标签：{topics}

请严格按以下 JSON 格式输出，不要有其他内容：
{
  "what": "作者构建了什么（1-2句，聚焦技术实现）",
  "purpose": "解决了什么问题/方便干什么（1-2句）",
  "scene": "典型应用场景（用顿号分隔，3-5个场景）"
}
```

---

## 六、触发配置

### Mac cron（当前）

```bash
# crontab -e 添加以下行（每日 08:00 执行）
0 8 * * * cd /path/to/github_news && python pipeline/run.py >> logs/pipeline.log 2>&1
```

### GitHub Actions（后期）

```yaml
# .github/workflows/daily.yml
on:
  schedule:
    - cron: '0 0 * * *'   # UTC 00:00 = 北京 08:00
  workflow_dispatch:        # 支持手动触发
```

---

## 七、已知问题对照

| 问题编号 | 本方案解决方式 |
|---------|-------------|
| D1 | 改用 github-trending-api.de + 爬虫双源 |
| D2 | 直接读取 `stars_today` 字段 |
| D3 | history/ 保存每日快照，weekly 从7天数据聚合 |
| D4 | DeepSeek API 实时生成，每项目独立分析 |
| D5 | weekly insights 由 AI 动态生成 |
| F2 | 前端新增今日/本周/本月 tab |
| F3 | history/ 目录支持历史回溯 |
| F4 | 卡片展示 stars_today 字段 |
| T1 | 后端抓取，前端只读静态 JSON，无 API 频率问题 |
| T2 | cron/Actions 定时触发 |
| T3 | 每日重新生成，无过时静态数据 |
| T4 | 真实7天历史聚合 |
