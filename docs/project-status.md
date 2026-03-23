# OmniVideo Downloader - 项目现状文档

> 最后更新: 2026-03-23  
> **运维/规则速查**：见 [docs/product-and-operations.md](./product-and-operations.md) · [文档索引](./README.md)

---

## 一、项目概述

多平台视频下载工具 + AI 视频处理平台。用户输入视频 URL，系统解析、下载、AI 分析。

- **前端**: Vue 3 + Vite + Vue Router + Naive UI + TailwindCSS（SPA）
- **后端**: Python 3.13 + FastAPI + yt-dlp + OpenAI (DeepSeek)
- **数据库**: MySQL + SQLAlchemy async（aiomysql）
- **缓存**: Redis（解析/下载/字幕缓存 + 任务状态）
- **认证**: PyJWT + pwdlib(bcrypt) + Google OAuth
- **AI**: DeepSeek API（`api.deepseek.com`，兼容 OpenAI 协议）

---

## 二、目录结构

```
omni-video-downloader/
├── backend/
│   ├── main.py                          # FastAPI 应用入口
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── .env                             # 环境变量（不入库）
│   ├── venv/                            # Python 虚拟环境
│   └── app/
│       ├── api/
│       │   ├── video.py                 # 视频解析/下载 API（含异步任务）
│       │   ├── ai.py                    # AI 分析 API（字幕/总结/导图/问答/翻译）
│       │   ├── auth.py                  # 注册/登录/JWT/Google
│       │   ├── history.py               # 用户下载历史（需登录）
│       │   ├── admin.py                 # 管理员 API（用户管理/统计）
│       │   └── pay.py                   # VIP 下单 / 支付回调 / 订单查询
│       ├── core/
│       │   ├── config.py                # pydantic-settings（JWT、TASK_MODE、匿名 AI 限次、支付参数等）
│       │   ├── redis.py                 # Redis 异步连接管理
│       │   ├── logging.py               # 日志配置
│       │   ├── database.py              # SQLAlchemy async 引擎 + get_db
│       │   ├── security.py              # JWT、pwdlib 密码哈希
│       │   ├── permissions.py           # VIP / AI 配额依赖（已挂载到 AI 路由）
│       │   └── task_dispatcher.py       # 双模式任务调度器（local/queue，传递 user_id）
│       ├── schemas/
│       │   ├── video.py                 # 视频相关 Pydantic 模型
│       │   ├── ai.py                    # AI 相关 Pydantic 模型
│       │   ├── auth.py / history.py     # 认证与下载历史
│       ├── services/
│       │   ├── video_service.py         # 视频解析/下载核心逻辑
│       │   ├── bilibili_service.py      # B 站专用解析/下载
│       │   ├── douyin_service.py        # 抖音专用解析/下载
│       │   ├── subtitle_service.py      # 字幕/弹幕提取 + AI 上下文构建
│       │   ├── ai_service.py            # AI 总结/思维导图/问答/翻译
│       │   ├── auth_service.py          # 注册登录、Google 用户合并
│       │   ├── task_service.py          # Redis 异步下载任务与进度（含重试 + user_id 传递）
│       │   └── persist_service.py       # 数据持久化工具（upsert_video / record_download_history / record_ai_task）
│       └── models/                      # User、Video、DownloadHistory（统一表）、AITask
├── frontend/
│   ├── package.json
│   ├── vite.config.ts                   # Vite 配置，/api 代理到 localhost:8000
│   └── src/
│       ├── App.vue                      # 根组件（导航栏 + 登录态 + Home）
│       ├── main.ts
│       ├── router.ts                    # 路由：/ /history /admin /pricing /guide
│       ├── style.css                    # CSS 变量 + TailwindCSS
│       ├── api/
│       │   ├── video.ts                 # 视频 API 客户端
│       │   ├── ai.ts                    # AI API（SSE 问答、额度、usage-rules、quota-status）
│       │   ├── auth.ts                  # 认证 + 下载历史（Bearer）
│       │   ├── pay.ts                   # VIP 定价与支付
│       │   └── admin.ts                 # 管理端
│       ├── composables/
│       │   └── useAuth.ts               # 全局登录态、localStorage token
│       ├── pages/
│       │   ├── Home.vue                 # 首页（解析 + 下载 + AI）
│       │   ├── HistoryPage.vue          # 下载记录
│       │   ├── AdminPage.vue            # 管理后台
│       │   ├── PricingPage.vue          # VIP 定价与支付
│       │   └── GuidePage.vue            # 使用说明
│       └── components/
│           ├── VideoResult.vue          # 视频信息卡片 + 清晰度选择 + 下载按钮
│           ├── LoginModal.vue           # 登录/注册 + Google GIS 按钮
│           ├── VipModal.vue             # 开通 VIP / 扫码支付
│           ├── AIPanel.vue              # AI 分析面板（Tab + 额度提示）
│           └── ai/
│               ├── SummaryView.vue      # 总结摘要 Tab
│               ├── SubtitleView.vue     # 字幕文本 Tab
│               ├── MindMapView.vue      # 思维导图 Tab（markmap 渲染）
│               └── QAView.vue           # AI 问答 Tab（SSE 流式聊天）
├── docker/
│   └── docker-compose.yml
└── docs/
    ├── README.md                        # 文档索引
    ├── product-and-operations.md        # 产品规则与运维速查
    └── project-status.md                # 本文档
```

---

## 三、后端 API 清单

### 视频相关

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/video/parse` | 解析视频信息（标题/封面/清晰度列表） |
| POST | `/api/video/download` | 创建异步下载任务，返回 `task_id`；完成后得直链或文件 URL |
| GET  | `/api/video/task/{task_id}` | 轮询下载任务状态与进度 |
| GET  | `/api/video/proxy/image?url=` | 图片代理（解决 B 站防盗链） |
| GET  | `/api/video/file/{disk_name}` | 提供已下载的文件 |
| GET  | `/api/health` | 健康检查 |

### AI 相关

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/ai/subtitle` | 提取字幕/弹幕 |
| POST | `/api/ai/summary` | AI 生成总结（可传 text 或让后端自动获取） |
| POST | `/api/ai/mindmap` | AI 生成思维导图 Markdown |
| POST | `/api/ai/chat` | AI 问答（SSE 流式响应） |
| POST | `/api/ai/translate` | 字幕批量翻译（DeepSeek + Redis 缓存） |
| GET  | `/api/ai/usage-rules` | 公开：匿名/注册默认额度等配置（给使用说明页） |
| GET  | `/api/ai/quota-status` | 当前请求的 AI 额度快照（可选登录；访客依赖 Redis） |

