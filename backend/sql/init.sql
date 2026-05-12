-- OmniVideo Downloader - Database Initialization
-- Run: mysql -u root -p < sql/init.sql

CREATE DATABASE IF NOT EXISTS omni_video
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE omni_video;

-- Grant privileges (adjust password as needed)
-- CREATE USER IF NOT EXISTS 'omni'@'localhost' IDENTIFIED BY 'omni123';
-- GRANT ALL PRIVILEGES ON omni_video.* TO 'omni'@'localhost';
-- FLUSH PRIVILEGES;

-- ============================================================
-- Users
-- ============================================================
CREATE TABLE IF NOT EXISTS users (
    id            BIGINT PRIMARY KEY AUTO_INCREMENT,
    phone         VARCHAR(20)  UNIQUE COMMENT '手机号（唯一）',
    password_hash VARCHAR(255)         COMMENT 'bcrypt hash',
    nickname      VARCHAR(100)         COMMENT '昵称',
    avatar_url    TEXT                 COMMENT '头像 URL',
    google_id     VARCHAR(128) UNIQUE  COMMENT 'Google sub (唯一)',
    google_email  VARCHAR(255)         COMMENT 'Google 邮箱',
    is_vip        BOOLEAN      NOT NULL DEFAULT FALSE,
    vip_expire_at DATETIME             COMMENT 'VIP 到期时间',
    vip_plan_id   VARCHAR(32)          COMMENT 'monthly / yearly — last paid plan',
    ai_quota      INT          NOT NULL DEFAULT 5 COMMENT '每日免费 AI 次数',
    created_at    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_phone (phone),
    INDEX idx_google_id (google_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================
-- Videos (parsed video metadata)
-- ============================================================
CREATE TABLE IF NOT EXISTS videos (
    id         BIGINT PRIMARY KEY AUTO_INCREMENT,
    url        TEXT         NOT NULL,
    url_hash   VARCHAR(32)  NOT NULL COMMENT 'MD5(url) for dedup',
    platform   VARCHAR(50)  NOT NULL,
    title      VARCHAR(500),
    duration   INT,
    thumbnail  TEXT,
    created_at DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_url_hash (url_hash)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================
-- Downloads (user download records)
-- ============================================================
CREATE TABLE IF NOT EXISTS downloads (
    id         BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id    BIGINT       COMMENT 'NULL for anonymous',
    video_id   BIGINT       NOT NULL,
    format_id  VARCHAR(50),
    resolution VARCHAR(20),
    method     VARCHAR(20)  DEFAULT 'server' COMMENT 'direct / server',
    status     VARCHAR(20)  DEFAULT 'done',
    file_path  TEXT,
    created_at DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user (user_id),
    INDEX idx_video (video_id),
    FOREIGN KEY (user_id)  REFERENCES users(id) ON DELETE SET NULL,
    FOREIGN KEY (video_id) REFERENCES videos(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================
-- Download History (per-user, for history page)
-- ============================================================
CREATE TABLE IF NOT EXISTS download_history (
    id         BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id    BIGINT       NOT NULL,
    url        TEXT         NOT NULL,
    platform   VARCHAR(50)  NOT NULL,
    title      VARCHAR(500),
    thumbnail  TEXT,
    format_id  VARCHAR(50),
    resolution VARCHAR(20),
    method     VARCHAR(20)  DEFAULT 'server',
    created_at DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user (user_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================
-- AI Tasks (summary / mindmap / translate / chat)
-- ============================================================
CREATE TABLE IF NOT EXISTS ai_tasks (
    id              BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id         BIGINT       COMMENT 'NULL for anonymous',
    video_id        BIGINT,
    task_type       VARCHAR(50)  NOT NULL COMMENT 'summary / mindmap / translate / chat',
    status          VARCHAR(20)  DEFAULT 'done',
    result_snapshot MEDIUMTEXT   COMMENT 'JSON snapshot of AI result',
    created_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user (user_id),
    INDEX idx_video (video_id),
    FOREIGN KEY (user_id)  REFERENCES users(id) ON DELETE SET NULL,
    FOREIGN KEY (video_id) REFERENCES videos(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================
-- Orders (payment orders for VIP plans)
-- ============================================================
CREATE TABLE IF NOT EXISTS orders (
    id              BIGINT PRIMARY KEY AUTO_INCREMENT,
    order_no        VARCHAR(64)  NOT NULL UNIQUE,
    user_id         BIGINT       NOT NULL,
    plan_id         VARCHAR(32)  NOT NULL COMMENT 'monthly / yearly',
    amount          INT          NOT NULL COMMENT 'unit: fen',
    pay_method      VARCHAR(20)  NOT NULL COMMENT 'wechat / alipay',
    status          VARCHAR(20)  NOT NULL DEFAULT 'pending',
    transaction_id  VARCHAR(128),
    qr_url          TEXT,
    paid_at         DATETIME,
    created_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user (user_id),
    INDEX idx_order_no (order_no),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================
-- Site settings (singleton id=1): VIP list prices in fen
-- ============================================================
CREATE TABLE IF NOT EXISTS site_settings (
    id                      INT          PRIMARY KEY,
    vip_monthly_price_fen   INT          NOT NULL COMMENT '月度 VIP 标价（分）',
    vip_yearly_price_fen    INT          NOT NULL COMMENT '年度 VIP 标价（分）',
    updated_at              DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

INSERT INTO site_settings (id, vip_monthly_price_fen, vip_yearly_price_fen)
VALUES (1, 990, 8800)
ON DUPLICATE KEY UPDATE id = id;
