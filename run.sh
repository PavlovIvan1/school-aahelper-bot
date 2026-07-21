#!/bin/bash
# Полный цикл на сервере, без внешних сервисов (Vercel и т.п. не нужны —
# admin_api.py сам отдаёт и API, и статику мини-аппа с одного порта):
#   1. docker compose up -d --build (бот + admin API/webapp + cloudflared tunnel)
#   2. дождаться HTTPS-адреса тоннеля в логах cloudflared
#   3. вписать его в .env как ADMIN_WEBAPP_URL
#   4. если адрес изменился — пересоздать контейнер бота, чтобы кнопка
#      /admin вела на актуальный адрес
#
# Использование: ./run.sh

set -euo pipefail
cd "$(dirname "$0")"

ENV_FILE=".env"
WAIT_ATTEMPTS=30
WAIT_DELAY=2

if [ ! -f "$ENV_FILE" ]; then
  echo "[run.sh] Не найден $ENV_FILE — создайте его (cp .env.example .env) и заполните перед первым запуском."
  exit 1
fi

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

CURRENT=$(grep -E '^ADMIN_WEBAPP_URL=' "$ENV_FILE" | tail -1 | cut -d= -f2- || true)

if [ "$CURRENT" = "$URL" ]; then
  echo "[run.sh] ADMIN_WEBAPP_URL в .env уже актуален ($URL), перезапуск бота не требуется."
else
  if grep -q '^ADMIN_WEBAPP_URL=' "$ENV_FILE"; then
    sed -i.bak "s#^ADMIN_WEBAPP_URL=.*#ADMIN_WEBAPP_URL=$URL#" "$ENV_FILE"
  else
    echo "ADMIN_WEBAPP_URL=$URL" >> "$ENV_FILE"
  fi
  rm -f "${ENV_FILE}.bak"
  echo "[run.sh] Обновил ADMIN_WEBAPP_URL в .env -> $URL"
  echo "[run.sh] Пересоздаю контейнер бота, чтобы подхватил новый .env..."
  docker compose up -d --force-recreate bot
fi

echo "[run.sh] Готово. Мини-апп и API живут на: $URL"
echo "[run.sh] В боте: /admin -> кнопка откроет актуальную панель."
