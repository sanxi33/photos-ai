#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PLIST_PATH="$HOME/Library/LaunchAgents/com.sanxi.photos-ai-daemon.plist"
LABEL="com.sanxi.photos-ai-daemon"

mkdir -p "$HOME/Library/LaunchAgents"
mkdir -p "$REPO_ROOT/logs"

render_plist() {
  cat > "$PLIST_PATH" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>${LABEL}</string>

  <key>ProgramArguments</key>
  <array>
    <string>${REPO_ROOT}/scripts/run.sh</string>
    <string>--daemon</string>
  </array>

  <key>WorkingDirectory</key>
  <string>${REPO_ROOT}</string>

  <key>RunAtLoad</key>
  <true/>

  <key>KeepAlive</key>
  <false/>

  <key>StandardOutPath</key>
  <string>${REPO_ROOT}/logs/stdout.log</string>

  <key>StandardErrorPath</key>
  <string>${REPO_ROOT}/logs/stderr.log</string>

  <key>ProcessType</key>
  <string>Background</string>

  <key>Nice</key>
  <integer>10</integer>

  <key>LowPriorityIO</key>
  <true/>
</dict>
</plist>
EOF
}

usage() {
  echo "用法: $0 {install|uninstall|start|stop|status}"
}

bootout_if_loaded() {
  launchctl bootout "gui/$(id -u)" "$PLIST_PATH" >/dev/null 2>&1 || true
}

case "${1:-}" in
  install)
    if [[ ! -f "$REPO_ROOT/.env" ]]; then
      echo "❌ 缺少 $REPO_ROOT/.env，请先配置。"
      exit 1
    fi
    if [[ ! -x "$REPO_ROOT/.venv/bin/python" ]]; then
      echo "❌ 缺少虚拟环境，请先运行 ./scripts/bootstrap.sh"
      exit 1
    fi

    render_plist
    bootout_if_loaded
    launchctl bootstrap "gui/$(id -u)" "$PLIST_PATH"
    launchctl enable "gui/$(id -u)/$LABEL" || true
    launchctl kickstart -k "gui/$(id -u)/$LABEL" || true
    echo "✅ 已安装并启动开机自启"
    echo "   查看日志: tail -f $REPO_ROOT/logs/stdout.log"
    ;;
  uninstall)
    bootout_if_loaded
    rm -f "$PLIST_PATH"
    echo "✅ 已卸载"
    ;;
  start)
    if [[ ! -f "$PLIST_PATH" ]]; then
      echo "❌ 未安装，请先执行: ./scripts/launchd.sh install"
      exit 1
    fi
    launchctl kickstart -k "gui/$(id -u)/$LABEL"
    echo "✅ 已启动"
    ;;
  stop)
    bootout_if_loaded
    echo "✅ 已停止"
    ;;
  status)
    if launchctl print "gui/$(id -u)/$LABEL" >/dev/null 2>&1; then
      echo "✅ 守护进程已加载"
      launchctl print "gui/$(id -u)/$LABEL" | head -n 30
    else
      echo "⏹  守护进程未加载"
    fi
    ;;
  *)
    usage
    exit 1
    ;;
esac
