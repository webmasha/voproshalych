# Заполнение Базы Знаний

**Статус:** База знаний заполнена. В базе ~315 чанков из Confluence, Sveden и UTMN.

## Текущее состояние

```bash
docker compose exec -T postgres psql -U voproshalych -d voproshalych -c \
  "SELECT source_type, COUNT(*) FROM chunks GROUP BY source_type;"
```

Ожидаемый вывод:
| source_type | count |
|-------------|-------|
| confluence | 7 |
| sveden | ~87 |
| utmn | ~90-150 |

## Быстрый старт

### 1. Подключение к корпоративной сети

Для парсинга Confluence и utmn.ru необходимо подключение к корпоративной сети ТюмГУ (VPN или локальная сеть университета).

### 2. Пересборка сервиса (при необходимости)

```bash
cd Submodules/voproshalych_v2
docker compose up -d --build qa-service
```

### 3. Запуск скрипта наполнения БЗ

```bash
cd Submodules/voproshalych_v2
docker compose exec -T qa-service uv run python scripts/fill_kb_from_sources.py --clear
```

**Аргументы:**
- `--clear` (по умолчанию) — очищает таблицы перед заполнением
- `--resume` — продолжить с последнего места (без очистки)

### 4. Запуск в фоне

```bash
docker compose exec -T qa-service sh -c "uv run python scripts/fill_kb_from_sources.py > /tmp/kb_fill.log 2>&1 &"
```

### 5. Продолжение после остановки (--resume)

```bash
docker compose exec -T qa-service uv run python scripts/fill_kb_from_sources.py --resume
```

### 6. Мониторинг

```bash
# Проверить лог (только если запущен в фоне)
docker compose exec -T qa-service tail -20 /tmp/kb_fill.log

# Проверить наполнение БД
docker compose exec -T postgres psql -U voproshalych -d voproshalych -c "SELECT source_type, COUNT(*) FROM chunks GROUP BY source_type;"

# Проверить текст в чанках
docker compose exec -T postgres psql -U voproshalych -d voproshalych -c "SELECT title, LEFT(text, 200) FROM chunks LIMIT 5;"
```

## Что делает скрипт

**Инкрементальное сохранение: документ за документом.**

1. **Обрабатывает источники:**
   - **Confluence** — 7 политик и положений ИБ (2 страницы)
   - **Sveden** — ~87 PDF документов
   - **UTMN** — PDF с 22 страниц

2. **Для каждого документа:**
   ```
   Парсинг PDF (Tesseract OCR)
         ↓
   Создание чанков
         ↓
   Эмбеддинги (батчами по 5 текстов)
         ↓
   Сохранение в БД ✅
   ```

## Остановка скрипта

```bash
# Перезапустить контейнер
docker compose restart qa-service

# Или убить процесс
docker compose exec -T qa-service pkill -f fill_kb_from_sources
```

## Очистка БД вручную

```bash
docker compose exec -T postgres psql -U voproshalych -d voproshalych -c "TRUNCATE chunks, embeddings RESTART IDENTITY CASCADE;"
```

## Как работает PDF парсинг

### Tesseract OCR

- **Языки:** `rus+eng`
- **Параметры:** `--oem 3 --psm 1`
- **Разрешение:** 300 DPI

### Почему Tesseract

| Сравнение | EasyOCR | Tesseract |
|-----------|---------|-----------|
| Русский язык | Плохое качество | ✅ Хорошее |
| RAM | ~1 GB | ✅ ~100 MB |

## Конфигурация

### Chunk размеры

В `src/qa/kb/config.py`:
- `chunk_size`: 1000 символов
- `chunk_overlap`: 200 символов
- `min_chunk_size`: 0

### Источники

Настраиваются в `scripts/fill_kb_from_sources.py`, класс `Config`:
- `confluence_pages` — список страниц Confluence
- `sveden_url` — страница Сведения
- `utmn_pages` — список страниц UTMN

### Фильтр Confluence

`ALLOWED_PDF_TITLES` в `src/qa/kb/parsers/confluence.py` — фильтр разрешённых PDF.
