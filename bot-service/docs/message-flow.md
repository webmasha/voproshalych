# Путь сообщения через систему

Этот документ описывает, как сообщение проходит через проект от мессенджера до ответа пользователю, и какие функции участвуют в каждом шаге.

## Общая схема

Для всех платформ схема одинаковая:

1. Платформенный адаптер получает входящее сообщение.
2. Адаптер нормализует сообщение в общий формат `IncomingMessage`.
3. Адаптер отправляет HTTP-запрос в `core` на `POST /messages`.
4. `core` валидирует входные данные и вызывает бизнес-логику.
5. Бизнес-логика возвращает `BotResponse`.
6. Адаптер получает список действий и выполняет их на своей платформе.

## Общие модели core

### `bot-service/core/models/message.py`

#### `Platform`

Enum поддерживаемых платформ:

- `telegram`
- `vk`
- `max`

#### `IncomingMessage`

Нормализованная входная модель для `core`.

Основные поля:

- `platform` — откуда пришло сообщение
- `user_id` — пользователь платформы
- `chat_id` — чат платформы
- `text` — текст сообщения
- `message_id` — идентификатор сообщения
- `timestamp` — время сообщения
- `metadata` — дополнительные поля

Эта модель нужна, чтобы бизнес-логика не зависела от формата Telegram, VK или MAX.

### `bot-service/core/models/response.py`

#### `ActionType`

Типы действий, которые `core` может вернуть адаптеру.

Сейчас реализовано:

- `send_text`

#### `OutgoingAction`

Одно действие для платформенного адаптера.

Основные поля:

- `type` — тип действия
- `text` — текст ответа
- `metadata` — дополнительные параметры действия

#### `BotResponse`

Контейнер для списка действий:

```python
BotResponse(actions=[...])
```

## Путь сообщения в core

### `bot-service/core/main.py`

#### `healthcheck()`

Функция отдает `GET /health`.

Назначение:

- проверка, что сервис поднят
- используется Docker healthcheck

#### `process_message(message: IncomingMessage) -> BotResponse`

Функция обрабатывает `POST /messages`.

Что происходит:

1. FastAPI принимает JSON.
2. Pydantic валидирует JSON как `IncomingMessage`.
3. Вызывается `bot_service.handle_message(message)`.
4. Возвращается `BotResponse`.

### `bot-service/core/services/bot_service.py`

#### `BotService.handle_message(message: IncomingMessage) -> BotResponse`

Главная функция бизнес-логики.

Сейчас она делает следующее:

1. Берет `message.text`.
2. Нормализует текст через `strip()` и `lower()`.
3. Если текст равен `/start`, возвращает приветствие.
4. Если текст равен `/ping`, возвращает `pong`.
5. Иначе возвращает `Echo: <текст>`.
6. Упаковывает ответ в `BotResponse` c действием `send_text`.

Именно эту функцию нужно менять, когда вы добавляете общий функционал бота.

## Путь сообщения в Telegram

Файл:

- `bot-service/bots/telegram/bot.py`

### `main()`

Точка входа Telegram-адаптера.

Что делает:

1. Считывает настройки через `Settings`.
2. Проверяет `TELEGRAM_BOT_TOKEN`.
3. Создает `Bot`.
4. Создает `CoreClient`.
5. Создает `Dispatcher` через `build_dispatcher(core_client)`.
6. Запускает polling через `dispatcher.start_polling(bot)`.

### `Settings`

Хранит настройки Telegram-адаптера:

- `telegram_bot_token`
- `bot_core_url`
- `request_timeout_seconds`

### `CoreClient`

Вспомогательный клиент для связи с `core`.

#### `__init__(settings)`

Создает `httpx.AsyncClient`.

#### `close()`

Закрывает HTTP-клиент.

#### `process_message(message: Message) -> dict[str, Any]`

Что делает:

1. Вызывает `_build_payload(message)`.
2. Отправляет `POST /messages` в `core`.
3. Возвращает JSON-ответ от `core`.

#### `_build_payload(message: Message) -> dict[str, Any]`

Преобразует Telegram-сообщение в общий контракт `IncomingMessage`.

Что именно извлекается:

- `platform = "telegram"`
- `user_id = message.from_user.id`
- `chat_id = message.chat.id`
- `text = message.text`
- `message_id = message.message_id`
- `timestamp = message.date`
- `metadata` с Telegram-специфичными полями

### `build_dispatcher(core_client)`

Создает `Dispatcher` и регистрирует обработчики.

### `handle_text_message(message: Message)`

Внутренний обработчик, зарегистрированный в `build_dispatcher()`.

Что делает:

1. Проверяет, что у сообщения есть текст и `from_user`.
2. Вызывает `core_client.process_message(message)`.
3. Получает `bot_response`.
4. Проходит по `bot_response["actions"]`.
5. Если действие `send_text`, вызывает `message.answer(action["text"])`.
6. Если запрос в `core` упал, отправляет `"Сервис временно недоступен."`

### Итоговый путь Telegram-сообщения

```text
Telegram update
-> dispatcher.start_polling()
-> handle_text_message()
-> CoreClient.process_message()
-> CoreClient._build_payload()
-> POST /messages
-> process_message()
-> BotService.handle_message()
-> BotResponse
-> handle_text_message()
-> message.answer(...)
```

## Путь сообщения в VK

Файл:

- `bot-service/bots/vk/bot.py`

### `main()`

Точка входа VK-адаптера.

Что делает:

1. Считывает настройки через `Settings`.
2. Проверяет `VK_BOT_TOKEN`.
3. Создает `CoreClient`.
4. Создает VK-бот через `build_bot(settings, core_client)`.
5. Запускает long polling через `bot.run_forever()`.