### 认证与用户（P1）

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/auth/register` | 手机号 + 密码注册，返回 JWT + 用户信息 |
| POST | `/api/auth/login` | 手机号 + 密码登录 |
| POST | `/api/auth/google` | Body: `{ "id_token": "..." }`，google-auth 校验后与 `google_id` 绑定/注册 |
| GET  | `/api/auth/me` | 当前用户（Header: `Authorization: Bearer <token>`） |
| POST | `/api/user/downloads` | 记录一条下载历史（需登录） |
| GET  | `/api/user/downloads` | 分页查询当前用户下载历史（需登录，下载完成自动记录） |

### 管理员

| 方法 | 路径 | 说明 |
|------|------|------|
| GET  | `/api/admin/users` | 分页用户列表 + 搜索（需管理员） |
| PUT  | `/api/admin/users/{id}` | 编辑用户 VIP/配额/管理员权限（需管理员） |
| GET  | `/api/admin/stats` | 系统统计（用户数/VIP/今日下载/今日AI调用）（需管理员） |

### 支付（VIP）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/pay/plans` | 可售套餐列表 |
| POST | `/api/pay/create` | 创建订单，返回扫码支付信息 |
| GET | `/api/pay/status/{order_no}` | 订单支付状态（前端轮询） |
| POST | `/api/pay/notify/wechat` | 微信支付异步通知 |
| POST | `/api/pay/notify/alipay` | 支付宝异步通知 |

**Google 登录配置**：后端 `.env` 设置 `GOOGLE_CLIENT_ID`（与 Google Cloud「网页应用」Client ID 一致）；前端 `index.html` 引入 GIS 脚本，`LoginModal.vue` 内 `google.accounts.id.initialize` + `renderButton`。Cloud Console「已授权的 JavaScript 来源」需包含前端域名（如 `http://localhost:5173`）。**修改 `.env` 后须重启 uvicorn**，否则会出现 `Token has wrong audience ... expected one of ['']`。

---

## 四、支持平台与下载策略

| 平台 | 解析方式 | 下载方式 | 字幕获取 |
|------|----------|----------|----------|
| YouTube | yt-dlp | 服务器下载 | json3 优先 + yt-dlp 降级（见第十四节） |
| Bilibili | 自研 API（`bilibili_service.py`） | 自研 API 下载 | dm/view API 免登录获取 CC 字幕；弹幕降级 |
| 抖音 | 自研 API（`douyin_service.py`） | 自研 API 下载 | 暂不支持 |
| TikTok | yt-dlp | 服务器下载 | yt-dlp |
| Twitter/X | yt-dlp | 服务器下载 | yt-dlp |
| Instagram | yt-dlp | 服务器下载 | yt-dlp |

**平台识别**: `video_service.py` 的 `detect_platform()` 通过 URL hostname 匹配 `PLATFORM_MAP`。

---

## 五、B 站字幕/弹幕获取机制（重要）

这是最复杂的部分，三级降级策略：

### 1. CC 字幕（`_extract_bilibili_subtitles`）

**优先方案（免登录）**: 使用 `/x/v2/dm/view` API

```
GET https://api.bilibili.com/x/v2/dm/view?aid={aid}&oid={cid}&type=1
→ data.subtitle.subtitles[].subtitle_url  (含 auth_key，可直接访问)
→ 字幕 JSON 格式: body[].{from, to, content}
```

**备选方案（需 Cookie）**: 使用 `/x/player/v2` API + `BILIBILI_COOKIE`

**关键发现**: `/x/player/v2` 强制要求 SESSDATA Cookie 才返回字幕。而 `/x/v2/dm/view`（弹幕视图 API）会附带字幕 URL 且无需登录。这是一个未被广泛记录的免登录字幕获取方案。

### 2. 弹幕降级（`_extract_bilibili_danmaku`）

```
GET https://api.bilibili.com/x/v1/dm/list.so?oid={cid}
→ XML 格式，<d p="时间戳,...">弹幕文本</d>
```

### 3. 元信息降级（`get_video_context`）

若字幕和弹幕都为空，从视频标题/简介/标签构建上下文。

### 字幕提取总流程（`extract_subtitles`）

```
Bilibili:
  1. _extract_bilibili_subtitles() → CC 字幕 (source: "cc")
  2. _extract_bilibili_danmaku()   → 弹幕   (source: "danmaku")

其他平台:
  _extract_ytdlp_subtitles()       → CC 字幕 (source: "cc")
```

### AI 上下文获取流程（`get_video_context`）

前端 AIPanel 先调用 `/ai/subtitle` 获取字幕：
- 若有内容 → 直接传 text 给 `/ai/summary` 和 `/ai/mindmap`
- 若为空 → 不传 text，后端自动调用 `get_video_context()` 走降级链

---

## 六、B 站 API 端点参考

| API | 用途 | 需登录 |
|-----|------|--------|
| `/x/web-interface/view?bvid=` | 视频基本信息（aid/cid/title/desc） | 否 |
| `/x/player/playurl?bvid=&cid=&qn=` | 视频流地址 | 否（高清需 Cookie） |
| `/x/player/v2?bvid=&cid=` | 播放器信息（含字幕列表） | **是（字幕需 SESSDATA）** |
| `/x/v2/dm/view?aid=&oid=&type=1` | 弹幕视图（含字幕列表） | **否** |
| `/x/v1/dm/list.so?oid=` | 弹幕 XML | 否 |
| `/x/tag/archive/tags?bvid=` | 视频标签 | 否 |

### BV 号提取

```python
re.search(r"(BV[\w]+)", url)  # 从 URL 中提取 BV 号
```

---

## 七、AI 服务架构

### 配置

```env
OPENAI_API_BASE=https://api.deepseek.com
OPENAI_API_KEY=sk-xxx
OPENAI_MODEL=deepseek-chat
```

使用 OpenAI SDK 连接 DeepSeek API（兼容接口）。

### 功能

