# 数据库脚本说明

## 已有库增量迁移

若后端日志或接口报错 **`Unknown column 'users.vip_plan_id'`**，说明线上/本地库尚未执行下列迁移，**在对应 MySQL 上执行一次即可**：

```bash
# 将连接参数换成你的环境（与 backend/.env 中 DATABASE_URL 一致）
mysql -h <主机> -P <端口> -u <用户> -p <数据库名> < sql/migrate_vip_plan_id.sql
```

或在客户端中直接执行：

```sql
ALTER TABLE users
  ADD COLUMN vip_plan_id VARCHAR(32) NULL COMMENT 'monthly / yearly — last paid plan' AFTER vip_expire_at;
```

执行成功后重启后端（若使用连接池一般无需重启），再尝试登录。

**说明**：`vip_plan_id` 在首次成功支付后由支付回调写入；老用户该字段可为 `NULL`，不影响登录。