### `Settings`

Хранит настройки VK-адаптера:

- `vk_bot_token`
- `bot_core_url`
- `request_timeout_seconds`

### `CoreClient`

Назначение то же, что и в Telegram-адаптере.

#### `process_message(message: Message)`

Формирует payload и отправляет его в `core`.

#### `_build_payload(message: Message)`

Преобразует VK-сообщение в общий контракт.

Что извлекается:

- `platform = "vk"`
- `user_id = message.from_id`
- `chat_id = message.peer_id`
- `text = message.text`
- `message_id = message.conversation_message_id`
- `timestamp = message.date`
- `metadata` с данными VK

### `build_bot(settings, core_client)`

Создает объект `Bot` и регистрирует обработчик сообщений.

### `handle_text_message(message: Message)`

Внутренний обработчик, зарегистрированный в `build_bot()`.

Что делает:

1. Проверяет, что сообщение содержит текст.
2. Вызывает `core_client.process_message(message)`.
3. Получает ответ `core`.
4. Проходит по `actions`.
5. Для `send_text` вызывает `message.answer(action["text"])`.
6. При ошибке запроса в `core` отправляет fallback-сообщение.

### Итоговый путь VK-сообщения

```text
VK long polling
-> bot.run_forever()
-> handle_text_message()
-> CoreClient.process_message()
-> CoreClient._build_payload()
-> POST /messages
-> process_message()
-> BotService.handle_message()
-> BotResponse
-> handle_text_message()
-> message.answer(...)
```

## Путь сообщения в MAX

Файл:

- `bot-service/bots/max/main.go`

### `main()`

Точка входа MAX-адаптера.

Что делает:

1. Считывает настройки через `NewSettings()`.
2. Проверяет `MAX_BOT_TOKEN`.
3. Создает контекст с graceful shutdown.
4. Создает API-клиент через `maxbot.New(settings.MaxBotToken)`.
5. Создает HTTP-клиент для `core` через `NewCoreClient(settings)`.
6. Читает обновления через `api.GetUpdates(ctx)`.
7. Для каждого update вызывает `handleUpdate(ctx, api, coreClient, update)`.

### `NewSettings()`

Читает настройки из переменных окружения:

- `MAX_BOT_TOKEN`
- `BOT_CORE_URL`
- `BOT_CORE_TIMEOUT_SECONDS`

### `NewCoreClient(settings)`

Создает Go HTTP-клиент для вызова `core`.

### `CoreClient.ProcessMessage(ctx, payload)`

Что делает:

1. Сериализует `IncomingMessage` в JSON.
2. Создает `POST` запрос на `/messages`.
3. Отправляет запрос в `core`.
4. Проверяет HTTP-статус.
5. Декодирует JSON в `BotResponse`.

### `handleUpdate(ctx, api, coreClient, update)`

Главная функция обработки событий MAX.

Что делает:

1. Проверяет, что update имеет тип `*schemes.MessageCreatedUpdate`.
2. Берет текст из `messageUpdate.Message.Body.Text`.
3. Если текста нет, завершает обработку.
4. Вызывает `buildIncomingMessage(messageUpdate)`.
5. Отправляет payload в `core` через `coreClient.ProcessMessage(...)`.
6. Если `core` недоступен, вызывает `sendFallbackMessage(...)`.
7. Если ответ получен, проходит по `response.Actions`.
8. Для `send_text` создает сообщение через `maxbot.NewMessage()`.
9. Вызывает `api.Messages.Send(ctx, message)`.

### `buildIncomingMessage(update)`

Преобразует MAX update в общий формат `IncomingMessage`.

Что извлекается:

- `platform = "max"`
- `user_id` из `message.Sender.UserId`
- `chat_id` из `message.Recipient.ChatId` или `message.Recipient.UserId`
- `text` из `message.Body.Text`
- `message_id` из `message.Body.Mid`
- `timestamp` из `message.Timestamp`
- `metadata["sender_name"]`

### `sendFallbackMessage(ctx, api, update)`

Отправляет пользователю сообщение `"Сервис временно недоступен."`, если `core` не ответил.

### Итоговый путь MAX-сообщения

```text
MAX update
-> api.GetUpdates(ctx)
-> handleUpdate()
-> buildIncomingMessage()
-> CoreClient.ProcessMessage()
-> POST /messages
-> process_message()
-> BotService.handle_message()
-> BotResponse
-> handleUpdate()
-> api.Messages.Send(...)
```

## Что возвращает core и как это исполняется

Сейчас `core` всегда возвращает `BotResponse`, внутри которого список `actions`.

Пример:

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

На стороне адаптеров это означает:

- Telegram: `message.answer(text)`
- VK: `message.answer(text)`
- MAX: `api.Messages.Send(...)`

## Где расширять путь обработки

Если нужно добавить новую возможность, смотреть нужно в такие точки:

### Новый сценарий бизнес-логики

Менять:

- `bot-service/core/services/bot_service.py`

### Новые поля входящего сообщения

Менять:

- `bot-service/core/models/message.py`
- соответствующий `_build_payload()` или `buildIncomingMessage()` в адаптере

### Новый тип действия

Менять:

- `bot-service/core/models/response.py`
- `bot-service/core/services/bot_service.py`
- обработчики ответа в Telegram, VK и MAX адаптерах

## Краткое резюме

Главная идея проекта:

- адаптеры знают, как общаться с платформой
- `core` знает, как принимать решения
- общий контракт между ними позволяет держать бизнес-логику в одном месте
