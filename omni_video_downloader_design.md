# OmniVideo Downloader 系统设计文档

一个支持 **多平台视频解析与下载** 的工具站 + 浏览器插件系统。\
用户只需要输入 **一个视频URL**，即可下载来自不同平台的视频，并支持
**AI视频总结、字幕翻译、会员功能**。

------------------------------------------------------------------------

# 1 项目目标

构建一个统一的视频下载平台，支持：

-   多平台视频解析
-   视频下载
-   浏览器插件快速下载
-   AI视频总结
-   字幕翻译
-   会员系统

支持平台：

-   YouTube
-   Bilibili
-   抖音
-   TikTok
-   Twitter/X
-   Instagram

核心原则：

1.  站在开源项目基础上开发
2.  使用 yt-dlp 进行视频解析
3.  尽量减少自研复杂逻辑
4.  系统可扩展
5.  UI简洁易用

------------------------------------------------------------------------

# 2 系统架构

整体架构如下：

Chrome插件 → 前端网站(Vue3) → FastAPI API → 用户系统 / 视频解析服务 /
AI服务 → MySQL / yt-dlp / OpenAI

------------------------------------------------------------------------

# 3 技术栈

## 前端

-   Vue3
-   Vite
-   Naive UI
-   TailwindCSS

特点：

-   响应式布局
-   支持移动端
-   工具站UI风格

## 后端

-   Python
-   FastAPI

原因：

-   异步性能好
-   与 yt-dlp 同语言
-   AI扩展方便

## 数据库

-   MySQL

用途：

-   用户系统
-   下载记录
-   视频解析历史
-   AI任务记录

## 缓存

-   Redis

用途：

-   下载任务队列
-   API限流
-   视频缓存

## 视频解析

-   yt-dlp

能力：

-   视频解析
-   视频下载
-   字幕下载

## AI能力

-   OpenAI API
-   Whisper

功能：

-   视频转文字
-   视频总结
-   字幕翻译

------------------------------------------------------------------------

# 4 核心模块

系统包含以下模块：

1.  用户系统
2.  视频解析模块
3.  视频下载模块
4.  下载任务系统
5.  AI视频总结
6.  浏览器插件
7.  会员系统

------------------------------------------------------------------------

# 5 数据库设计

## users

用户表

CREATE TABLE users ( id BIGINT PRIMARY KEY AUTO_INCREMENT, email
VARCHAR(255), password VARCHAR(255), google_id VARCHAR(255), is_vip
BOOLEAN DEFAULT FALSE, vip_expire_at DATETIME, created_at DATETIME );

## videos

CREATE TABLE videos ( id BIGINT PRIMARY KEY AUTO_INCREMENT, url TEXT,
platform VARCHAR(50), title VARCHAR(255), duration INT, thumbnail TEXT,
created_at DATETIME );

## downloads

CREATE TABLE downloads ( id BIGINT PRIMARY KEY AUTO_INCREMENT, user_id
BIGINT, video_id BIGINT, format VARCHAR(50), status VARCHAR(20),
file_path TEXT, created_at DATETIME );

## ai_tasks

CREATE TABLE ai_tasks ( id BIGINT PRIMARY KEY AUTO_INCREMENT, video_id
BIGINT, type VARCHAR(50), status VARCHAR(20), result TEXT, created_at
DATETIME );

------------------------------------------------------------------------

# 6 yt-dlp封装设计

封装文件：

backend/services/video_service.py

主要功能：

## 解析视频

调用：

yt-dlp -j URL

返回：

-   title
-   thumbnail
-   duration
-   formats

## 获取真实下载地址

yt-dlp -g URL

用于直接下载。

## 下载视频

yt-dlp -f best URL

保存路径：

/downloads

------------------------------------------------------------------------

# 7 智能下载策略

系统自动判断下载方式。

## 方式1 直链下载

返回真实下载地址。

适用平台：

