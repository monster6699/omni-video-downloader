#!/usr/bin/env python3
"""
RQ Worker 启动入口（macOS 必用此方式或 shell 先 export，勿直接 ``rq worker``）。

原因：``python -m uvicorn`` / ``rq worker`` 会先加载 uvicorn、rq、redis 等，再才执行你的业务代码；
ObjC/fork 相关初始化可能已发生，仅在 main.py 里 ``os.environ`` 往往无效。
本脚本在 **import rq 之前** 设置 OBJC_DISABLE_INITIALIZE_FORK_SAFETY。

用法（在 backend 目录，且 PYTHONPATH 含当前目录）::

    export PYTHONPATH=.
    python rq_worker.py worker video_tasks
"""
from __future__ import annotations

import os
import sys

if sys.platform == "darwin":
    os.environ["OBJC_DISABLE_INITIALIZE_FORK_SAFETY"] = "YES"
    import multiprocessing

    try:
        multiprocessing.set_start_method("spawn")
    except RuntimeError:
        pass

if __name__ == "__main__":
    from rq.cli import main

    raise SystemExit(main())
