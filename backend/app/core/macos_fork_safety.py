"""
macOS: 在 fork + exec 子进程（yt-dlp 调 ffmpeg、部分 subprocess 实现）之前设置环境变量，
避免系统中止子进程并弹出「Python 意外退出」
（Application Specific Information: crashed on child side of fork pre-exec）。

应在尽可能早的时机导入本模块（例如在 main.py、task_service 的最前面）。

**重要**：若你用 ``python -m uvicorn main:app`` 启动，uvicorn/watchfiles 会在加载 main.py
**之前** 就完成部分原生初始化，仅靠此处 ``os.environ`` 可能仍无法避免弹窗。
macOS 上请改用 ``python dev_uvicorn.py``，Worker 用 ``python rq_worker.py worker video_tasks``，
或在 shell 里 **先** ``export OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES`` 再启动 Python。
"""

from __future__ import annotations

import os
import sys

if sys.platform == "darwin":
    # 强制覆盖空字符串等无效值；子进程继承该环境变量后 fork 检查才会关闭。
    os.environ["OBJC_DISABLE_INITIALIZE_FORK_SAFETY"] = "YES"
    import multiprocessing

    try:
        # 避免默认 fork 与 ObjC 运行时冲突（含部分库隐式用 multiprocessing）
        multiprocessing.set_start_method("spawn")
    except RuntimeError:
        pass
