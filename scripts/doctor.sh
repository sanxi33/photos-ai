#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

ok() { echo "✅ $*"; }
warn() { echo "⚠️  $*"; }
fail() { echo "❌ $*"; }

EXIT_CODE=0

if [[ "$(uname -s)" == "Darwin" ]]; then
  ok "系统: macOS"
else
  fail "仅支持 macOS"
  EXIT_CODE=1
fi

if command -v uv >/dev/null 2>&1; then
  ok "uv 已安装: $(uv --version | head -n 1)"
else
  warn "未检测到 uv"
  EXIT_CODE=1
fi

if [[ -x .venv/bin/python ]]; then
  ok "虚拟环境已创建"
else
  warn "未检测到 .venv，请先运行 ./scripts/bootstrap.sh"
  EXIT_CODE=1
fi

if [[ -f .env ]]; then
  ok "检测到 .env"
else
  warn "缺少 .env，请先 cp .env.example .env"
  EXIT_CODE=1
fi

if command -v ollama >/dev/null 2>&1; then
  ok "ollama 已安装"
  if ollama list | grep -q "Qwen3-VL-8B-NSFW-Caption-V4.5-mxfp4"; then
    ok "默认模型已存在"
  else
    warn "默认模型不存在: Qwen3-VL-8B-NSFW-Caption-V4.5-mxfp4"
  fi
else
  warn "未安装 ollama（可忽略：你也可以使用别的兼容服务）"
fi

if [[ -x .venv/bin/python && -f .env ]]; then
  set +e
  CHECK_OUTPUT=$(.venv/bin/python - <<'PY'
from runtime_config import load_runtime_config, ConfigError
import requests

try:
    cfg = load_runtime_config(require_env_file=True)
except ConfigError as e:
    print(f"CONFIG_ERROR::{e}")
    raise SystemExit(2)

try:
    resp = requests.get(cfg.api_url.rsplit('/v1/chat/completions', 1)[0] + '/v1/models', timeout=5)
    print(f"API_STATUS::{resp.status_code}")
except Exception as e:
    print(f"API_ERROR::{e}")
    raise SystemExit(3)

print(f"MODEL::{cfg.model}")
PY
)
  RC=$?
  set -e

  if [[ $RC -eq 0 ]]; then
    ok "配置解析与接口连通检查通过"
    echo "$CHECK_OUTPUT" | sed 's/^/   /'
  else
    warn "配置或接口检查失败"
    echo "$CHECK_OUTPUT" | sed 's/^/   /'
    EXIT_CODE=1
  fi
fi

if [[ $EXIT_CODE -eq 0 ]]; then
  ok "环境检查通过"
else
  warn "环境检查未完全通过，请按提示处理"
fi

exit $EXIT_CODE
