# 产品与运维说明

> 沉淀日期：2026-03-23  
> 面向：产品、前端/后端开发、运维配置

本文与 [`project-status.md`](./project-status.md) 互补：**这里偏「规则 + 行为 + 配置速查」**，后者偏「实现细节 + 长文记录」。

---

## 1. 前端路由（Vue Router）

| 路径 | 页面 | 说明 |
|------|------|------|
| `/` | `Home.vue` | 解析、下载、AI 面板 |
| `/history` | `HistoryPage.vue` | 下载记录（需登录） |
| `/admin` | `AdminPage.vue` | 管理后台（需 `is_admin`） |
| `/pricing` | `PricingPage.vue` | VIP 定价与支付 |
| `/guide` | `GuidePage.vue` | 使用说明（额度与操作） |

入口：`frontend/src/router.ts`。顶栏导航与图标在 `App.vue`。

---

## 2. AI / VIP 额度规则（后端为准）

### 2.1 哪些接口算「LLM 消耗」

以下会走 **`check_ai_llm_access`**（访客限次 + 登录扣次 / VIP 放行）：

- `POST /api/ai/summary`
- `POST /api/ai/mindmap`
- `POST /api/ai/translate`（**缓存命中不扣次**，直接返回缓存）
- `POST /api/ai/chat`

**不计入**上述 LLM 配额：

- `POST /api/ai/subtitle`（仅拉取/解析字幕，不走大模型扣次逻辑）

### 2.2 访客（未登录）

- 按 **公网 IP** + **UTC 自然日** 统计，Redis key：`anon:ai:{YYYY-MM-DD}:{ip}`。
- 每日上限由环境变量 **`ANON_AI_DAILY_LIMIT`**（默认 `5`）控制。
- 超限：`403`，文案提示登录或开通 VIP。
- Redis 不可用：匿名调用 LLM 可能 **`503`**；登录用户仍走数据库配额，不依赖该计数。

### 2.3 已登录（非 VIP）

- 使用账号字段 **`ai_quota`**，每次成功调用上述 LLM 接口扣 **1**（翻译缓存命中不扣）。
- 注册默认额度与说明页展示可由 **`REGISTER_DEFAULT_AI_QUOTA`**（默认 `5`，需与业务/库表一致）配合 `GET /api/ai/usage-rules`。

### 2.4 VIP

- 在 **`is_vip` 且未过期**（`vip_expire_at` 晚于当前时间，逻辑见 `permissions.user_has_active_vip`）时，**不扣** `ai_quota`。

### 2.5 对外只读接口

| 方法 | 路径 | 用途 |
|------|------|------|
| GET | `/api/ai/usage-rules` | 静态规则 + 配置数字（给 `/guide` 等） |
| GET | `/api/ai/quota-status` | 当前请求下的额度快照（可选登录；访客读 Redis 已用量） |

实现要点：`app/core/permissions.py`、`app/api/ai.py`。前端 AI 面板通过 `fetchAiQuotaStatus` 展示文案，并在问答/翻译成功后 `inject('refreshAiQuota')` 刷新。

---

## 3. 下载任务进度（`/api/video/task/{task_id}`）

- 同一视频**不同清晰度**使用**不同磁盘文件名**（`{url_hash}_{format}.mp4`），避免 `/api/video/file/...` URL 相同导致**浏览器仍播放旧缓存的 360P**。
- 文件接口对视频响应头 **`Cache-Control: no-store`**。

- 任务状态存 Redis：`task:{task_id}` 的 `progress` 字段 **0–100**。
- **10%** 表示已进入 `_execute_download` 主流程；之后：
  - **yt-dlp**：`progress_hooks` 写入；若流式下载**无总字节数**，则用**时间估算**进度，避免长期卡在 10。
  - **B 站 / 抖音** 自研下载：无 yt-dlp hook 时，用**后台线程**缓慢推高进度，避免长期卡在 10。
- 完成：`progress=100`，并返回下载 URL 等信息。

代码：`backend/app/services/task_service.py`。

---

## 4. 支付与 VIP（微信 / 支付宝）

- 路由前缀：`/api/pay`（见 `backend/main.py`）。
- 典型接口：`GET /api/pay/plans`、`POST /api/pay/create`、`GET /api/pay/status/{order_no}`、支付渠道异步通知路由。
- 前端：**定价页** `PricingPage.vue`、**VIP 弹窗** `VipModal.vue`；支付方式图标使用 **`@vicons/ionicons5`** 的 `LogoWechat`、`LogoAlipay`（Lucide 无品牌标）。
- 商户与密钥类配置见 **`backend/app/core/config.py`** 与 `.env`（`WECHAT_*`、`ALIPAY_*`、`VIP_*` 等），**勿将密钥提交仓库**。

---

## 5. 管理后台（用户列表）

- `GET /api/admin/users` 已返回 `vip_expire_at`。
- 前端表格展示 **「VIP 到期」** 列；已过期标红并显示「已过期」。
- `PUT /api/admin/users/{id}` 使用 **`model_dump(exclude_unset=True)`** 做部分更新；**可将 `vip_expire_at` 置为 `null` 清空到期时间**（需请求体显式带该字段）。