-   YouTube
-   Twitter
-   Instagram

优点：

服务器无带宽压力

## 方式2 服务器下载

服务器下载视频。

适用：

-   Bilibili
-   抖音

流程：

解析视频 → 服务器下载 → 缓存3小时 → 用户下载

------------------------------------------------------------------------

# 8 下载缓存策略

服务器缓存视频：

默认3小时

配置项：

DOWNLOAD_CACHE_HOURS

示例：

3 / 6 / 12 / 24

------------------------------------------------------------------------

# 9 FastAPI API设计

## 解析视频

POST /api/video/parse

请求：

{ "url":"" }

返回：

{ "title":"","thumbnail":"","duration":0, "formats":\[\] }

## 下载视频

POST /api/video/download

请求：

{ "url":"","format":"1080p" }

返回：

download_url

## AI视频总结

POST /api/ai/summary

流程：

下载视频 → 提取音频 (如果有字幕优先提取字幕文字)→ Whisper转文字 → OpenAI总结

返回：

-   summary
-   keypoints
-   timeline

## 登录

POST /api/auth/login

## Google登录

POST /api/auth/google

## 用户信息

GET /api/user/profile

------------------------------------------------------------------------

# 10 浏览器插件设计

插件支持：

Chrome

插件结构：

extension - manifest.json - popup.html - popup.js - content.js

功能：

检测当前页面URL → 调用解析API → 显示下载按钮

------------------------------------------------------------------------

# 11 前端UI设计

UI风格：

工具站风格

配色：

-   #002EB7
-   #0084FF
-   #20D5C4
-   #8DFFF4
-   #EAFFFD

首页结构：

```
LOGO

万能视频下载

[ 输入URL ]

[解析视频]

---------------------

视频信息

封面
标题
时长

清晰度选择

1080p
720p
480p

[下载]
```



------------------------------------------------------------------------

# 12 Docker部署

系统包含：

-   nginx
-   frontend
-   fastapi
-   mysql
-   redis

docker-compose 管理所有服务。

------------------------------------------------------------------------

# 13 服务器配置

最低配置：

-   2核CPU
-   4G内存

推荐：

-   4核CPU
-   8G内存

AI任务较多时：

-   8核CPU
-   16G内存

------------------------------------------------------------------------

# 14 项目目录结构

video-downloader

frontend\
backend\
extension\
docker\
docs

backend - app - api - models - schemas - services - utils - ai -
yt_dlp_wrapper - main.py

frontend - src - pages - components

extension - manifest.json - popup.html - popup.js

docker - docker-compose.yml



------------------------------------------------------------------------

# 15 开发阶段规划

第一阶段：

-   URL解析
-   视频下载
-   基础UI

第二阶段：

-   会员系统
-   浏览器插件
-   下载记录

第三阶段：

-   AI视频总结
-   字幕翻译
-   批量下载

------------------------------------------------------------------------

# 16 风险控制

建议：

不长期存储视频

策略：

仅缓存3小时,后端可以自定义配置几个小时

------------------------------------------------------------------------

# 17 未来扩展

-   批量下载
-   播放列表下载
-   AI字幕
-   AI翻译
-   AI摘要
-   API服务
-   企业版

------------------------------------------------------------------------

# 18 盈利模式

-   VIP会员
-   AI总结收费
-   API调用收费
-   企业套餐

------------------------------------------------------------------------

# 19 MVP开发优先级

优先开发：

1.  视频解析
2.  视频下载
3.  基础UI

第二阶段：

-   会员系统
-   插件
-   下载记录

第三阶段：

-   AI总结
-   字幕翻译
-   思维导图

------------------------------------------------------------------------

# 20 项目总结

该系统是一个：

多平台视频下载工具 + AI视频处理平台

核心能力来自：

-   yt-dlp
-   FastAPI
-   OpenAI

目标：

打造一个统一的视频下载与AI处理平台。
