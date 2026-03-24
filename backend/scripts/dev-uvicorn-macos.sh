#!/usr/bin/env bash
# macOS：在启动 Python 前 export，并由 dev_uvicorn 在 import uvicorn 之前再次设置。
# 用法：cd backend && ./scripts/dev-uvicorn-macos.sh
set -euo pipefail
cd "$(dirname "$0")/.."
export OBJC_DISABLE_INITIALIZE_FORK_SAFETY="${OBJC_DISABLE_INITIALIZE_FORK_SAFETY:-YES}"
exec python dev_uvicorn.py "$@"
