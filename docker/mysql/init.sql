CREATE DATABASE IF NOT EXISTS omni_video CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE omni_video;

CREATE TABLE IF NOT EXISTS videos (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    url TEXT NOT NULL,
    platform VARCHAR(50) NOT NULL,
    title VARCHAR(500),
    duration INT,
    thumbnail TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS downloads (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    video_id BIGINT NOT NULL,
    format VARCHAR(50),
    status VARCHAR(20) DEFAULT 'pending',
    file_path TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (video_id) REFERENCES videos(id)
);
