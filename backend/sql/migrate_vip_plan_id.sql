-- Run once on existing DB: add current VIP plan tracking (monthly/yearly)
ALTER TABLE users
  ADD COLUMN vip_plan_id VARCHAR(32) NULL COMMENT 'monthly / yearly — last paid plan' AFTER vip_expire_at;
