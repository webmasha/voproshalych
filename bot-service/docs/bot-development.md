# Разработка и запуск ботов

Проект построен как набор платформенных адаптеров для ботов и общего `core`-сервиса с бизнес-логикой.

## Архитектура

Структура проекта:

```text
.
├── .env
├── docker-compose.yml
└── bot-service
    ├── pyproject.toml
    ├── core
    │   ├── config.py
    │   ├── main.py
    │   ├── models
    │   │   ├── message.py
    │   │   └── response.py
    │   └── services
    │       └── bot_service.py
    ├── bots
    │   ├── telegram
    │   │   └── bot.py
    │   ├── vk
    │   │   └── bot.py
    │   └── max
    │       └── main.go
    └── docs
        └── bot-development.md
```

Поток обработки сообщения:

1. Пользователь пишет в Telegram, VK или MAX.
2. Адаптер платформы принимает update.
3. Адаптер приводит update к общей модели `IncomingMessage`.
4. Адаптер отправляет `POST /messages` в `core`.
5. `core` выполняет бизнес-логику и возвращает `BotResponse`.
6. Адаптер выполняет действия из ответа, например отправляет текст пользователю.

Разделение ответственности:

- `core` отвечает за общую бизнес-логику.
- `bots/telegram`, `bots/vk`, `bots/max` отвечают только за интеграцию с платформой.
- Платформенно-специфичные детали не должны попадать в бизнес-логику без необходимости.

## Где писать функционал

Основная точка разработки функционала:

- `bot-service/core/services/bot_service.py`

Именно здесь должна жить общая логика:

- обработка команд
- роутинг сценариев
- вызовы внешних сервисов
- работа с базой данных
- валидация входящих данных
- генерация ответа для платформ

Сейчас базовый метод выглядит так:

```python
def handle_message(self, message: IncomingMessage) -> BotResponse:
    ...
```

На вход приходит уже нормализованное сообщение, поэтому внутри `core` не нужно разбирать Telegram/VK/MAX-форматы.

## Общий контракт между адаптерами и core

Входящая модель описана в:

- `bot-service/core/models/message.py`

Основные поля:

- `platform` — платформа: `telegram`, `vk`, `max`
- `user_id` — идентификатор пользователя на платформе
- `chat_id` — идентификатор чата на платформе
- `text` — текст сообщения
- `message_id` — идентификатор сообщения
- `timestamp` — время сообщения
- `metadata` — дополнительные поля платформы

Выходная модель описана в:

- `bot-service/core/models/response.py`

Сейчас поддерживается действие:

- `send_text`

То есть `core` не отправляет сообщение сам, а говорит адаптеру, что нужно сделать.

## Как добавлять новую бизнес-логику

Базовый порядок такой:

1. Добавить или изменить поведение в `BotService.handle_message()`.
2. Если нужно, расширить `IncomingMessage`.
3. Если нужен новый тип ответа, расширить `ActionType` и `OutgoingAction`.
4. После этого реализовать поддержку нового действия в нужных адаптерах.

Пример: если понадобится отправка изображения, порядок будет таким:

1. В `core/models/response.py` добавить новый тип действия, например `send_image`.
2. В `BotService` вернуть это действие при нужном сценарии.
3. В адаптерах Telegram/VK/MAX реализовать, как именно платформа отправляет изображение.

Важно:

- сначала расширяется общий контракт
- потом бизнес-логика
- потом платформенные адаптеры

Не наоборот.

## Как писать адаптеры платформ

Адаптер платформы должен делать только три вещи:

1. Получить update от платформы.
2. Преобразовать update в `IncomingMessage`.
3. Отправить запрос в `core` и выполнить `BotResponse`.

Файлы адаптеров:

- `bot-service/bots/telegram/bot.py`
- `bot-service/bots/vk/bot.py`
- `bot-service/bots/max/main.go`

Если добавляется новая платформа, ориентир такой же:

1. создать новый адаптер
2. нормализовать входящие события
3. слать их в `core`
4. исполнять ответ `core`

## Запуск проекта

Настройки окружения лежат в:

- `.env`

Минимальные переменные:

- `BOT_CORE_APP_NAME`
- `BOT_CORE_APP_VERSION`
- `BOT_CORE_URL`
- `BOT_CORE_TIMEOUT_SECONDS`
- `TELEGRAM_BOT_TOKEN`
- `VK_BOT_TOKEN`
- `MAX_BOT_TOKEN`

Перед запуском нужно заполнить токены нужных платформ.

Запуск всех сервисов:

```bash
docker compose up --build
```

Запуск только одного сервиса:

```bash
docker compose up --build core
docker compose up --build telegram-bot
docker compose up --build vk-bot
docker compose up --build max-bot
```

Пересборка конкретного сервиса:

```bash
docker compose build --no-cache core
docker compose build --no-cache telegram-bot
docker compose build --no-cache vk-bot
docker compose build --no-cache max-bot
```

## Локальный HTTP API core

`core` поднимает FastAPI и имеет два основных endpoint:

- `GET /health`
- `POST /messages`

Файл приложения:

- `bot-service/core/main.py`

Пример запроса в `core`:

```bash
curl -X POST http://localhost:8000/messages \
  -H "Content-Type: application/json" \
  -d '{
    "platform": "telegram",
    "user_id": "123",
    "chat_id": "123",
    "text": "/ping",
    "metadata": {}
  }'
```

Пример ответа:

```json
{
  "actions": [
    {
      "type": "send_text",
      "text": "pong",
      "metadata": {}
    }
  ]
}
```

## Зависимости

Python-зависимости описаны в:

- `bot-service/pyproject.toml`

Они разделены по группам:

- `core`
- `telegram`
- `vk`

Это сделано для того, чтобы каждый контейнер ставил только свои зависимости.

## Рекомендации по разработке

- Общую логику пишите в `core`, а не в адаптерах.
- Не завязывайте `core` на Telegram/VK/MAX-специфику без крайней необходимости.
- Если поведение должно работать одинаково на всех платформах, оно должно жить в `core`.
- Если поведение зависит от API платформы, оно должно жить в адаптере.
- Любое новое действие сначала оформляйте как часть общего контракта.

## Текущее состояние

Сейчас реализовано:

- общий FastAPI `core`
- Telegram-адаптер на `aiogram`
- VK-адаптер на `vkbottle`
- MAX-адаптер на `max-bot-api-client-go`
- запуск через Docker Compose
