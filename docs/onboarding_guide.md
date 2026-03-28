# Onboarding Guide

## Назначение

Этот документ нужен для быстрого входа новых разработчиков в проект `voproshalych`.

## Минимальные шаги перед началом работы

1. Перейдите в корень проекта `voproshalych`.
2. Создайте `.env` из шаблона:

```bash
cp .env.example .env
```

## Шаг 1: Настройка переменных окружения

1. Откройте файл `.env` и заполните обязательные значения.
2. Минимально необходимые переменные:

- `TELEGRAM_BOT_TOKEN`:
  1. Откройте Telegram и найдите `@BotFather`.
  2. Создайте бота командой `/newbot`.
  3. Скопируйте токен и вставьте в `.env`.

- `VK_BOT_TOKEN`:
  1. Создайте или откройте сообщество VK.
  2. Включите сообщения сообщества.
  3. Включите Long Poll API для бота.
  4. Создайте ключ доступа сообщества и вставьте в `.env`.

- `MISTRAL_API_KEY`:
  1. Зайдите на `mistral.ai`.
  2. Откройте `Try AI Studio -> API Keys`.
  3. Создайте ключ и вставьте в `.env`.

- `OPENROUTER_API_KEY`:
  1. Зайдите на `openrouter.ai`.
  2. Создайте API key.
  3. Вставьте ключ в `.env`.

- `GIGACHAT_CLIENT_ID` и `GIGACHAT_CLIENT_SECRET`:
  1. Получите доступ у ответственных за интеграцию GigaChat.
  2. Заполните оба значения в `.env`.

- `CONFLUENCE_TOKEN`:
  1. Запросите токен у администраторов проекта.
  2. Убедитесь, что доступ к нужному пространству Confluence открыт.

3. Опциональные переменные:

- `MAX_BOT_TOKEN`: заполняется только если тестируется MAX-бот.
- `HF_TOKEN`: нужен для более быстрой загрузки embedding-модели при сборке.

4. Базовые переменные БД (`POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`) можно оставить значениями из шаблона для локальной разработки.

## Шаг 2: Запуск сервисов

Запустите сервисы в одном из режимов:

- Полный запуск (с MAX-ботом):

```bash
docker compose up -d --build
```

- Запуск без MAX-бота (если `MAX_BOT_TOKEN` не задан):

```bash
docker compose up -d --build postgres db-migrate qa-service bot-core telegram-bot vk-bot
```

- Только backend-контур (без платформенных ботов):

```bash
docker compose up -d --build postgres db-migrate qa-service bot-core
```

## Проверка работоспособности

Проверка статуса сервисов:

```bash
docker compose ps
```

Проверка `qa-service`:

```bash
curl http://localhost:8004/health
```

Тест запроса к QA:

```bash
curl -X POST http://localhost:8004/qa -H "Content-Type: application/json" -d '{"question":"Какие правила приема в магистратуру?"}'
```

## Бэкап базы данных

### Экспорт

Создание дампа с командами DROP (для последующего чистого импорта):

```bash
docker compose exec -T postgres pg_dump -U voproshalych -d voproshalych --clean > voproshalych_db_$(date +%Y%m%d).sql
```

### Импорт

**Вариант 1: База пустая или таблицы не нужны**

```bash
docker compose exec -T postgres psql -U voproshalych -d voproshalych < voproshalych_db_YYYYMMDD.sql
```

**Вариант 2: База уже содержит таблицы (создает ошибки "multiple primary keys")**

Сначала очистите все таблицы в схеме public:

```bash
docker compose exec -T postgres psql -U voproshalych -d voproshalych -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
```

Затем импортируйте дамп:

```bash
docker compose exec -T postgres psql -U voproshalych -d voproshalych < voproshalych_db_YYYYMMDD.sql
```

**Вариант 3: Импорт в новую чистую базу**

1. Удалите том Docker с базой данных:

```bash
docker compose down -v
```

2. Запустите контейнеры заново:

```bash
docker compose up -d postgres
```

3. Дождитесь готовности PostgreSQL (10-15 секунд), затем импортируйте:

```bash
docker compose exec -T postgres psql -U voproshalych -d voproshalych < voproshalych_db_YYYYMMDD.sql
```
