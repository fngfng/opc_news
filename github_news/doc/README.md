# GitHub Trending Hub - 项目说明文档

## 项目概述

GitHub Trending Hub 是一个纯静态的 GitHub 热门开源项目追踪网站，无需后端服务即可运行。通过调用 GitHub 公开 API，自动聚合每日和每周热门开源项目，并提供项目解读、星标趋势等功能。

---

## 已知问题与功能差距

详见 [ISSUES.md](./ISSUES.md)，包含数据准确性、功能缺失、技术局限三类共 13 个问题，并附校验状态跟踪。

---

## 功能模块

### 1. 每日热门（Daily Trending）

- 调用 GitHub Search API，按星标数降序抓取最近活跃的高热度项目
- 默认展示 24 个项目，以卡片网格布局呈现
- 每个项目卡片包含：
  - 项目名称 / 作者头像缩写
  - 项目描述（最多 2 行）
  - 编程语言（带色点）、星标数、Fork 数
  - HOT 徽章（前 5 名）
  - 可展开的「项目解读」（作者做了什么 / 方便干什么 / 应用场景）

### 2. 每周精选（Weekly Summary）

基于每日数据自动汇总生成，包含：

- **数据概览**：热门项目数、总星标、主要语言数、热门话题数
- **热门话题标签**：按出现频次排列
- **语言分布**：Top 5 编程语言占比
- **本周 Top 10 精选**：可点击查看详情
- **本周洞察**：固定的趋势分析文案（AI Agent / 安全工具 / 教育资源 / 终端工具）

### 3. 语言筛选

支持按以下语言快速过滤每日热门：

`全部` / `TypeScript` / `Python` / `Rust` / `Go` / `JavaScript`

### 4. 项目详情弹窗

点击「星标趋势」按钮后弹出：

- 实时从 GitHub API 拉取最新项目元数据（stars / forks / watchers / issues / topics）
- 嵌入 [star-history.com](https://star-history.com) 渲染星标增长曲线图
- 提供「访问仓库」和「官网」直达链接

### 5. 手动刷新

- 点击「手动更新数据」按钮重新请求 GitHub API
- API 调用失败时自动降级使用内置的静态备用数据（24 个知名项目）
- 右下角 Toast 提示更新结果

### 6. 统计栏

页面顶部展示三项实时统计：

| 指标 | 说明 |
|------|------|
| 收录项目 | 当前展示的项目总数 |
| 总星标数 | 所有项目星标数之和 |
| 最后更新 | 上次成功获取数据的时间 |

### 7. 键盘快捷键

| 快捷键 | 功能 |
|--------|------|
| `Ctrl + 1` | 切换到每日热门 |
| `Ctrl + 2` | 切换到每周精选 |
| `Ctrl + R` | 手动刷新数据 |
| `Esc` | 关闭项目详情弹窗 |

---

## 技术实现

### 技术栈

| 层级 | 技术 |
|------|------|
| 结构 | HTML5 |
| 样式 | 纯 CSS（CSS 变量 + Flexbox + Grid） |
| 逻辑 | 原生 JavaScript（ES6+，无框架） |
| 图标 | Font Awesome 6.5 |
| 字体 | Inter + JetBrains Mono（Google Fonts） |

### 外部依赖

| 依赖 | 用途 | 是否必须 |
|------|------|---------|
| GitHub Search API | 获取热门项目列表 | 核心功能 |
| GitHub Repos API | 获取项目详情 | 弹窗功能 |
| star-history.com API | 渲染星标趋势图 | 弹窗功能 |
| Google Fonts CDN | Inter / JetBrains Mono 字体 | 仅影响外观 |
| Font Awesome CDN | 图标库 | 仅影响外观 |

### GitHub API 限制

| 场景 | 限制 |
|------|------|
| 未认证请求 | 60 次 / 小时（按 IP） |
| 认证请求（加 Token） | 5000 次 / 小时 |

> 高访问量场景需在请求头中加入 `Authorization: token <YOUR_TOKEN>` 或做服务端缓存代理。

### 项目解读生成逻辑

`generateSummary()` 函数根据项目描述和 topics 的关键词匹配，从预设模板中选取对应的「作者做了什么 / 方便干什么 / 应用场景」文案，覆盖以下领域：

- AI / Agent / LLM
- 终端 / CLI / Shell
- 安全 / 扫描
- API 网关
- 学习路线 / 教育
- 设计资源 / UI
- Markdown / 文档
- 金融交易
- 聊天机器人 / 微信
- 系统设计 / 架构
- 通用兜底

---

## 目录结构

```
opc_news/
├── index.html        # 完整单文件应用（HTML + CSS + JS 内联）
└── doc/
    └── README.md     # 本说明文档
```

---

## 部署指南

### 方案一：本地预览

直接用浏览器打开 `index.html` 即可，无需任何环境配置。

### 方案二：GitHub Pages（免费）

1. 在 GitHub 创建新仓库
2. 将 `index.html` 推送到 `main` 分支根目录
3. 进入仓库 Settings → Pages → Source 选择 `main` 分支
4. 访问 `https://<用户名>.github.io/<仓库名>`

### 方案三：Vercel（免费，推荐）

1. 注册 [Vercel](https://vercel.com) 账号
2. 点击「New Project」→ 导入 GitHub 仓库，或直接拖拽文件夹
3. 无需任何配置，自动部署，获得 `*.vercel.app` 域名

### 方案四：Netlify（免费）

1. 注册 [Netlify](https://netlify.com) 账号
2. 将 `index.html` 所在文件夹拖拽到 Netlify 控制台
3. 自动部署，获得 `*.netlify.app` 域名

### 方案五：Nginx 自托管

```nginx
server {
    listen 80;
    server_name your-domain.com;
    root /var/www/opc_news;
    index index.html;
}
```

---

## 扩展建议

| 方向 | 实现思路 |
|------|---------|
| 增加 GitHub Token | 在 `fetch` 请求头加入 Token，解除 60次/小时限制 |
| 服务端缓存 | 用 Node.js / Python 定时爬取 GitHub API，缓存 JSON 供前端直接读取 |
| 更多语言筛选 | 在 `filter-tabs` HTML 中添加新的 `filter-tab` 按钮 |
| 自定义项目解读 | 对接真实 AI API（如 Claude / GPT）替换 `generateSummary()` 的模板逻辑 |
| 数据持久化 | 将每日数据写入 localStorage，支持离线浏览历史记录 |
| 邮件订阅 | 接入 Resend / SendGrid，每日将 Top10 发送到邮箱 |
