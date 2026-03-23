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

# Тестовый запрос
curl -X POST http://localhost:8004/qa \
  -H "Content-Type: application/json" \
  -d '{"question": "Какие правила приёма в ТюмГУ?"}'
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

## Структура тестов

### Unit-тесты

- `tests/unit/test_llm_pool.py` — тесты LLM Pool
- `tests/unit/test_providers.py` — тесты провайдеров

### Интеграционные тесты

- `tests/integration/test_qa_api.py` — тесты API

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

### Тесты падают с ошибкой импорта

```bash
uv sync
```

## Конфигурация

### Переменные окружения

| Переменная | Описание |
|------------|----------|
| `MISTRAL_API_KEY` | API ключ Mistral AI |
| `OPENROUTER_API_KEY` | API ключ OpenRouter |
| `GIGACHAT_CLIENT_ID` | Client ID GigaChat |
| `GIGACHAT_CLIENT_SECRET` | Client Secret GigaChat |
| `MODEL_PRIORITY` | Порядок провайдеров |
| `POSTGRES_HOST` | Хост PostgreSQL |
| `POSTGRES_DB` | Имя БД |
| `POSTGRES_USER` | Пользователь БД |
| `POSTGRES_PASSWORD` | Пароль БД |
