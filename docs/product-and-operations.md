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
| `ANON_AI_DAILY_LIMIT` | 访客每日 LLM 次数上限（默认 5） |
| `REGISTER_DEFAULT_AI_QUOTA` | 与「注册默认 AI 次数」说明一致（默认 5，与库表默认对齐） |
| `TASK_MODE` | `local` / `queue`（RQ） |
| `WECHAT_*` / `ALIPAY_*` | 支付通道（见 `config.py`） |

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