| 功能 | 函数 | Prompt 策略 |
|------|------|-------------|
| 总结 | `generate_summary()` | 区分字幕源/元信息源两套 Prompt，返回 JSON `{summary, keypoints, timeline}` |
| 思维导图 | `generate_mindmap()` | 区分字幕源/元信息源两套 Prompt，返回 Markdown 大纲 |
| 问答 | `stream_chat()` | SSE 流式输出，保留最近 10 轮对话历史 |

文本截断: summary/mindmap 截取前 12000 字符，chat 截取前 10000。

---

## 八、前端关键组件

### AIPanel.vue（AI 面板容器）

数据流:
1. `onMounted` / `watch(url)` → 调用 `runAnalysis()`
2. 先 `fetchSubtitles(url)` 获取字幕
3. 并行调用 `fetchSummary` + `fetchMindMap`（有字幕传 text，无字幕不传让后端降级）
4. 各 Tab 独立 loading/error 状态

### MindMapView.vue（思维导图）

- 使用 `markmap-lib`（解析 Markdown）+ `markmap-view`（SVG 渲染）+ `markmap-common`（资源加载）
- `onMounted` + `watch(markdown)` 双重触发渲染（因 NTabPane 懒加载，组件挂载时数据可能已就绪）
- 渲染后调用 `markmapInstance.fit()` 确保自适应

### QAView.vue（AI 问答）

- 使用 `fetch` API 读取 SSE 流
- 支持快捷问题按钮
- 保持对话历史

---

## 九、缓存策略

| 缓存 Key 模式 | TTL | 说明 |
|---------------|-----|------|
| `parse:{url_hash}` | 1 小时 | 视频解析结果 |
| `dl:{url_hash}:{format}` | DOWNLOAD_CACHE_HOURS（默认 3h） | 下载文件路径 |
| `subtitle:{url_hash}` | 6 小时 | 字幕/弹幕提取结果 |
| `ai_context:{url_hash}` | 6 小时 | AI 上下文（字幕+弹幕+元信息） |

**注意**: 开发时如果修改了字幕逻辑需要验证效果，需要手动清除 Redis 缓存:
```bash
redis-cli DEL "subtitle:{hash}" "ai_context:{hash}"
```

---

## 十、环境变量（.env）

```env
DATABASE_URL=mysql+aiomysql://omni:omni123@localhost:3306/omni_video
REDIS_URL=redis://localhost:6379/0
DOWNLOAD_DIR=./downloads
DOWNLOAD_CACHE_HOURS=3
CORS_ORIGINS=["http://localhost:5173","http://localhost"]
BILIBILI_COOKIE=                  # 可选，大多数情况下不需要（dm/view API 免登录）
YOUTUBE_COOKIES_FILE=             # 可选，Netscape 格式 cookies.txt 路径（缓解 YouTube 429）
JWT_SECRET=change-me-to-a-random-hex-string
JWT_EXPIRE_MINUTES=10080          # 7 天
GOOGLE_CLIENT_ID=                 # Google OAuth 客户端 ID
TASK_MODE=local                   # 任务调度模式：local（开发）/ queue（生产 RQ）
ANON_AI_DAILY_LIMIT=5             # 访客每日 LLM 次数（UTC 日、按 IP）
REGISTER_DEFAULT_AI_QUOTA=5       # 与注册默认 ai_quota 说明一致（可选）
OPENAI_API_BASE=https://api.deepseek.com
OPENAI_API_KEY=sk-xxx             # 必填，DeepSeek API Key
OPENAI_MODEL=deepseek-chat
# 微信支付 / 支付宝 / VIP 定价等见 config.py 与部署环境，勿提交密钥
```

---

## 十一、本地开发启动

```bash
# 1. 后端
cd backend
source venv/bin/activate      # 或直接用 venv/bin/python
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# 2. 前端
cd frontend
npm run dev                   # Vite 开发服务器 http://localhost:5173
                              # /api 自动代理到 localhost:8000

# 3. 依赖服务
# Redis 需要在本地运行（默认 localhost:6379）
# MySQL 远程库（配置 DATABASE_URL）
```

---

## 十二、设计文档完成度对照

> 对照 `omni_video_downloader_design.md` 原始规划

### 已完成

| 设计模块 | 完成状态 | 说明 |
|----------|----------|------|
| URL 解析（6 平台） | ✅ | YouTube/Bilibili/抖音/TikTok/Twitter/Instagram |
| 视频下载 | ✅ | 服务器下载模式，缓存 3h |
| 基础 UI | ✅ | Vue3 + Naive UI + TailwindCSS 工具站风格 |
| AI 视频总结 | ✅ | DeepSeek API，返回 summary/keypoints/timeline |
| AI 思维导图 | ✅ | Markdown → markmap 渲染 |
| AI 问答 | ✅ | SSE 流式聊天 |
| 字幕提取 | ✅ | YouTube json3 + B 站 dm/view API + 弹幕降级 |
| Redis 缓存 | ✅ | 解析/下载/字幕/AI 上下文 |
| Docker 基础 | ✅ | backend Dockerfile + docker-compose（backend + redis） |

### 未完成（与设计文档对齐的具体工作项）

