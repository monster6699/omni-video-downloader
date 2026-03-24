#!/usr/bin/env python3
"""
本地启动 FastAPI（在导入 uvicorn / watchfiles **之前** 设置 macOS fork 安全变量）。

勿用 ``python -m uvicorn main:app``：uvicorn 会先 import 自身，ObjC 可能在 main.py 运行前就初始化，
导致下载时子进程仍触发「fork pre-exec」崩溃弹窗。

用法（在 backend 目录）::

    python dev_uvicorn.py              # macOS 默认 **无** 热重载（避免 fork 弹窗）
    python dev_uvicorn.py --reload     # macOS 慎用：可能触发 ObjC/fork 崩溃
    python dev_uvicorn.py --port 8080
"""
from __future__ import annotations

import argparse
import os
import sys

if sys.platform == "darwin":
    os.environ["OBJC_DISABLE_INITIALIZE_FORK_SAFETY"] = "YES"
    import multiprocessing

    try:
        multiprocessing.set_start_method("spawn")
    except RuntimeError:
        pass


def main() -> None:
    is_darwin = sys.platform == "darwin"
    # macOS：uvicorn --reload 走 WatchFiles，会 fork 子进程，极易触发
    # 「crashed on child side of fork pre-exec」；默认关闭热重载。
    default_reload = not is_darwin

    parser = argparse.ArgumentParser(description="Run uvicorn with macOS fork-safety env set first.")
    parser.add_argument("--app", default="main:app", help="ASGI app path")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument(
        "--reload",
        action=argparse.BooleanOptionalAction,
        default=default_reload,
        help="Hot reload (default: off on macOS, on elsewhere). On macOS, reload may crash Python.",
    )
    args = parser.parse_args()

    if is_darwin and args.reload:
        print(
            "WARNING: --reload on macOS often causes fork/ObjC crashes (Python 意外退出). "
            "Prefer default (no reload) or restart the process after code changes.",
            file=sys.stderr,
        )

    import uvicorn

    uvicorn.run(args.app, host=args.host, port=args.port, reload=args.reload)


if __name__ == "__main__":
    main()
