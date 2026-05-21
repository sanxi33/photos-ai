#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

usage() {
  cat <<'EOF'
用法:
  ./scripts/run.sh --oneshot   # 测试命令：只处理 1 张未处理照片，然后退出
  ./scripts/run.sh --daemon    # 持续守护：空闲时继续处理更多照片
EOF
}

if [[ $# -ne 1 ]]; then
  usage
  exit 1
fi

if [[ ! -f .env ]]; then
  echo "❌ 缺少 .env。先执行: cp .env.example .env"
  exit 1
fi

if [[ ! -x .venv/bin/python ]]; then
  echo "❌ 虚拟环境不存在。先执行: ./scripts/bootstrap.sh"
  exit 1
fi

case "$1" in
  --oneshot)
    exec .venv/bin/python photos_daemon.py --oneshot
    ;;
  --daemon)
    exec .venv/bin/python photos_daemon.py
    ;;
  *)
    usage
    exit 1
    ;;
esac
