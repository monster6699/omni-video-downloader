# 说明

MySQL 表结构由 **`docker-compose.yml`** 挂载 **`../backend/sql/init.sql`** 到容器的 `/docker-entrypoint-initdb.d/`，**仅在数据卷首次初始化时**执行。当前部署流程建议直接重建库并执行 `init.sql`；脚本说明见 **[`backend/sql/README.md`](../../backend/sql/README.md)**。

本目录不再维护独立的 `init.sql`，避免与 ORM / 业务表结构脱节。
