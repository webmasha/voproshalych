# Вопрошалыч v2

Виртуальный помощник студента ТюмГУ.

## Архитектура

Проект построен на принципах микросервисной архитектуры. Основные компоненты:

- **Платформенные адаптеры** (telegram-bot, vk-bot, max-bot) — получают сообщения от пользователей и нормализуют их в единый формат
- **Core** — центральный сервис с диалоговой логикой, управлением состояниями, сессиями и обработкой ошибок
- **QA Service** — сервис вопросов-ответов с LLM Pool и Knowledge Base
- **PostgreSQL + pgvector** — единая база данных для хранения пользователей, сообщений, чанков и эмбеддингов

## Компоненты

### Bot Service (Платформенные адаптеры)

- **telegram-bot** — Адаптер для Telegram (aiogram)
- **vk-bot** — Адаптер для VK (vkbottle)
- **max-bot** — Адаптер для MAX

Каждый адаптер получает сообщения от платформы, нормализует в единый формат IncomingMessage, отправляет в core и выполняет действия на платформе.

### Core (:8000)

Центральный сервис диалоговой логики:
- Управление состояниями (START, DIALOG, WAITING_ANSWER)
- Управление сессиями
- Обработка ошибок
- Subscription сервис (рассылки)
- Holiday сервис (поздравления)

### QA Service (:8004)

Сервис вопросов-ответов с LLM Pool:
- **LLM Pool** — Пул провайдеров с автоматическим fallback:
  - Mistral AI (open-mistral-nemo) — по умолчанию
  - OpenRouter (openrouter/free) — fallback
  - GigaChat (GigaChat) — fallback

- **Knowledge Base** — База знаний (Этап 2):
  - Chunking — разбиение на чанки
  - Embeddings — векторные представления (deepvk/USER-bge-m3)
  - Vector Search — семантический поиск

### Database (PostgreSQL + pgvector)

Единая база данных voproshalych:
- users — Пользователи платформ
- sessions — Сессии
- messages — Сообщения
- chunks — Чанки базы знаний
- embeddings — Векторные представления
- subscriptions — Подписки на рассылки
- holidays — Праздники

## Быстрый старт

### Требования

- Docker и Docker Compose
- Python 3.12+ (для локальной разработки)
- UV (менеджер пакетов)

### Запуск через Docker Compose

```bash
git clone https://github.com/webmasha/voproshalych.git
cd voproshalych
docker compose up -d
```

### Проверка работы

```bash
curl http://localhost:8004/health

curl -X POST http://localhost:8004/qa \
  -H "Content-Type: application/json" \
  -d '{"question": "Привет, кто ты?"}'
```

## Разработка

### Структура проекта

- **bot-service/** — Платформенные адаптеры
  - **core/** — Диалоговая логика
  - **bots/** — Telegram, VK, MAX адаптеры
- **qa-service/** — QA сервис с LLM
  - **src/qa/** — Исходный код
    - **api/** — API routes
    - **llm/** — LLM Pool
    - **models/** — Модели данных
  - **tests/** — Тесты
  - **docs/** — Документация
- **db/** — Пакет для работы с базой данных
  - **src/voproshalych_db/** — SQLAlchemy модели
  - **migration/** — Alembic миграции
- **docker-compose.yml** — Конфигурация Docker Compose

### Локальная разработка

#### QA Service

```bash
cd qa-service
uv sync
uv run uvicorn qa.main:app --reload
```

#### Тесты

```bash
uv run pytest
uv run pytest --cov=src
```

### Конфигурация

Переменные окружения в .env:

```bash
# Database
POSTGRES_HOST=postgres
POSTGRES_DB=voproshalych
POSTGRES_USER=voproshalych
POSTGRES_PASSWORD=voproshalych

# LLM Providers
MISTRAL_API_KEY=your_key
OPENROUTER_API_KEY=your_key
GIGACHAT_CLIENT_ID=your_id
GIGACHAT_CLIENT_SECRET=your_secret
```

## Документация

- QA Service — Путь запроса: qa-service/docs/message-flow.md
- QA Service — Тестирование: qa-service/docs/testing.md
- Bot Service — Разработка ботов: bot-service/docs/bot-development.md

## Технологический стек

- Python 3.12 — Язык программирования
- FastAPI — Веб-фреймворк
- PostgreSQL + pgvector — База данных
- Docker + Docker Compose — Контейнеризация
- UV — Менеджер пакетов
- LangGraph — Agent Framework (Этап 2)

### LLM Providers

| Провайдер | Модель | Статус |
|-----------|--------|--------|
| Mistral AI | open-mistral-nemo | По умолчанию |
| OpenRouter | openrouter/free | Fallback |
| GigaChat | GigaChat | Fallback |

### Embeddings

Модель: deepvk/USER-bge-m3 (1024 измерения)

## Roadmap

### Этап 1: MVP

- [x] LLM Pool с fallback
- [x] QA Service API
- [x] PostgreSQL + pgvector
- [x] Docker Compose

### Этап 2: Knowledge Base

- [ ] Document Downloader (парсинг сайтов)
- [ ] Chunking (разбиение на чанки)
- [ ] Embeddings (векторные представления)
- [ ] Vector Search (семантический поиск)

### Этап 3: Agent

- [ ] ReAct Agent на LangGraph
- [ ] Tools: Confluence, Web Scraper
- [ ] Agent Cache

## Лицензия

MIT