| 功能项 | 要做的事（设计文档中的目标） | 当前状态 |
|--------|------------------------------|----------|
| **用户系统** | 账号体系：`users` 表、注册/登录、签发 JWT；`GET /api/auth/me` 返回当前用户与 VIP 字段 | ✅ 已实现（PyJWT + pwdlib/bcrypt） |
| **登录方式（已定）** | **手机号 + 密码**；**Google**：GIS 前端取 `id_token`，`POST /api/auth/google` 校验并绑定 `google_id` / `google_email`；微信 Tab 仍为占位 | ✅ 手机号+Google 已通；短信/微信后续 |
| **会员/VIP** | `is_vip`、`vip_expire_at`、`ai_quota`；`require_vip` / `check_ai_quota` 供后续挂到业务路由 | ✅ 已挂载到 LLM AI 路由；**访客**按 IP + UTC 日限次（`ANON_AI_DAILY_LIMIT`，Redis）；登录用户扣 `ai_quota`；VIP 不限；`/guide` 使用说明页 + `GET /api/ai/usage-rules` |
| **下载记录** | 独立表 `download_history` + `POST/GET /api/user/downloads`（登录后前端可记一条） | ✅ 已实现；下载完成后自动写入 `downloads` 表 |
| **视频解析历史** | `videos` 表（`sql/init.sql` 含 `url_hash` 去重） | ✅ 已实现；`/api/video/parse` 自动 upsert 写入 |
| **AI 任务记录** | `ai_tasks` 表 | ✅ 已实现；summary/mindmap/translate/chat 均自动写入 |
| **数据库** | MySQL + SQLAlchemy async + 启动 `create_all` + `backend/sql/init.sql` | ✅ 已启用 |
| **Chrome 浏览器插件** | Manifest V3：`extension/` 下 popup + content script，检测当前页 URL → 调 `POST /api/video/parse` → 展示下载入口 | 未开发 |
| **智能下载策略** | **直链**：对 YouTube/Twitter/Instagram 等返回可 `yt-dlp -g` 的真实地址，浏览器直拉；**服务器下载**：Bilibili/抖音 等保持服务端拉流 + 缓存（`DOWNLOAD_CACHE_HOURS`） | ✅ 已实现：直链优先 + 服务器回退 |
| **AI 字幕翻译** | 在已有字幕上调用大模型翻译或独立翻译接口；前端增加 Tab/按钮 | ✅ 已实现：翻译API + 7种语言 + 双语对照 |
| **Whisper 语音转文字** | 无字幕时：抽音频 → Whisper 转写 → 再走总结/导图（设计文档里 AI 总结流程中的兜底） | 未实现（调研见第十五节） |
| **批量下载** | 多 URL 输入、并发或队列任务（依赖下载任务队列） | 未实现 |
| **播放列表下载** | yt-dlp 解析 playlist，前端展示多集勾选再下载 | 未实现 |
| **下载任务队列** | Redis 队列 + worker，异步下载、进度、失败重试 | ✅ 已实现：双模式调度器（local/queue）+ 重试逻辑 + 自动持久化 |
| **完整 Docker 部署** | `docker-compose`：nginx（反向代理 + 静态前端）、frontend 镜像、MySQL、Redis、backend | 仅有 backend + redis |
| **响应式/移动端** | 工具站布局在小屏可点可用（设计文档「响应式、支持移动端」） | 未专门适配 |
| **API 对外服务** | 开放 API Key、按量计费、限流 （设计文档「未来扩展」） | 未实现 |
| **企业版** | 私有化交付、批量接口、SLA（设计文档「未来扩展」） | 未实现 |
| **付费计费系统** | VIP 订阅（微信/支付宝扫码、回调、订单轮询） | ✅ 已实现；细节见 [product-and-operations.md](./product-and-operations.md) · `app/api/pay.py` |

---

## 十二-A、后续开发计划（优先级排序）

### P0 — 核心体验完善（近期）

当前产品已能下载和 AI 分析，但以下功能对用户体验有直接提升：

| # | 功能 | 工作量 | 说明 |
|---|------|--------|------|
| 1 | AI 字幕翻译 | 中 | 已有字幕文本 + DeepSeek API，新增翻译 Prompt 即可；前端增加翻译 Tab/按钮 |
| 2 | 智能下载策略 | 小 | YouTube/Twitter/Instagram 支持直链下载，减少服务器带宽；B 站/抖音保持服务器下载 |
| 3 | 下载任务队列 | 中 | 当前同步下载阻塞请求；引入 Redis 队列 + 后台 worker，支持进度回报 |

### P1 — 用户体系（中期） ✅ 已完成

产品走向可运营需要用户体系支撑：

| # | 功能 | 工作量 | 状态 | 说明 |
|---|------|--------|------|------|
| 4 | 数据库正式接入 | 中 | ✅ 已实现 | MySQL 远程库 + SQLAlchemy async + 应用启动自动建表 + `sql/init.sql` |
| 5 | 手机号注册/登录 | 中 | ✅ 已实现 | 手机号+密码；PyJWT + pwdlib(bcrypt)；前端登录弹窗完整对接 |
| 6 | Google 登录 | 小 | ✅ 已实现 | GIS 前端 `renderButton` + `POST /api/auth/google`；`.env` 配置 `GOOGLE_CLIENT_ID`；改 env 后需重启后端 |
| 7 | 下载记录/历史 | 小 | ✅ 已实现 | `download_history` 表 + `POST/GET /api/user/downloads` |
| 8 | 会员/VIP 系统 | 中 | ✅ 已实现 | User 模型含 `is_vip`/`vip_expire_at`/`ai_quota`；`require_vip`/`check_ai_quota` 依赖 |

#### P1 验收摘要（2026-03-21）

- **数据库**：`backend/sql/init.sql` 初始化远程 MySQL；应用启动 `Base.metadata.create_all` 与现有表对齐。
- **手机号**：注册/登录、`/api/auth/me`、前端 `LoginModal` + `useAuth` + Token 存 `localStorage`。
- **Google**：OAuth Client ID 写入 `.env`；`index.html` 加载 `accounts.google.com/gsi/client`；弹窗内 GIS 按钮； audience 报错多为 **`GOOGLE_CLIENT_ID` 空且未重启后端**。
- **下载历史**：已登录可 `POST/GET /api/user/downloads`；**首页下载成功后自动写入历史**可在后续迭代对接（当前需前端显式调用）。
- **VIP**：字段与权限依赖已具备；**高清/AI 限次等业务挂载**为后续迭代。
- **仍属 P1 延伸（未在表中单独成行）**：短信验证码；微信登录。

#### P1.5 架构升级验收（2026-03-22）

本次升级完成三个关键模块：任务调度抽象、数据持久化、VIP 权限挂载。

**一、任务调度器 (`task_dispatcher.py`)**

| 项目 | 说明 |
|------|------|
| 双模式架构 | `TASK_MODE=local`（asyncio.to_thread，开发用）/ `TASK_MODE=queue`（RQ worker，生产用） |
| 重试机制 | `_MAX_RETRIES=2`，覆盖 `ConnectionError / TimeoutError / OSError`，退避间隔 3s/6s |
| 入口隔离 | 本地模式调 `create_download_task()`；RQ 模式调 `blocking_download_job()` |

**二、数据持久化 (`persist_service.py`)**

| 数据 | 写入时机 | 去重方式 |
|------|----------|----------|
| `videos` | 视频解析（`/api/video/parse`） | `url_hash`（MD5 前 12 位）唯一索引 |
| `downloads` | 下载任务完成后 (`_persist_download`) | 无去重（每次下载一条记录） |
| `ai_tasks` | AI 端点（summary/mindmap/translate/chat）调用后 | 无去重（每次调用一条） |

