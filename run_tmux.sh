#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="${AAHELPER_PROJECT_DIR:-$SCRIPT_DIR}"
BOT_SESSION="${AAHELPER_BOT_SESSION:-aahelper-bot}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
RESTART_DELAY_SEC="${RESTART_DELAY_SEC:-5}"

TELEGRAM_PROXY_URL="${TELEGRAM_PROXY_URL:-}"
HTTP_PROXY="${HTTP_PROXY:-$TELEGRAM_PROXY_URL}"
HTTPS_PROXY="${HTTPS_PROXY:-$TELEGRAM_PROXY_URL}"
ALL_PROXY="${ALL_PROXY:-$TELEGRAM_PROXY_URL}"

if [[ ! -f "$PROJECT_DIR/.env" ]]; then
  echo "[aahelper] ERROR: .env not found in $PROJECT_DIR"
  exit 1
fi

if [[ ! -f "$PROJECT_DIR/bot.py" ]]; then
  echo "[aahelper] ERROR: bot.py not found in $PROJECT_DIR"
  exit 1
fi

echo "[aahelper] project: $PROJECT_DIR"
echo "[aahelper] session: $BOT_SESSION"

tmux kill-session -t "$BOT_SESSION" 2>/dev/null || true
pkill -f "${PROJECT_DIR}/bot.py" 2>/dev/null || true
sleep 1

TMUX_CMD="cd '${PROJECT_DIR}'"
if [[ -n "$TELEGRAM_PROXY_URL" ]]; then
  TMUX_CMD+=" && export TELEGRAM_PROXY_URL='${TELEGRAM_PROXY_URL}' HTTP_PROXY='${HTTP_PROXY}' HTTPS_PROXY='${HTTPS_PROXY}' ALL_PROXY='${ALL_PROXY}'"
fi
TMUX_CMD+=" && while true; do echo \"[aahelper-bot] start \$(date -Is)\"; ${PYTHON_BIN} bot.py; echo \"[aahelper-bot] exit \$?, sleep ${RESTART_DELAY_SEC}s\"; sleep ${RESTART_DELAY_SEC}; done"

tmux new -d -s "$BOT_SESSION" "$TMUX_CMD"
tmux set-option -t "$BOT_SESSION" remain-on-exit on

sleep 2

if tmux has-session -t "$BOT_SESSION" 2>/dev/null; then
  echo "[aahelper] $BOT_SESSION: UP"
else
  echo "[aahelper] $BOT_SESSION: DOWN"
  exit 1
fi

tmux ls || true
echo "[aahelper] tail:"
tmux capture-pane -pt "$BOT_SESSION" | tail -n 25 || true
echo "[aahelper] attach: tmux attach -t $BOT_SESSION"
