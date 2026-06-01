# Docker — helper-бот (school-aahelperbot)

Отдельная папка на сервере, свой `docker compose` — без основного бота.

## Запуск

```bash
cd /path/to/school-aahelperbot
cp .env.docker.example .env.docker   # опционально, если нужны только overrides
docker compose up -d --build
docker compose logs -f bot
```

Секреты: `BOT_TOKEN`, `OMNIDESK_WEBHOOK_URL`, прокси — в `.env`.

## Миграция с tmux

```bash
tmux kill-session -t aahelper-bot 2>/dev/null || true
docker compose up -d --build
```

Не запускайте одновременно tmux и Docker на одном `BOT_TOKEN`.

## Пока без Docker

`./run_tmux.sh` — см. `TMUX_RUNBOOK.md`.
