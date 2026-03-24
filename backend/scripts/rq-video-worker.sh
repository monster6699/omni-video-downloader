#!/usr/bin/env bash
# macOS：shell 先 export + 用 rq_worker.py（rq 导入前设环境），避免「fork pre-exec」弹窗。
# 用法：cd backend && ./scripts/rq-video-worker.sh
set -euo pipefail
cd "$(dirname "$0")/.."
export OBJC_DISABLE_INITIALIZE_FORK_SAFETY="${OBJC_DISABLE_INITIALIZE_FORK_SAFETY:-YES}"
export PYTHONPATH="${PYTHONPATH:-.}"
exec python rq_worker.py worker video_tasks "$@"