ORM 模型字段对齐：
- `Video`：新增 `url_hash`
- `Download`：新增 `user_id`、`resolution`、`method`；`format` → `format_id`
- `AITask`：新建表

**三、VIP 权限挂载**

| 场景 | 行为 |
|------|------|
| 匿名用户调用 AI | 正常通过，不消耗配额 |
| 登录用户（有配额） | 正常通过，`ai_quota -= 1` |
| 登录用户（配额=0） | 返回 HTTP 403 + `"今日免费 AI 次数已用完，升级 VIP 无限使用"` |
| VIP 用户 | 无限使用，不消耗配额 |
| 前端 403 处理 | 捕获 `QuotaExhaustedError` → 显示升级 VIP 提示条 |

**四、自动化测试报告（2026-03-22 19:55 CST）**

共 7 组、24 项测试，全部通过。

| 测试组 | 子项数 | 结果 | 说明 |
|--------|--------|------|------|
| Test 1: 模块加载 | 8 | ✅ 全通过 | config/dispatcher/permissions/models/persist/task/app/ORM 注册 |
| Test 2: DB Schema | 4 | ✅ 全通过 | `videos`(8列) / `downloads`(9列) / `ai_tasks`(7列) / `users`(12列) |
| Test 3: 视频解析+持久化 | 3 | ✅ 全通过 | POST parse → DB 写入 → upsert 去重 |
| Test 4: 下载调度+重试 | 5 | ✅ 全通过 | local 模式 → task_id → 轮询 done → DB 记录 → 重试常量 |
| Test 5: AI+任务持久化 | 3 | ✅ 全通过 | 匿名字幕 → 匿名总结 → ai_tasks 写入 |
| Test 6: VIP 配额 | 5 | ✅ 全通过 | 获取 token → 有配额正常 → 配额-1 → 配额=0 返 403 → 匿名仍可用 |
| Test 7: 前端编译 | 1 | ✅ 全通过 | `vue-tsc --noEmit` 零错误 |

**测试用例明细：**

```
TEST 1: Module Imports & App Loading
[PASS] config.py: TASK_MODE=local loaded
[PASS] task_dispatcher.py: imported OK
[PASS] permissions.py: check_ai_quota(user, db) signature correct
[PASS] Video model: columns=[id, url, url_hash, platform, title, duration, thumbnail, created_at]
[PASS] Download model: columns=[id, user_id, video_id, format_id, resolution, method, status, file_path, created_at]
[PASS] AITask model: columns=[id, user_id, video_id, task_type, status, result_snapshot, created_at]
[PASS] persist_service.py: all functions imported
[PASS] task_service.py: retry config OK (max=2, errors=[ConnectionError, TimeoutError, OSError])
[PASS] main.py: App loaded, 21 routes registered
[PASS] ORM registration: [ai_tasks, download_history, downloads, users, videos]

TEST 2: Database Table Schemas
[PASS] videos: all 8 columns present
[PASS] downloads: all 9 columns present
[PASS] ai_tasks: all 7 columns present
[PASS] users: all 12 columns present

TEST 3: Video Parse + DB Persistence
[PASS] POST /api/video/parse — status=200, title=Rick Astley - Never Gonna Give You Up
[PASS] Video persisted in DB — id=1, hash=75170fc230cd, platform=youtube
[PASS] Upsert dedup (no duplicate) — count=1

TEST 4: Download Task Dispatcher + Retry
[PASS] TASK_MODE=local — actual=local
[PASS] POST /api/video/download — task_id=83092d73ef78
[PASS] Task completed — status=done, method=direct
[PASS] Download persisted in DB — id=1, method=direct, status=done
[PASS] Retry constants — max=2, errors=[ConnectionError, TimeoutError, OSError]

TEST 5: AI Endpoints + Task Persistence
[PASS] POST /ai/subtitle (anon) — source=cc, lines=61
[PASS] POST /ai/summary (anon) — has_summary=True
[PASS] AI tasks in DB — 1 task(s): [(summary, done)]

TEST 6: VIP Quota Enforcement
[PASS] Get auth token — user_id=7, quota=5
[PASS] AI call (quota=2) — status=200
[PASS] Quota decremented — expected=1, actual=1
[PASS] Quota=0 → 403 — detail=今日免费 AI 次数已用完，升级 VIP 无限使用
[PASS] Anon still works — status=200

TEST 7: Frontend TypeScript Compilation
[PASS] vue-tsc --noEmit — exit code 0
```

#### P1.6 表合并 + 下载历史 + 管理员后台验收（2026-03-23）

本次修复 6 个问题并新增管理员功能。

**一、表结构合并（`downloads` → `download_history`）**

废弃 `downloads` 表，将 `download_history` 升级为统一下载记录表：
- 新增字段：`video_id`（FK videos）、`status`、`file_path`
- `user_id` 改为 nullable（支持匿名追踪）
- 一张表同时服务"用户看历史"和"系统追踪"

**二、下载历史自动记录**

| 改动文件 | 说明 |
|----------|------|
| `task_dispatcher.py` | `dispatch_download(url, format_id, user_id)` 新增第三参数 |
| `task_service.py` | user_id 从 API 层穿透到 `_run_task` → `_persist_download_history` |
| `persist_service.py` | `record_download_history()` 写入包含标题/缩略图/平台的完整记录 |
| `api/video.py` | `api_download_video` 传递 `user.id if user else None` |

**三、下载历史前端页面**

- 新建 `DownloadHistory.vue`：弹窗式下载历史列表（缩略图、标题、平台、时间、分页）
- 入口：用户下拉菜单 → "下载记录"

**四、ai_tasks user_id 修复**

- `get_optional_user` 增加 warning 日志（token 存在但解析失败时记录）
- 验证确认：登录用户调用 AI 后，`ai_tasks.user_id` 正确写入

**五、管理员后台**

| API | 说明 |
|-----|------|
| `GET /api/admin/users` | 分页用户列表 + 手机号/昵称/邮箱搜索 |
| `PUT /api/admin/users/{id}` | 编辑 VIP/配额/管理员权限 |
| `GET /api/admin/stats` | 统计：总用户/VIP数/今日下载/今日AI调用/AI类型分布 |

