# Гайд по созданию графа знаний (Knowledge Graph)

## Обзор

LightRAG использует **гибридный поиск**:
- **Векторный поиск** (pgvector) — семантическое сходство
- **Граф знаний** (Apache AGE) — связи между сущностями

При импорте чанков LightRAG автоматически:
1. Создаёт эмбеддинги для векторного поиска
2. Извлекает **сущности** (entities) из текста
3. Извлекает **связи** (relations) между сущностями
4. Строит **граф знаний** в PostgreSQL (через AGE)

## Какой LLM используется для графа?

При построении графа используется **LLM Pool** (в порядке приоритета):
1. Mistral (open-mistral-nemo)
2. OpenRouter (openrouter/free)
3. GigaChat

Для **качества графа** рекомендуется использовать более мощные модели. Можно настроить отдельную модель для индексации через `LIGHT_RAG_LLM_FOR_INDEXING`.

## Создание графа

### Полный цикл: импорт чанков + граф

```bash
# Импортировать все чанки в LightRAG и создать граф
curl -X POST http://localhost:8004/kb/import-to-lightrag
```

Это:
1. Возьмёт все чанки из таблицы `chunks`
2. Пропустит неизменившиеся (дедупликация по hash)
3. Создаст векторные представления в PostgreSQL
4. Извлечёт сущности и связи через LLM
5. Сохранит граф в PostgreSQL (таблицы `lightrag_vdb_entity_*`, `lightrag_vdb_relation_*`)

### Только перестроить граф (без импорта)

```bash
curl -X POST http://localhost:8004/kb/rebuild-knowledge-graph
```

Используется если нужно обновить граф без переиндексации чанков.

### С версией

```bash
# Создать новую версию индекса
curl -X POST http://localhost:8004/kb/import-to-lightrag \
  -H "Content-Type: application/json" \
  -d '{"notes": "First full import with KG"}'

# Проверить статус
curl http://localhost:8004/kb/index-status
```

## Проверка графа

### Таблицы в PostgreSQL

```bash
docker compose exec -T postgres psql -U voproshalych -d voproshalych -c \
  "\dt" | grep lightrag
```

Должны быть таблицы:
- `lightrag_vdb_entity_*` — сущности
- `lightrag_vdb_relation_*` — связи между сущностями

### Проверить сущности

```bash
docker compose exec -T postgres psql -U voproshalych -d voproshalych -c \
  "SELECT entity_type, COUNT(*) FROM lightrag_vdb_entity_deepvk_user_bge_m3_1024d GROUP BY entity_type LIMIT 10;"
```

### Проверить связи

```bash
docker compose exec -T postgres psql -U voproshalych -d voproshalych -c \
  "SELECT relation_type, COUNT(*) FROM lightrag_vdb_relation_deepvk_user_bge_m3_1024d GROUP BY relation_type LIMIT 10;"
```

## Версионирование

Каждый импорт создаёт версию:

```bash
# Список версий
curl http://localhost:8004/kb/index-versions

# Ответ:
# {
#   "versions": [
#     {"version_id": "v-20260327-052000-abc123", "status": "completed", ...},
#     {"version_id": "v-20260327-051500-def456", "status": "completed", ...}
#   ]
# }
```

### Параметры импорта

| Параметр | Описание |
|----------|----------|
| `chunk_ids` | Конкретные ID чанков (опционально) |
| `limit` | Лимит чанков для обработки |
| `version_id` | Кастомный ID версии |
| `notes` | Заметки к версии |

Пример:

```bash
curl -X POST http://localhost:8004/kb/import-to-lightrag \
  -H "Content-Type: application/json" \
  -d '{
    "limit": 100,
    "version_id": "v-experiment-001",
    "notes": "Тестирование качества графа"
  }'
```

## Частые вопросы

### Сколько времени занимает создание графа?

- ~374 чанков обрабатываются около 10-15 минут
- Зависит от количества LLM вызовов для извлечения сущностей
- Можно отслеживать в логах: `Phase 1: Processing X entities`

### Какие сущности извлекаются?

LightRAG извлекает:
- Имена (людей, организаций)
- Даты и события
- Термины и понятия
- Любые сущности, которые LLM считает релевантными

### Как обновить граф после добавления новых чанков?

```bash
# Добавить новые чанки через KB
curl -X POST http://localhost:8004/kb/documents \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.ru/new-doc"}'

# Затем импортировать
curl -X POST http://localhost:8004/kb/import-to-lightrag
```

Новые чанки будут добавлены, старые пропущены (дедупликация).

### Можно ли использовать другую модель для графа?

Да, для этого нужно настроить `LIGHT_RAG_LLM_FOR_INDEXING` в `.env`:

```bash
# Использовать OpenRouter для индексации
LIGHT_RAG_LLM_FOR_INDEXING=openrouter/free
```

## Рекомендации

1. **Первичный импорт**: Запустите на всех чанках с версией "v1.0"
2. **Мониторинг**: Проверяйте `index-status` после импорта
3. **Качество**: Проверяйте извлечённые сущности через SQL
4. **Обновления**: Используйте версионирование для отслеживания изменений

## Troubleshooting

### Ошибка "AGE extension not found"

```bash
# Проверить расширение
docker compose exec -T postgres psql -U voproshalych -d voproshalych -c \
  "SELECT * FROM pg_extension WHERE extname = 'age';"
```

### Пустой граф

```bash
# Проверить логи на ошибки LLM
docker compose logs qa-service | grep -i "llm\|error"
```

### Импорт занимает слишком долго

```bash
# Ограничить количество чанков
curl -X POST http://localhost:8004/kb/import-to-lightrag \
  -H "Content-Type: application/json" \
  -d '{"limit": 50}'
```
