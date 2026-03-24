# Chrome 插件开发说明

> **与当前仓库一致（2026-03）**  
> - 源码在 `extension/`，构建：`cd extension && npm run build`，在 Chrome **加载已解压的扩展程序** 时选择 **`extension/dist/`**（不是仓库根下的空目录）。  
> - **Popup**：`src/popup/`（Vue 3 + Vite），入口 `index.html`；**Content**：`src/content/`（esbuild 打成一个 `content/index.js`）；**Background**：`src/background/index.ts` → `dist/background/index.js`。  
> - **共享逻辑**：`src/shared/api.ts`（`Authorization: Bearer` + `localhost:8000/api`）、`storage.ts`（token/user）、**`videoUrlPatterns.ts`**（判断当前 Tab 是否为「视频页」——需与后端可解析的 URL 形态一致，例如抖音除 `/video/` 外还有 **`/jingxuan?modal_id=`**）。  
> - 模板里不要直接写 `navigator.xxx`，应放到 `<script setup>` 的函数中，避免 `vue-tsc` 报「组件实例上不存在 navigator」。  
> - 插件内「在网站上打开完整版」链接形如：`http://localhost:5173/?url=...`，网站首页会回填解析框（见 `project-status.md`）。

下文保留原「目标与概念」说明，部分 manifest 路径为教学示例，**以仓库 `extension/manifest.json` 为准**。

---

# 🧠 一、插件要做什么（先定目标）

你这个插件的核心是：

```
在用户正在看的视频页面 → 一键解析 → 下载 / AI分析
```

------

## 🎯 MVP 功能（第一版必须做）

### ✅ 核心功能

- 自动识别当前页面视频 URL
- 点击插件 → 调用你的后端 `/api/video/parse`
- 展示：
  - 标题
  - 封面
  - 清晰度列表
- 点击下载

------

### 🚀 加分功能（第二阶段）

- 自动弹出下载按钮（页面注入）
- AI总结入口
- 一键发送到你网站

------

# 🧩 二、整体架构

```
Chrome 插件
├── popup（弹窗 UI）
├── content script（页面注入）
└── background（通信 & 权限）

          ↓ API
你的 FastAPI 后端
```

------

# 📦 三、目录结构

```
extension/
├── manifest.json
├── popup/
│   ├── popup.html
│   ├── popup.js
│   └── popup.css
├── content/
│   └── content.js
└── background/
    └── background.js
```

------

# ⚙️ 四、manifest.json（Manifest V3）

```
{
  "manifest_version": 3,
  "name": "Omni Video Downloader",
  "version": "1.0",
  "description": "Download videos from multiple platforms",

  "permissions": [
    "activeTab",
    "storage",
    "scripting"
  ],

  "host_permissions": [
    "http://localhost:8000/*",
    "https://*/*"
  ],

  "action": {
    "default_popup": "popup/popup.html"
  },

  "background": {
    "service_worker": "background/background.js"
  },

  "content_scripts": [
    {
      "matches": ["<all_urls>"],
      "js": ["content/content.js"]
    }
  ]
}
```

------

# 🧠 五、核心逻辑

------

## 5.1 获取当前页面 URL

```
// popup.js

chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
  const url = tabs[0].url;
  console.log("当前页面:", url);
});
```

------

## 5.2 调用你后端解析接口

```
async function parseVideo(url) {
  const res = await fetch("http://localhost:8000/api/video/parse", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({ url })
  });

  return await res.json();
}
```

------

## 5.3 展示结果

```
const result = await parseVideo(url);

document.getElementById("title").innerText = result.title;
document.getElementById("cover").src = result.cover;
```

------

## 5.4 下载

```
async function downloadVideo(url) {
  const res = await fetch("http://localhost:8000/api/video/download", {
    method: "POST",
    body: JSON.stringify({ url })
  });

  const data = await res.json();
  console.log("task_id:", data.task_id);
}
```

------

# 🎨 六、popup.html（极简版）

```
<!DOCTYPE html>
<html>
<head>
  <style>
    body { width: 300px; font-family: Arial; }
    img { width: 100%; }
  </style>
</head>
<body>
  <h3 id="title">Loading...</h3>
  <img id="cover" />
  <button id="download">Download</button>

  <script src="popup.js"></script>
</body>
</html>
```

------

# ⚡ 七、进阶玩法（你这个项目强烈建议）

------

## 🔥 7.1 页面注入下载按钮（非常加分）

比如在：

- YouTube
- B站
- 抖音
- TikTok

直接插一个按钮：

```
// content.js

const btn = document.createElement("button");
btn.innerText = "下载视频";

btn.onclick = () => {
  fetch("http://localhost:8000/api/video/download", {
    method: "POST",
    body: JSON.stringify({ url: location.href })
  });
};

document.body.appendChild(btn);
```

------

## 🔥 7.2 AI总结直接展示

```
点击插件 → 显示总结
```

------

## 🔥 7.3 登录同步（很关键）

你后端有 JWT：

👉 插件可以存 token：

```
chrome.storage.local.set({ token: "xxx" });
```

------

# ⚠️ 八、关键坑（你一定会遇到）

------

## ❗ 1. CORS 问题

后端必须允许：

```
allow_origins=["*"]
```

------

## ❗ 2. HTTPS 限制

Chrome 插件：

👉 有些请求必须 HTTPS（发布后）

------

## ❗ 3. B站 / 抖音限制

👉 不能直接抓视频流
 👉 你现在的“后端解析”方案是对的 ✅

------

## ❗ 4. Store 审核（很重要）

Chrome Web Store 对：

👉 下载类插件审查很严格

建议：

- 不写“下载 YouTube”字样

- 用：

  > "Video Tool" / "Media Assistant"

------

# 🚀 九、上线流程

1. 打开：`chrome://extensions/`
2. 开启「开发者模式」
3. 在仓库中执行 `cd extension && npm run build`
4. 「加载已解压的扩展程序」选择 **`extension/dist/`** 目录（内含 `manifest.json`、`popup/`、`background/`、`content/`）

------

# 🧠 十、推荐你下一步这样做

------

## 🥇 第一阶段

- popup + parse + download
- 打通 API

------

## 🥈 第二阶段

- 页面注入按钮
- 登录同步

------

## 🥉 第三阶段

- AI总结
- UI优化

