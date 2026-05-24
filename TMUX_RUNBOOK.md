# Запуск бота поддержки (aahelper) в tmux

## Быстрый старт

```bash
cd /path/to/school-aahelperbot
cp .env.example .env   # если ещё нет
# отредактируйте .env — BOT_TOKEN

chmod +x run_tmux.sh
./run_tmux.sh
```

Если ошибка `bash\r: No such file or directory` — у файла Windows-переводы строк. На сервере:

```bash
sed -i 's/\r$//' run_tmux.sh
chmod +x run_tmux.sh
./run_tmux.sh
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

## Прокси (опционально)

```bash
TELEGRAM_PROXY_URL='http://user:pass@host:port' ./run_tmux.sh
```

## Переменные

| Переменная | По умолчанию | Описание |
|------------|--------------|----------|
| `AAHELPER_PROJECT_DIR` | каталог скрипта | Путь к проекту |
| `AAHELPER_BOT_SESSION` | `aahelper-bot` | Имя tmux-сессии |
| `PYTHON_BIN` | `python3` | Интерпретатор |
| `RESTART_DELAY_SEC` | `5` | Пауза перед рестартом |
