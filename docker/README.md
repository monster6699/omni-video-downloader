# Docker 编排说明

一键拉起 **MySQL 8**、**Redis 7**、**FastAPI 后端**、**Vue 前端（构建为静态资源）**、**Nginx** 反向代理。

## 与仓库其它部分的关系

| 组件 | 说明 |
|------|------|
| **数据库初始化** | 使用仓库根目录 **`backend/sql/init.sql`**（通过 compose 挂载到 MySQL），与 ORM 模型一致；**不要**使用历史上 `docker/mysql/` 下的精简脚本。`init.sql` 仅在**空数据卷首次初始化**时执行；已有库升级见 **`docker/mysql/README.md`** → **`backend/sql/README.md`**（增量 `migrate_*.sql`）。 |
| **异步驱动** | `DATABASE_URL` 使用 **`mysql+asyncmy://`**（与 `requirements.txt` 一致）。 |
| **Chrome 扩展** | **不在**本 `docker-compose` 中；在宿主机执行 `cd extension && npm run build`，在浏览器加载 `extension/dist/`。扩展内 API 默认 `localhost:8000`，若只走 Nginx 80 端口需改扩展 `shared/api.ts` 或配合反向代理。 |
| **生产任务队列** | 默认 `TASK_MODE=local`；若改为 `queue`，需另起 RQ worker（见 `docs/project-status.md`）。 |

## 快速启动

```bash
cd docker
cp .env.example .env
# 编辑 .env：至少填写 OPENAI_API_KEY；生产修改 JWT_SECRET、MYSQL_* 

docker compose up -d --build
```

- 浏览器访问：**http://localhost**（由 `HTTP_PORT` 控制，默认 80）→ 前端；**/api/** → 后端。
- 直连后端调试：**http://localhost:8000**（`BACKEND_PORT`）。

## 健康检查与数据

- MySQL 数据卷：`omni-video_mysql_data`（compose project 名 `omni-video`）。
- 下载文件：`downloads_data` → 容器内 `/app/downloads`。

## Nginx 超时

- 普通 API：`proxy_read_timeout` **900s**（适配长耗时字幕翻译等）。
- **`/api/ai/chat`**：**关闭 buffering**，读超时 **3600s**（SSE）。

## 常见问题

1. **首次启动 MySQL 失败 healthcheck**：`start_period` 已加长；若仍失败，检查端口 3306 是否被本机占用。
2. **CORS**：通过 Nginx 同源访问前端时一般无跨域；若前端单独 `npm run dev` 连 Docker 后端，请在 `CORS_ORIGINS` 中加入 `http://localhost:5173`。
3. **清空库重来**：`docker compose down -v` 会删除卷（**数据清空**）。
