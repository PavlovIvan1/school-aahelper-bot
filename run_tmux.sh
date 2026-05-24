#!/usr/bin/env bash
set -euo pipefail

# Каталог проекта (по умолчанию — там, где лежит этот скрипт)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="${AAHELPER_PROJECT_DIR:-$SCRIPT_DIR}"
BOT_SESSION="${AAHELPER_BOT_SESSION:-aahelper-bot}"

# Опционально: прокси для Telegram (как у основного бота)
TELEGRAM_PROXY_URL="${TELEGRAM_PROXY_URL:-}"
HTTP_PROXY="${HTTP_PROXY:-$TELEGRAM_PROXY_URL}"
HTTPS_PROXY="${HTTPS_PROXY:-$TELEGRAM_PROXY_URL}"
ALL_PROXY="${ALL_PROXY:-$TELEGRAM_PROXY_URL}"

PYTHON_BIN="${PYTHON_BIN:-python3}"
RESTART_DELAY_SEC="${RESTART_DELAY_SEC:-5}"

if [[ ! -f "$PROJECT_DIR/.env" ]]; then
  echo "[aahelper] ERROR: .env not found in $PROJECT_DIR"
  echo "[aahelper] Copy .env.example to .env and set BOT_TOKEN"
  exit 1
fi

if [[ ! -f "$PROJECT_DIR/bot.py" ]]; then
  echo "[aahelper] ERROR: bot.py not found in $PROJECT_DIR"
  exit 1
fi

echo "[aahelper] project: $PROJECT_DIR"
echo "[aahelper] session: $BOT_SESSION"

echo "[aahelper] stop old tmux session (if any)"
tmux kill-session -t "$BOT_SESSION" 2>/dev/null || true

echo "[aahelper] stop orphan bot processes for this project"
pkill -f "${PROJECT_DIR}/bot.py" 2>/dev/null || true
pkill -f "cd ${PROJECT_DIR}.*bot.py" 2>/dev/null || true
sleep 1

PROXY_EXPORT=""
if [[ -n "$TELEGRAM_PROXY_URL" ]]; then
  PROXY_EXPORT="export TELEGRAM_PROXY_URL='${TELEGRAM_PROXY_URL}' HTTP_PROXY='${HTTP_PROXY}' HTTPS_PROXY='${HTTPS_PROXY}' ALL_PROXY='${ALL_PROXY}';"
fi

BOT_LOOP="cd '${PROJECT_DIR}' && ${PROXY_EXPORT} while true; do"
BOT_LOOP+=" echo \"[aahelper-bot] starting at \$(date -Is)\";"
BOT_LOOP+=" ${PYTHON_BIN} bot.py;"
BOT_LOOP+=" code=\$?;"
BOT_LOOP+=" echo \"[aahelper-bot] exited with \$code, restart in ${RESTART_DELAY_SEC}s\";"
BOT_LOOP+=" sleep ${RESTART_DELAY_SEC};"
BOT_LOOP+=" done"

echo "[aahelper] start bot session: $BOT_SESSION"
tmux new -d -s "$BOT_SESSION" "bash -lc $(printf '%q' "$BOT_LOOP")"
tmux set-option -t "$BOT_SESSION" remain-on-exit on

sleep 2

if tmux has-session -t "$BOT_SESSION" 2>/dev/null; then
  echo "[aahelper] $BOT_SESSION: UP"
else
  echo "[aahelper] $BOT_SESSION: DOWN"
  exit 1
fi

echo "[aahelper] sessions:"
tmux ls 2>/dev/null | grep -E "^${BOT_SESSION}:" || tmux ls || true

echo "[aahelper] tail logs:"
tmux capture-pane -pt "$BOT_SESSION" | tail -n 25 || true

echo "[aahelper] attach: tmux attach -t $BOT_SESSION"
echo "[aahelper] done"
