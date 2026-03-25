# Вопрошалыч v2

Новая версия виртуального помощника студента ТюмГУ.

Заказчик: ФГАОУ ВО «Тюменский государственный университет», управление по сопровождению студентов «Единый деканат».

Исполнители: Ефимова Мария Александровна, Горохов Константин Алексеевич, Батыев Рамиль Рустамович, Мустаков Максим Рашитович.

Проект переписывается с нуля и заменяет предыдущую реализацию 2023 года.

## Что делает система

1. Принимает вопросы студентов в VK, Telegram и MAX.
2. Ищет информацию в официальных источниках ТюмГУ (Confluence, sveden.utmn.ru, utmn.ru).
3. Генерирует ответ через LLM и, когда нужно, добавляет ссылки на источники.
4. Сохраняет пользователей, сообщения и историю Q/A в PostgreSQL.

## Архитектура

1. `bot-service` — платформенные адаптеры и `bot-core` с диалоговой логикой.
2. `qa-service` — retrieval + generation, LLM pool, база знаний.
3. `db` — миграции и схема данных.
4. `postgres` + `pgvector` — хранение и векторный поиск.

## Быстрый запуск

1. Скопируй переменные окружения:

```bash
cp .env.example .env
```

2. Запусти все сервисы (включая MAX-бот):

```bash
docker compose up -d --build
```

3. Запусти сервисы без MAX-бота (если `MAX_BOT_TOKEN` не задан):

```bash
docker compose up -d --build postgres db-migrate qa-service bot-core telegram-bot vk-bot
```

4. Запусти только backend-контур без платформенных ботов:

```bash
docker compose up -d --build postgres db-migrate qa-service bot-core
```

## Полезные команды

Проверка состояния:

```bash
docker compose ps
```

Проверка QA health:

```bash
curl http://localhost:8004/health
```

Тест запроса к QA:

```bash
curl -X POST http://localhost:8004/qa -H "Content-Type: application/json" -d '{"question":"Какие правила приема в магистратуру?"}'
```

## Бэкап базы

Экспорт:

```bash
docker compose exec -T postgres pg_dump -U voproshalych -d voproshalych > voproshalych_db_$(date +%Y%m%d).sql
```

Импорт:

```bash
docker compose exec -T postgres psql -U voproshalych -d voproshalych < voproshalych_db_YYYYMMDD.sql
```

## Документация

- `docs/pipeline-user-query.md`
- `qa-service/docs/KB_FILL_GUIDE.md`
- `qa-service/docs/testing.md`
- `qa-service/docs/message-flow.md`
