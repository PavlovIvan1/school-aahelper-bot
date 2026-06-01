# Запуск бота поддержки (aahelper) в tmux

## Быстрый старт

```bash
cd /path/to/school-aahelperbot
cp .env.example .env   # если ещё нет
# отредактируйте .env — BOT_TOKEN

git pull
bash after_pull.sh    # после каждого pull (убирает CRLF из .sh)
./run_tmux.sh
```

### Почему после `git pull` ломается `run_tmux.sh`

Файл когда-то попал в репозиторий с окончаниями строк Windows (`CRLF`). На Linux shebang читается как `bash\r` → ошибка `/usr/bin/env: 'bash\r'`.

**На сервере после pull:**

```bash
bash after_pull.sh
# или одной строкой:
sed -i 's/\r$//' run_tmux.sh && chmod +x run_tmux.sh
```

**Один раз у того, кто коммитит (Windows/WSL), чтобы больше не тащить CRLF:**

```bash
git add --renormalize .
git commit -m "Normalize line endings to LF"
git push
```

На сервере можно задать каталог явно:

```bash
AAHELPER_PROJECT_DIR=/root/school-aahelperbot ./run_tmux.sh
```

## Сессия

| Имя | Процесс |
|-----|---------|
| `aahelper-bot` | `python3 bot.py` (с автоперезапуском при падении) |

## Полезные команды

Список сессий:

```bash
tmux ls
```

Подключиться к логам:

```bash
tmux attach -t aahelper-bot
```

Отключиться: `Ctrl+b`, затем `d`.

Остановить:

```bash
tmux kill-session -t aahelper-bot
```

Хвост лога без attach:

```bash
tmux capture-pane -pt aahelper-bot | tail -n 40
```

## Прокси (для РФ)

По умолчанию тот же прокси, что у `school-aabot` (см. `TELEGRAM_PROXY_URL` в `.env`).

```bash
# в .env:
TELEGRAM_PROXY_URL=http://user:pass@host:port
```

`run_tmux.sh` пробрасывает `TELEGRAM_PROXY_URL`, `HTTP_PROXY`, `HTTPS_PROXY`, `ALL_PROXY` в процесс бота.

## Docker (отдельно от основного бота)

См. `DOCKER.md` в этой же папке.

## Переменные

| Переменная | По умолчанию | Описание |
|------------|--------------|----------|
| `AAHELPER_PROJECT_DIR` | каталог скрипта | Путь к проекту |
| `AAHELPER_BOT_SESSION` | `aahelper-bot` | Имя tmux-сессии |
| `PYTHON_BIN` | `python3` | Интерпретатор |
| `RESTART_DELAY_SEC` | `5` | Пауза перед рестартом |