- User 模型新增 `is_admin` 字段
- `require_admin` 依赖：非管理员返回 403
- 前端 `AdminPanel.vue`：统计卡片 + 用户表格（VIP 开关、配额编辑）+ 搜索
- 入口：用户下拉菜单 → "管理后台"（仅管理员可见）

**六、自动化测试报告（2026-03-23 09:42 CST）**

共 6 组、17 项测试，全部通过。

```
TEST 1: Login + Profile
[PASS] Auth: get token — user_id=7
[PASS] UserProfile has is_admin — is_admin=False

TEST 2: Video Parse
[PASS] Parse video — title=Rick Astley - Never Gonna Give You Up

TEST 3: Download → auto write download_history
[PASS] Create download task (with auth) — task_id=8a69739c427e
[PASS] Download completed — status=done, method=direct
[PASS] download_history written with user_id — id=4, user_id=7, video_id=1

TEST 4: Download History API
[PASS] GET /user/downloads — total=1, items=1
[PASS] History item has title+platform — platform=youtube

TEST 5: AI summary → ai_tasks has user_id
[PASS] AI summary with auth — status=200
[PASS] ai_tasks has user_id — id=8, user_id=7, type=summary

TEST 6: Admin API
[PASS] Admin login, is_admin in profile — is_admin=True
[PASS] GET /admin/stats — users=7, today_dl=1
[PASS] GET /admin/users — total=7
[PASS] PUT /admin/users (set quota) — status=200
[PASS] Quota updated in DB — ai_quota=99
[PASS] Non-admin → 403 — status=403
[PASS] Search by phone — found=1
```

### P2 — 扩展功能（中后期）

提升产品竞争力的进阶功能：

| # | 功能 | 工作量 | 说明 |
|---|------|--------|------|
| 9 | Whisper 语音转文字 | 大 | 覆盖所有无字幕视频（抖音等）；需 ffmpeg + Whisper API；详见第十五节 |
| 10 | 批量下载 | 中 | 支持多 URL 同时输入和并发下载，依赖任务队列 |
| 11 | 播放列表下载 | 中 | yt-dlp 已支持 playlist 解析，需前端展示列表选择 UI |
| 12 | Chrome 浏览器插件 | 大 | Manifest V3，检测当前页面 URL → 调用解析 API → 弹窗显示下载；需 Chrome Web Store 发布 |
| 13 | 响应式/移动端适配 | 中 | TailwindCSS 断点适配，移动端交互优化 |

### P3 — 部署与商业化（后期）

| # | 功能 | 工作量 | 说明 |
|---|------|--------|------|
| 14 | 完整 Docker 部署 | 中 | 补充 nginx（反向代理 + 静态资源）、frontend 构建镜像、MySQL 容器 |
| 15 | 付费计费系统 | 大 | 三端支付接入，详见第十六节 |
| 16 | API 对外服务 | 中 | API Key 管理、调用频率控制、用量统计 |
| 17 | 企业版 | 大 | 私有部署方案、批量 API、SLA 保障 |

### 里程碑时间线（建议）

```
当前 ──── P0 核心体验 ──── P1 用户体系 ──── P2 扩展功能 ──── P3 商业化
         ┃                 ┃                 ┃                 ┃
         ┣ 字幕翻译        ┣ MySQL 接入      ┣ Whisper ASR     ┣ Docker 全套
         ┣ 直链下载        ┣ 手机号登录      ┣ 批量下载        ┣ 付费系统
         ┗ 任务队列        ┣ Google OAuth    ┣ 播放列表        ┣ API 服务
                          ┣ 下载记录        ┣ 浏览器插件      ┗ 企业版
                          ┗ VIP 系统        ┗ 移动端适配
```

---

## 十三、历史踩坑记录

### Google 登录 id_token audience

- 报错形如：`Token has wrong audience ... expected one of ['']` → 后端 **`GOOGLE_CLIENT_ID` 为空**（`.env` 未加载或改后未重启 uvicorn）。
- **处理**：在 `backend/.env` 设置与 Google Cloud Console 一致的 Web Client ID，**重启后端**；Console 中「已授权的 JavaScript 来源」需包含前端 origin（如 `http://localhost:5173`）。

### B 站字幕 API

- `/x/player/v2` 接口**必须** SESSDATA Cookie 才返回 `subtitles` 数组，不登录返回空
- `/x/v2/dm/view` 接口（弹幕视图）会在 `data.subtitle.subtitles` 中返回字幕 URL（含 auth_key），**无需登录**
- `/x/web-interface/view` 的 `subtitle.list` 虽然有字幕 ID，但 `subtitle_url` 为空，无法直接使用

### 思维导图渲染

- Naive UI 的 `NTabPane` 默认懒加载，组件在 Tab 激活时才挂载
- `watch` 不会对初始值触发（除非 `immediate: true`）
- 解决方案: `onMounted` 中也调用 `renderMindMap()`，双重保证
- markmap 渲染后需要调用 `fit()` 确保 SVG 内容自适应容器

### 前端 AI 分析流程

- 字幕为空时不能短路退出，否则总结/思维导图也会一起失败
- 正确做法: 字幕为空时仍调用 summary/mindmap API（不传 text），让后端 `get_video_context()` 走弹幕+元信息降级链

### SQLAlchemy `create_all` 不修改已有表

- `Base.metadata.create_all` 只创建新表，不会 ALTER 已有表的列
- ORM 模型新增字段（如 `url_hash`、`user_id`、`resolution`）必须手动执行 `ALTER TABLE` 迁移
- 列重命名（`format` → `format_id`）需要先 RENAME 再 ADD 新列

### 异步线程中的数据库写入

- `_blocking_download` 运行在同步线程，不能直接使用 FastAPI 的 async session
- 解决：线程完成后由 async 包装器 `_run_task` 创建独立的 `async_session()` 写入 DB
- 关键：使用 `from app.core.database import async_session` 而非 `get_db` 依赖

### 多次 `asyncio.run()` 与 SQLAlchemy

- 测试脚本中多次调用 `asyncio.run()` 会创建新的事件循环
- aiomysql 连接绑定到第一个循环，后续循环尝试复用会报 `Task got Future attached to a different loop`
- 解决：测试中使用同步 pymysql 直连验证 DB，避免与应用共享 async engine

