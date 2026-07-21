#!/bin/bash
# Поднимает стек на сервере и печатает HTTPS-адрес тоннеля:
#   1. docker compose up -d --build (бот + admin API + cloudflared tunnel)
#   2. дождаться HTTPS-адреса тоннеля в логах cloudflared
#   3. напечатать его
#
# Git на сервере не трогаем (никаких commit/push отсюда) — URL просто
# скопируйте и передайте туда, где обновляется admin-webapp/config.js.
#
# Использование: ./run.sh

set -euo pipefail
cd "$(dirname "$0")"

WAIT_ATTEMPTS=30
WAIT_DELAY=2

echo "[run.sh] docker compose up -d --build"
docker compose up -d --build

echo "[run.sh] Жду HTTPS-адрес тоннеля от cloudflared..."
URL=""
for i in $(seq 1 "$WAIT_ATTEMPTS"); do
  URL=$(docker compose logs cloudflared 2>/dev/null \
    | grep -oE 'https://[a-zA-Z0-9.-]+\.trycloudflare\.com' \
    | tail -1 || true)
  if [ -n "$URL" ]; then
    break
  fi
  sleep "$WAIT_DELAY"
done

if [ -z "$URL" ]; then
  echo "[run.sh] Не нашёл адрес тоннеля за $((WAIT_ATTEMPTS * WAIT_DELAY))с."
  echo "[run.sh] Смотри логи вручную: docker compose logs cloudflared"
  exit 1
fi

echo "[run.sh] Готово. Tunnel URL: $URL"
echo "[run.sh] Скопируйте этот адрес — его нужно вписать в admin-webapp/config.js и передеплоить на Vercel."
