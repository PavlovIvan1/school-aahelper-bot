#!/bin/bash
# Полный цикл деплоя на сервере:
#   1. docker compose up -d --build (бот + admin API + cloudflared tunnel)
#   2. дождаться HTTPS-адреса тоннеля в логах cloudflared
#   3. подставить его в admin-webapp/config.js
#   4. закоммитить и запушить, если адрес поменялся
#
# Использование: ./run.sh

set -euo pipefail
cd "$(dirname "$0")"

CONFIG_FILE="admin-webapp/config.js"
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

echo "[run.sh] Tunnel URL: $URL"

if [ ! -f "$CONFIG_FILE" ]; then
  echo "[run.sh] Не найден $CONFIG_FILE, пропускаю подстановку."
  exit 1
fi

sed -i.bak "s#const API_BASE_URL = \".*\";#const API_BASE_URL = \"$URL\";#" "$CONFIG_FILE"
rm -f "${CONFIG_FILE}.bak"

if git diff --quiet -- "$CONFIG_FILE"; then
  echo "[run.sh] Адрес тоннеля не изменился, config.js без изменений."
else
  git add "$CONFIG_FILE"
  git commit -m "Update admin API tunnel URL"
  git push origin main
  echo "[run.sh] config.js обновлён и запушен: $URL"
  echo "[run.sh] Осталось передеплоить admin-webapp на Vercel с этим изменением."
fi

echo "[run.sh] Готово."