---

## 十四、YouTube 字幕获取机制

### 429 限流问题

YouTube 的 `timedtext` API 对不同类型字幕有不同的限流策略：

| 字幕类型 | 示例 | 限流 |
|----------|------|------|
| 手动字幕（manual） | 人工上传的字幕 | **不限流** |
| 自动字幕-原语言（auto） | 视频原始语言的语音识别 | **不限流** |
| 自动翻译字幕（auto-translated） | 机器翻译到其他语言 | **严格限流（429）** |

### 多策略降级方案（`_extract_ytdlp_subtitles`）

```
Strategy 1: json3 格式 URL（主）
  ├── 1) 手动字幕（按语言优先级: zh-Hans > zh > zh-CN > en > ja）
  ├── 2) 自动字幕-原语言
  └── 3) 自动翻译字幕（有重试）

Strategy 2: yt-dlp 文件下载（备）
  └── yt-dlp download() 写入 VTT/SRT 文件 → 读取解析
```

### 关键设计

- **json3 格式**: YouTube 的轻量 JSON 字幕格式，相比 VTT/SRT 下载更可靠
- **候选排序**: `_build_subtitle_candidates()` 按照不限流 → 可能限流的顺序排列
- **end 时间推算**: json3 的手动字幕可能不含 `dDurMs`，用下一条字幕的 start 推算
- **cookies 支持**: 可配置 `YOUTUBE_COOKIES_FILE` 指向 Netscape 格式 cookies.txt 文件

### 配置

```env
YOUTUBE_COOKIES_FILE=           # 可选，Netscape 格式 cookies.txt 路径
```

---

## 十五、待实现：抖音字幕（Whisper ASR）

### 调研结论

- 抖音无公开、免费、免登录的字幕 API
- `yt-dlp` 的抖音 extractor 不提供字幕信息
- 抖音分享页和相关 API 均不包含嵌入式字幕数据

### 推荐方案：OpenAI Whisper 语音转文字

利用项目已有的 AI 能力（OpenAI 兼容 API），对视频音频进行 ASR 处理：

```
1. 下载视频（已有功能）
2. 提取音频轨道（ffmpeg）
3. 调用 Whisper API 进行语音转文字
4. 解析 Whisper 返回的时间戳字幕
5. 缓存结果到 Redis
```

### 技术要点

| 项目 | 说明 |
|------|------|
| API | OpenAI `/v1/audio/transcriptions`（需确认 DeepSeek 是否支持，否则用 OpenAI 官方） |
| 本地方案 | `openai-whisper` Python 包（离线，需 GPU） |
| 音频格式 | mp3/wav，建议使用 ffmpeg 从视频中提取 |
| 文件大小限制 | OpenAI API: 25MB；超限需分段处理 |
| 语言支持 | 自动检测，支持中/英/日等多语言 |
| 适用范围 | 不仅限抖音，可覆盖所有无字幕视频 |

### 实现优先级

此功能计划在最后阶段实现，因为：
1. 需要额外 API 成本（Whisper API 按分钟计费）
2. 需要 ffmpeg 依赖
3. 处理时间较长（音频提取 + 转写）
4. 当前核心功能（下载/字幕/AI 分析）优先完善

---

## 十六、支付系统设计

### 支付渠道

支持三种支付方式，覆盖国内外用户：

| 渠道 | 适用场景 | 接入方式 | 说明 |
|------|----------|----------|------|
| **支付宝** | 国内用户 | 支付宝开放平台 SDK | 扫码支付 + H5 支付；需企业主体申请 |
| **微信支付** | 国内用户 | 微信支付 API v3 | Native 支付（扫码）+ JSAPI/H5；需企业主体 + 微信商户号 |
| **Stripe** | 海外用户 | Stripe API + Checkout | 信用卡/Apple Pay/Google Pay；个人即可申请 |

### 付费产品设计

| 产品类型 | 计费方式 | 说明 |
|----------|----------|------|
| VIP 月卡 | 按月订阅 | 解锁高清下载、AI 分析无限次、批量下载 |
| VIP 年卡 | 按年订阅 | 同月卡权益，折扣价 |
| AI 次数包 | 按次购买 | 非 VIP 用户按次购买 AI 总结/翻译额度 |
| API 调用包 | 按量购买 | 面向开发者的 API 调用额度 |

### 后端架构

```
backend/app/
├── api/
│   └── payment.py              # 支付相关 API
├── services/
│   └── payment_service.py      # 支付核心逻辑
└── models/
    └── order.py                # 订单模型
```

### API 设计

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/payment/create` | 创建支付订单（参数: channel, product_type, amount） |
| POST | `/api/payment/callback/alipay` | 支付宝异步回调 |
| POST | `/api/payment/callback/wechat` | 微信支付异步回调 |
| POST | `/api/payment/callback/stripe` | Stripe Webhook |
| GET  | `/api/payment/status/{order_id}` | 查询订单支付状态 |
| GET  | `/api/user/subscription` | 查询用户当前订阅/额度 |

### 数据库表设计

```sql
CREATE TABLE orders (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id BIGINT NOT NULL,
    order_no VARCHAR(64) UNIQUE NOT NULL,       -- 内部订单号
    channel ENUM('alipay', 'wechat', 'stripe') NOT NULL,
    product_type ENUM('vip_monthly', 'vip_yearly', 'ai_pack', 'api_pack') NOT NULL,
    amount DECIMAL(10, 2) NOT NULL,
    currency VARCHAR(10) DEFAULT 'CNY',
    status ENUM('pending', 'paid', 'failed', 'refunded') DEFAULT 'pending',
    channel_order_no VARCHAR(128),              -- 第三方订单号
    paid_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user (user_id),
    INDEX idx_order_no (order_no),
    INDEX idx_status (status)
);

CREATE TABLE subscriptions (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id BIGINT UNIQUE NOT NULL,
    plan ENUM('free', 'vip_monthly', 'vip_yearly') DEFAULT 'free',
    ai_quota INT DEFAULT 0,                     -- 剩余 AI 次数
    api_quota INT DEFAULT 0,                    -- 剩余 API 调用次数
    expire_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_user (user_id)
);
```

### 支付流程

```
用户选择套餐 → 前端调用 /payment/create → 后端生成订单
    │
    ├─ 支付宝 → 返回支付链接/二维码 → 用户扫码 → 支付宝回调 → 更新订单+权益
    ├─ 微信   → 返回支付二维码     → 用户扫码 → 微信回调   → 更新订单+权益
    └─ Stripe → 返回 Checkout URL  → 用户支付 → Webhook    → 更新订单+权益
