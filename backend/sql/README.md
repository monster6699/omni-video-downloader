# 数据库脚本说明

部署时以 **`sql/init.sql` 全量建库建表** 为准。该文件已包含：

- `users.vip_plan_id` 字段
- `site_settings` 表与默认行（`id=1`，月度/年度 VIP 标价）

使用方式：

```bash
mysql -h <主机> -P <端口> -u <用户> -p <数据库名> < sql/init.sql
```

说明：

- `vip_plan_id` 在首次成功支付后由回调写入；历史用户该字段可为 `NULL`。
- `.env` 中的 `VIP_MONTHLY_PRICE` / `VIP_YEARLY_PRICE` 仅在应用首次懒插入 `site_settings` 时作为种子；正常运行后以数据库值为准。
