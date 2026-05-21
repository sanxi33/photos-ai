#!/usr/bin/env bash
set -euo pipefail

resolve_repo_root() {
  if [[ -f "./photos_daemon.py" && -f "./pyproject.toml" ]]; then
    pwd
    return
  fi

  local target="${PHOTOS_AI_INSTALL_DIR:-$HOME/photos-ai}"
  local repo_url="${PHOTOS_AI_REPO_URL:-https://github.com/<owner>/photos-ai.git}"

  if [[ "$repo_url" == *"<owner>"* ]]; then
    echo "❌ 你在仓库外执行了安装脚本，但还没设置仓库地址。"
    echo "   请先设置 PHOTOS_AI_REPO_URL，例如："
    echo "   PHOTOS_AI_REPO_URL=https://github.com/yourname/photos-ai.git curl -fsSL https://raw.githubusercontent.com/yourname/photos-ai/main/scripts/bootstrap.sh | bash"
    exit 1
  fi

  if [[ ! -d "$target/.git" ]]; then
    echo "==> 拉取仓库到 $target"
    git clone "$repo_url" "$target"
  else
    echo "==> 更新仓库 $target"
    git -C "$target" pull --ff-only
  fi

  echo "$target"
}

REPO_ROOT="$(resolve_repo_root)"
cd "$REPO_ROOT"

echo "==> Photos AI 一键安装"

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "❌ 仅支持 macOS。"
  exit 1
fi

if ! command -v git >/dev/null 2>&1; then
  echo "❌ 缺少 git，请先安装。"
  exit 1
fi

if ! command -v xcode-select >/dev/null 2>&1; then
  echo "❌ 系统缺少 xcode-select，请先安装 Command Line Tools。"
  exit 1
fi

if ! command -v uv >/dev/null 2>&1; then
  echo "==> 检测到未安装 uv，开始安装"
  curl -LsSf https://astral.sh/uv/install.sh | sh
  if [[ -x "$HOME/.local/bin/uv" ]]; then
    export PATH="$HOME/.local/bin:$PATH"
  fi
fi

if ! command -v uv >/dev/null 2>&1; then
  echo "❌ uv 安装失败，请手动安装后重试。"
  exit 1
fi

if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "==> 已生成 .env（你可以先用默认值，稍后再改）"
fi

echo "==> 创建虚拟环境并安装依赖"
if [[ -d .venv ]]; then
  echo "==> 检测到已有 .venv，复用现有环境"
else
  uv venv
fi
uv sync --extra dev

if ! command -v ollama >/dev/null 2>&1; then
  echo "⚠️  未检测到 ollama，可继续使用你自己的 OpenAI 兼容服务。"
  echo "   若要安装 Ollama: https://ollama.com"
else
  echo "==> 检测本地模型"
  if ! ollama list | grep -q "Qwen3-VL-8B-NSFW-Caption-V4.5-mxfp4"; then
    echo "⚠️  未检测到默认模型 Qwen3-VL-8B-NSFW-Caption-V4.5-mxfp4"
    echo "   请按你的服务方式手动准备该模型。"
  else
    echo "✅ 默认模型已存在"
  fi
fi

echo "==> 运行环境检查"
./scripts/doctor.sh || true

echo
echo "✅ 安装完成"
echo "下一步："
echo "1) 编辑配置文件 .env（确认模型名和端口）"
echo "2) 运行一次: ./scripts/run.sh --oneshot"
echo "3) 常驻运行: ./scripts/run.sh --daemon"
echo "4) 可选开机自启: ./scripts/launchd.sh install"