```

### 安全要点

- 回调验签：支付宝（RSA2）、微信（HMAC-SHA256）、Stripe（Webhook Secret）
- 订单幂等：通过 `order_no` 唯一索引防止重复处理
- 金额校验：回调中核对金额与订单金额一致
- HTTPS 强制：所有回调地址必须 HTTPS
- 敏感配置：商户密钥、API Key 通过环境变量管理，不入库

### 环境变量

```env
# 支付宝
ALIPAY_APP_ID=                    # 应用 ID
ALIPAY_PRIVATE_KEY=               # 应用私钥（RSA2）
ALIPAY_PUBLIC_KEY=                # 支付宝公钥
ALIPAY_NOTIFY_URL=                # 异步回调地址

# 微信支付
WECHAT_MCH_ID=                    # 商户号
WECHAT_API_KEY_V3=                # API v3 密钥
WECHAT_APP_ID=                    # 公众号/小程序 AppID
WECHAT_NOTIFY_URL=                # 异步回调地址
WECHAT_CERT_PATH=                 # 商户证书路径

# Stripe
STRIPE_SECRET_KEY=                # Stripe 密钥
STRIPE_WEBHOOK_SECRET=            # Webhook 签名密钥
STRIPE_SUCCESS_URL=               # 支付成功跳转
STRIPE_CANCEL_URL=                # 支付取消跳转
```

### 依赖

```
# requirements.txt 新增
python-alipay-sdk>=3.0.0     # 支付宝 SDK
wechatpayv3>=1.2.0           # 微信支付 v3 SDK
```

---

## 支付集成实现报告（2026-03-23）

### 已完成

1. **数据库**: `orders` 表 — 订单号、用户、套餐、金额、支付方式、状态、交易号、二维码链接、支付时间
2. **后端 Model**: `backend/app/models/order.py` (SQLAlchemy ORM)
3. **Config**: `backend/app/core/config.py` 新增微信/支付宝参数 + VIP 定价
4. **支付服务**: `backend/app/services/pay_service.py`
   - 微信 Native 下单 (`create_wechat_native_order`) — 返回 `code_url`
   - 支付宝当面付 (`create_alipay_precreate_order`) — 返回 `qr_code`
   - 微信回调验签 (`verify_wechat_notify`)
   - 支付宝回调验签 (`verify_alipay_notify`)
   - VIP 发放 (`fulfill_order`) — 设置 `is_vip`, 延长 `vip_expire_at`, 写入 `users.vip_plan_id`（当前套餐 monthly/yearly）
5. **API 路由**: `backend/app/api/pay.py`
   - `GET  /api/pay/plans` — 公开，返回套餐列表
   - `POST /api/pay/create` — 需登录，创建订单 + 调用支付网关
   - `GET  /api/pay/status/{order_no}` — 需登录，轮询订单状态
   - `POST /api/pay/notify/wechat` — 微信异步回调
   - `POST /api/pay/notify/alipay` — 支付宝异步回调
6. **前端 API**: `frontend/src/api/pay.ts` — `getPlans`, `createOrder`, `getOrderStatus`
7. **定价页**: `frontend/src/pages/PricingPage.vue` — 套餐卡片、支付方式选择、二维码展示、轮询等待
8. **VIP 弹窗**: `frontend/src/components/VipModal.vue` — 从导航栏"开通 VIP"按钮触发
9. **路由**: `/pricing` 加入 `router.ts`
10. **App.vue**: 未登录与已登录用户均显示 VIP 入口；已登录 VIP 显示「VIP 套餐」与「套餐与续费」链接
11. **users.vip_plan_id**: 字段 + `sql/migrate_vip_plan_id.sql`（已有库需执行迁移）；定价页 / VIP 弹窗展示「已是当前套餐」

### 测试结果

| 测试项 | 结果 |
|--------|------|
| `GET /api/pay/plans` 返回月度/年度套餐 | PASS |
| `POST /api/pay/create` 支付宝下单 → 返回 `qr_url` | PASS |
| `POST /api/pay/create` 微信下单 → 返回 `code_url` | PASS |
| `GET /api/pay/status/{order_no}` 查询订单状态 | PASS |
| 定价页 `/pricing` 渲染正常，套餐/价格/支付按钮显示正确 | PASS |
| 定价页选择支付宝 → 生成二维码 → 等待支付中 | PASS |
| VIP 用户仍可从导航进入「VIP 套餐」/「套餐与续费」 | PASS |
| 非 VIP 用户点击「开通 VIP」未登录时打开登录 | PASS |

### 技术决策

- **订单号格式**: `OV` + 时间戳 + 6位随机数
- **支付宝密钥**: 自动包装 PEM 头（`_wrap_pem` 辅助函数）
- **VIP 发放**: 已是 VIP 则从 `vip_expire_at` 延长；新 VIP 从当前时间起算
- **幂等性**: 回调处理检查 `order.status != 'pending'` 防止重复发放
- **前端二维码**: 使用 `qrcode` npm 包客户端渲染
- **轮询策略**: 每 2 秒查询一次，最多 5 分钟超时

### 故障排查：登录报 `Unknown column 'users.vip_plan_id'`

已在代码中增加字段，**已有数据库需执行一次** [`backend/sql/migrate_vip_plan_id.sql`](../backend/sql/migrate_vip_plan_id.sql)（详见同目录 [`README.md`](../backend/sql/README.md)）。

### 故障排查：微信已支付但订单 `status` 仍为 `pending`

常见原因是 **异步通知 URL 未收到请求**（仅 HTTP、内网穿透断开、未配 HTTPS 等）。已实现：**前端轮询 `GET /api/pay/status/{order_no}` 时，后端会调用微信/支付宝查单**；若官方结果为已支付且金额一致，会自动 `fulfill_order` 并更新为 `paid`。刷新支付等待页或再等一次轮询即可。

生产环境仍建议将 **`WECHAT_NOTIFY_URL` / `ALIPAY_NOTIFY_URL` 配成公网 HTTPS**，以便实时回调与对账。