---

## 6. 环境变量速查（补充）

在 `project-status.md` 第十节基础上，按需增加：

| 变量 | 含义 |
|------|------|
| `DATABASE_URL` | 推荐 **`mysql+asyncmy://...`**；若仍写 `mysql+aiomysql://`，应用启动时会替换为 asyncmy（见 `app/core/database.py`） |
| `TRANSLATE_MAX_OUTPUT_TOKENS` | 字幕翻译单次 `max_tokens` 上限（默认 `8192`），过小易导致返回截断、缺行 |
| `ANON_AI_DAILY_LIMIT` | 访客每日 LLM 次数上限（默认 5） |
| `REGISTER_DEFAULT_AI_QUOTA` | 与「注册默认 AI 次数」说明一致（默认 5，与库表默认对齐） |
| `TASK_MODE` | **默认 `local`（开发）**：进程内线程池下载，**不启用 RQ**。生产可设 `queue` + 独立 Worker。 |
| `WECHAT_*` / `ALIPAY_*` | 支付通道（见 `config.py`） |

**数据库异常与前端**：`main.py` 将 **`DBAPIError`**（含连接断开、驱动协议错误等）统一为 **HTTP 503** + JSON `{"detail":"..."}`。网站 `api/ai.ts` 的 **`extractApiErrorMessage`** 会同时兼容纯文本错误体，避免界面只显示 `Internal Server Error`。

### `TASK_MODE=local`（推荐本地 / macOS 开发）

- 无需 `rq worker`；`POST /api/video/download` 仍写 Redis 任务状态，由 **API 进程内** `asyncio.to_thread` 执行下载。
- 避免 RQ 子进程与 macOS fork/ObjC 安全机制冲突。

### `TASK_MODE=queue` 时（生产或压测）

1. **安装依赖**：`pip install -r requirements.txt`（已包含 `rq`）。若仍报 `RQ is not installed`，在 venv 内重新执行安装。
2. **单独起 Worker**（与 uvicorn 进程不同）：队列名为 `video_tasks`，需在项目根（或设置 `PYTHONPATH=backend`）执行，例如：
   ```bash
   cd backend && source venv/bin/activate
   export PYTHONPATH=.
   python rq_worker.py worker video_tasks
   ```
   或使用：`./scripts/rq-video-worker.sh`（shell 先 `export` + 同上 Python 入口）。
   **勿在 macOS 上直接 `rq worker`**：`rq` 会先加载依赖，仅靠 `main.py` 里设环境变量往往太晚，仍会出现「Python 意外退出 / fork pre-exec」弹窗。
   Worker 与 API 共用同一 `REDIS_URL`，否则任务会一直停在 pending。
3. **macOS 上起 API**：勿用 `python -m uvicorn main:app`（uvicorn/watchfiles 先于 `main.py` 初始化）。请用：
   ```bash
   cd backend && export PYTHONPATH=. && python dev_uvicorn.py
   ```
   或：`./scripts/dev-uvicorn-macos.sh`。**`dev_uvicorn.py` 在 macOS 上默认关闭 `--reload`**（热重载会 fork 子进程，极易触发「Python 意外退出 / fork pre-exec」）；改代码后请手动重启进程。需要热重载时可加 `--reload`，但可能再次弹窗。
   若必须用 `uvicorn` 命令，请在**同一终端**先执行 `export OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES`，并尽量**不要**加 `--reload`。
4. **改代码后务必重启 Worker**：Worker 是独立进程，不随 uvicorn `--reload` 更新；未重启会仍跑旧逻辑（例如清晰度、缓存 key）。
5. **清晰度参数**：enqueue 时会把 `url`、`format_id` 写入 Redis `task:{id}`；Worker 优先读 Redis，避免 RQ 序列化导致 `format_id` 丢失、始终落到默认画质。
6. 下载文件 Redis 缓存 key 使用 **`dl:v2:`** 前缀；升级后旧 `dl:{hash}:*` 不再命中，避免指向已废弃的单文件路径。

---

## 7. 相关代码入口（速查）

| 主题 | 位置 |
|------|------|
| AI 权限与匿名限次 | `backend/app/core/permissions.py` |
| AI 路由 | `backend/app/api/ai.py` |
| 下载任务与进度 | `backend/app/services/task_service.py` |
| 任务调度入口 | `backend/app/core/task_dispatcher.py` |
| 管理端用户更新 | `backend/app/api/admin.py` |
| 前端额度 API | `frontend/src/api/ai.ts` |
| VIP 时间展示格式 | `frontend/src/utils/format.ts`（`formatVipExpireAt` 等） |

---

## 8. 文档维护说明

- 大版本或规则变更时：更新 **本文** + `project-status.md` 对应表格/日期。
- 设计层面的长篇机制（B 站字幕链、缓存 key）仍以 **`project-status.md`** 为准。
