# Тестирование и запуск QA-сервиса

## Быстрые команды

### Запуск сервиса

```bash
# Локально с переменными окружения
MISTRAL_API_KEY=your_key \
OPENROUTER_API_KEY=your_key \
uv run uvicorn qa.main:app --host 0.0.0.0 --port 8004

# Через Docker
docker compose up -d qa-service
```

### Проверка работоспособности

```bash
# Health check
curl http://localhost:8004/health

# Тестовый запрос (LightRAG с fallback)
curl -X POST http://localhost:8004/qa \
  -H "Content-Type: application/json" \
  -d '{"question": "Какие правила приёма в ТюмГУ?"}'

# Только LightRAG
curl -X POST http://localhost:8004/qa/lightrag \
  -H "Content-Type: application/json" \
  -d '{"question": "Какие правила приёма?"}'

# Только Classic RAG
curl -X POST http://localhost:8004/qa/classic \
  -H "Content-Type: application/json" \
  -d '{"question": "Какие правила приёма?"}'
```

### Запуск тестов

```bash
# Все тесты
uv run pytest

# Только unit-тесты
uv run pytest tests/unit/

# Только интеграционные тесты
uv run pytest tests/integration/

# С покрытием кода
uv run pytest --cov=src --cov-report=html
```

### Docker команды

```bash
# Сборка образа
docker compose build qa-service

# Запуск с PostgreSQL
docker compose up -d postgres qa-service

# Логи
docker compose logs qa-service

# Остановка
docker compose down
```

## Тестирование LightRAG

### Проверка статуса LightRAG

```bash
# Статус инициализации
curl http://localhost:8004/health

# Логи LightRAG
docker compose logs qa-service | grep -i "lightrag"
```

### Тестирование графа знаний

```bash
# Проверить расширения PostgreSQL
docker compose exec -T postgres psql -U voproshalych -d voproshalych -c \
  "SELECT * FROM pg_extension WHERE extname IN ('vector', 'age');"

# Проверить таблицы графа
docker compose exec -T postgres psql -U voproshalych -d voproshalych -c \
  "\dt" | grep lightrag
```

### Импорт и построение графа

```bash
# Импорт чанков в LightRAG (включает KG extraction)
curl -X POST http://localhost:8004/kb/import-to-lightrag

# Статус импорта
curl http://localhost:8004/kb/index-status

# История версий
curl http://localhost:8004/kb/index-versions
```

### Проверка fallback

```bash
# Остановить LightRAG (симуляция)
# Отправить запрос - должен fallback на classic RAG
curl -X POST http://localhost:8004/qa \
  -H "Content-Type: application/json" \
  -d '{"question": "тест fallback"}'
```

## Структура тестов

### Unit-тесты

- `tests/unit/test_llm_pool.py` — тесты LLM Pool
- `tests/unit/test_providers.py` — тесты провайдеров

### Интеграционные тесты

- `tests/integration/test_qa_api.py` — тесты API
- `tests/integration/test_lightrag.py` — тесты LightRAG

## Частые проблемы

### Ошибка "No available LLM providers"

Проверьте переменные окружения:

```bash
echo $MISTRAL_API_KEY
echo $OPENROUTER_API_KEY
```

### Ошибка подключения к PostgreSQL

```bash
docker compose ps
docker compose logs postgres
```

### LightRAG не инициализируется

```bash
# Проверить расширения
docker compose exec -T postgres psql -U voproshalych -d voproshalych -c \
  "SELECT * FROM pg_extension WHERE extname = 'age';"

# Проверить логи
docker compose logs qa-service | grep -i error
```

### Тесты падают с ошибкой импорта

```bash
uv sync
```

## Конфигурация

### Переменные окружения

| Переменная | Описание | По умолчанию |
|------------|----------|--------------|
| `MISTRAL_API_KEY` | API ключ Mistral AI | - |
| `OPENROUTER_API_KEY` | API ключ OpenRouter | - |
| `GIGACHAT_CLIENT_ID` | Client ID GigaChat | - |
| `GIGACHAT_CLIENT_SECRET` | Client Secret GigaChat | - |
| `MODEL_PRIORITY` | Порядок провайдеров | `openrouter,gigachat,mistral` |
| `POSTGRES_HOST` | Хост PostgreSQL | `postgres` |
| `POSTGRES_DB` | Имя БД | `voproshalych` |
| `POSTGRES_USER` | Пользователь БД | `voproshalych` |
| `POSTGRES_PASSWORD` | Пароль БД | `voproshalych` |
| `USE_LIGHT_RAG` | Включить LightRAG | `true` |
| `LIGHT_RAG_USE_PG_GRAPH` | Использовать PG для графа | `true` |
| `LIGHT_RAG_MODEL_NAME` | Имя модели эмбеддингов | `deepvk-user-bge-m3` |

### Таймауты

| Параметр | Значение |
|----------|----------|
| LightRAG timeout | 20 сек |
| Classic RAG timeout | 15 сек |
| Max retries | 3 |
