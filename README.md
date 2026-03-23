# OmniVideo Downloader

多平台视频解析与下载 + AI 分析（总结 / 思维导图 / 字幕 / 翻译 / 问答），含用户体系、VIP 与支付、管理后台。

## 文档（从这里开始）

| 文档 | 说明 |
|------|------|
| [**docs/README.md**](docs/README.md) | 文档索引 |
| [**docs/product-and-operations.md**](docs/product-and-operations.md) | **产品规则、额度、下载进度、支付、运维速查** |
| [**docs/project-status.md**](docs/project-status.md) | 架构、API 清单、平台与 B 站细节、缓存、本地启动 |

## 目录速览

- `backend/` — FastAPI、yt-dlp、任务与 AI 服务  
- `frontend/` — Vue 3 SPA  
- `docs/` — 项目文档  
- `omni_video_downloader_design.md` — 早期设计稿  

## 本地开发

后端、数据库、Redis 等见 **docs/project-status.md → 第十一节**。

## 安全与提交

**勿将密钥提交到 Git**：`.env`、Google `client_secret*.json`、支付参数文件（如 `payParams*.txt`）、商户私钥 `*.pem`、运行日志目录等已写入 `.gitignore`。复制仓库后请在本地自行放置密钥，或使用 CI/部署环境的密钥注入。
