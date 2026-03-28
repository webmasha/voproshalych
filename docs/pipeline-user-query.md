# Пользовательский пайплайн: Вопрос пользователя → Ответ бота

## Общее описание

Данный документ описывает полный путь запроса пользователя от отправки сообщения в мессенджере до получения ответа от LLM с использованием базы знаний ТюмГУ.

---

### Mermaid диаграмма: полный сценарий вопроса

```mermaid
sequenceDiagram
    autonumber
    par Платформа (Telegram/VK/MAX)
        participant User as Пользователь
        participant Platform as Платформа<br/>(Telegram/VK/MAX API)
        participant Adapter as Platform Adapter<br/>(bots/*/bot.py)
        participant CoreClient as CoreClient<br/>(httpx)
    end

    par Bot-Core
        participant Core as bot-core<br/>(FastAPI)
        participant BotService as BotService<br/>(core/services/<br/>bot_service.py)
        participant UserService as UserService<br/>(core/services/<br/>user_service.py)
        participant QAClient as QAServiceClient<br/>(core/services/<br/>qa_service_client.py)
    end

    par QA-Service
        participant QA as qa-service<br/>(FastAPI)
        participant Embedding as Embedding<br/>(kb/embedding.py<br/>deepvk/USER-bge-m3)
        participant Search as Search<br/>(kb/search.py<br/>pgvector)
        participant BuildCtx as BuildContext<br/>(kb/search.py)
        participant LLMPool as LLM Pool<br/>(llm/pool.py)
    end

    par База данных
        participant DB_Postgres as PostgreSQL<br/>(+ pgvector)
    end

    par Внешние LLM
        participant Mistral as Mistral AI<br/>(API)
        participant GigaChat as GigaChat<br/>(API)
        participant OpenRouter as OpenRouter<br/>(API)
    end

    par Ответ пользователю
        participant PlatformOut as Platform API
        participant UserResult as Пользователь
    end

    %% ЭТАП 1: Отправка вопроса
    Note over User,Platform: ЭТАП 1: Пользователь отправляет вопрос
    User->>Platform: 1. Текстовый вопрос<br/>("Какие правила приёма в магистратуру?")
    Platform->>Adapter: 2. Событие Message

    %% ЭТАП 2: Normalize в адаптере
    Note over Adapter,CoreClient: ЭТАП 2: Нормализация сообщения
    Adapter->>Adapter: 3. detect_message_type()<br/>(определяет тип: text/voice/sticker...)
    Adapter->>Adapter: 4. _build_payload()<br/>(формирует IncomingMessage)
    Adapter->>CoreClient: 5. POST /messages<br/>(IncomingMessage: platform, user_id, chat_id, text, message_type)

    %% ЭТАП 3: Bot-Core обработка
    Note over Core,BotService: ЭТАП 3: Приём и маршрутизация в Bot-Core
    Core->>Core: 6. POST /messages endpoint<br/>(принимает JSON)
    Core->>BotService: 7. handle_message(IncomingMessage)

    %% ЭТАП 4: UserService - upsert пользователя
    Note over BotService,DB_Postgres: ЭТАП 4: Работа с пользователем
    BotService->>UserService: 8. upsert_user(message)
    UserService->>DB_Postgres: 9. SELECT FROM users<br/>(WHERE platform=? AND platform_user_id=?)
    DB_Postgres-->>UserService: 10. Результат (существующий user или None)
    alt Пользователь не найден
        UserService->>DB_Postgres: 11. INSERT INTO users<br/>(platform, platform_user_id, metadata)
    else Пользователь найден
        UserService->>DB_Postgres: 12. UPDATE users<br/>(username, first_name, last_name)
    end
    DB_Postgres-->>UserService: 13. Commit + user object
    UserService-->>BotService: 14. User object

    %% ЭТАП 5: Маршрутизация по типу сообщения
    Note over BotService,QAClient: ЭТАП 5: Маршрутизация текстового сообщения
    BotService->>BotService: 15. Проверка message_type
    alt message_type == "text"
        BotService->>BotService: 16. _handle_text_message()
        BotService->>BotService: 17. normalize_text = text.strip().lower()
        alt normalize_text == "/start"
            BotService->>BotService: 18. _build_start_response()<br/>(формирует приветствие + кнопки)
        else normalize_text == "/ping"
            BotService->>BotService: 19. reply_text = "pong"
        else Любой другой текст
            BotService->>QAClient: 20. ask(question)
        end
    else message_type == "voice"
        BotService->>BotService: 21. _handle_voice_message()<br/>(заглушка "Скоро будет STT")
    else Другой тип
        BotService->>BotService: 22. _build_unsupported_message_response()
    end

    %% ЭТАП 6: QAServiceClient с retry
    Note over QAClient,QA: ЭТАП 6: Отправка в QA-Service (с retry логикой)
    loop Retry (max 3 попытки, exponential backoff)
        QAClient->>QA: 23. POST /qa<br/>({question: "текст вопроса"})
        alt Успешный ответ (200)
            QA-->>QAClient: 24. {answer: "...", model: "...", sources: [...]}
        else Ошибка (503/500/429/timeout)
            QA--xQAClient: 25. Ошибка HTTP
            QAClient->>QAClient: 26. time.sleep(backoff)<br/>(backoff *= 2, max 8s)
        end
    end

    %% ЭТАП 7: QA-Service обработка вопроса
    Note over QA,Embedding: ЭТАП 7: Приём вопроса в QA-Service
    QA->>QA: 27. ask_question(QARequest)
    QA->>QA: 28. llm_pool.select_model()<br/>(выбирает доступный провайдер)
    QA->>QA: 29. provider_name = "mistral" (по умолчанию)

    %% ЭТАП 8: Генерация эмбеддинга
    Note over Embedding,DB_Postgres: ЭТАП 8: Генерация эмбеддинга
    QA->>Embedding: 30. get_embedding(question)
    Embedding->>Embedding: 31. model.encode(text)<br/>(deepvk/USER-bge-m3, normalize=True)
    Embedding-->>QA: 32. embedding = [0.123, 0.456, ...] (1024 float)

    %% ЭТАП 9: Векторный поиск
    Note over Search,DB_Postgres: ЭТАП 9: Векторный поиск в базе знаний
    QA->>Search: 33. search_chunks(embedding, top_k=3)
    Search->>DB_Postgres: 34. SQL: SELECT ... FROM chunks c<br/>JOIN embeddings e ON c.id = e.chunk_id<br/>WHERE e.embedding_vector IS NOT NULL<br/>ORDER BY e.embedding_vector <=> :embedding<br/>LIMIT 3
    DB_Postgres-->>Search: 35. Top-3 чанка<br/>(id, text, title, source_url, similarity)
    Search-->>QA: 36. chunks = [{id, text, title, source_url, similarity}, ...]

    %% ЭТАП 10: Построение контекста
    Note over BuildCtx,LLMPool: ЭТАП 10: Построение контекста для LLM
    alt chunks найдены
        QA->>BuildCtx: 37. build_context_from_chunks(chunks)
        BuildCtx->>BuildCtx: 38. Формирует контекст:<br/>--- Документ 1 ---<br/>Источник: ...<br/>Название: ...<br/>Содержание: ...
        BuildCtx-->>QA: 39. context = "--- Документ 1 ---\nИсточник: ..."
    else chunks не найдены
        QA->>QA: 40. context = "" (пустой)
    end

    %% ЭТАП 11: Сборка промпта
    Note over QA,LLMPool: ЭТАП 11: Сборка и отправка промпта в LLM
    QA->>QA: 41. Формирование финального промпта
    alt context существует
        QA->>QA: 42. prompt = SYSTEM_PROMPT_WITH_CONTEXT<br/>+ "Контекст из документов ТюмГУ:"<br/>+ context<br/>+ "Вопрос: " + question
    else context пустой
        QA->>QA: 43. prompt = SYSTEM_PROMPT<br/>+ "Вопрос: " + question
    end

    QA->>LLMPool: 44. llm_pool.call(prompt)

    %% ЭТАП 12: LLM Pool fallback
    Note over LLMPool,Mistral: ЭТАП 12: LLM Pool с fallback логикой
    loop По приоритету: mistral → gigachat → openrouter
        LLMPool->>LLMPool: 45. get_available_providers()
        LLMPool->>LLMPool: 46. Проверка доступности провайдеров
        alt Mistral доступен
            LLMPool->>Mistral: 47. POST /v1/chat/completions<br/>(prompt, temperature, max_tokens)
            Mistral-->>LLMPool: 48. {choices: [{message: {content: "..."}}], usage: {...}}
        else Mistral недоступен
            LLMPool->>GigaChat: 49. POST /llm/v1/chat/completions
            GigaChat-->>LLMPool: 50. Response JSON
        end
    end

    LLMPool-->>QA: 51. LLMResponse<br/>(content, model, usage)

    %% ЭТАП 13: Формирование ответа
    Note over QA,QAClient: ЭТАП 13: Формирование QAResponse
    QA->>QA: 52. Формирование QAResponse
    alt chunks найдены
        QA->>QA: 53. sources = [c.source_url for c in chunks]
    else
        QA->>QA: 54. sources = []
    end
    QA-->>QAClient: 55. QAResponse<br/>(answer, model, sources)

    %% ЭТАП 14: Возврат ответа в Bot-Service
    Note over QAClient,BotService: ЭТАП 14: Возврат ответа в Bot-Service
    QAClient-->>BotService: 56. reply_text = answer

    %% ЭТАП 15: Формирование BotResponse
    Note over BotService,PlatformOut: ЭТАП 15: Формирование BotResponse
    BotService->>BotService: 57. _build_feedback_buttons()<br/>(["👍", "👎"])
    BotService->>BotService: 58. BotResponse(actions=[<br/>OutgoingAction(send_text, reply_text, buttons)<br/>])

    %% ЭТАП 16: Отправка ответа на платформу
    Note over PlatformOut,UserResult: ЭТАП 16: Доставка ответа пользователю
    BotService->>Core: 59. BotResponse JSON
    Core-->>Adapter: 60. Response JSON
    Adapter->>Adapter: 61. build_inline_keyboard(buttons)
    Adapter->>PlatformOut: 62. sendMessage(text, reply_markup)
    PlatformOut-->>UserResult: 63. Доставляет сообщение с кнопками

    %% Альтернативные пути
    %% Команда /start
    alt normalize_text == "/start"
        BotService->>BotService: 64. _build_start_buttons(is_subscribed)<br/>(["Начать новый диалог"], ["Подписаться/Отписаться"])
    end

    %% Обработка ошибок QA-Service
    alt Ошибка QAServiceTimeout
        BotService->>BotService: 65. Возвращает: "Поиск ответа занимает дольше обычного..."
    else Ошибка QAServiceUnavailable
        BotService->>BotService: 66. Возвращает: "Сервис временно недоступен..."
    else Ошибка QAServiceError
        BotService->>BotService: 67. Возвращает: "Не удалось сформировать ответ..."
    end
```

---

### Детализация по каждому этапу

#### ЭТАП 1: Отправка вопроса пользователем (Platform Input)

**Участники:** Пользователь → Платформа (Telegram/VK/MAX)

**Описание:**
Пользователь отправляет текстовый вопрос через интерфейс мессенджера. Платформа генерирует событие `Message`.

**Реализация:**
- **Telegram**: `aiogram` Bot → Dispatcher → `handle_message()`
- **VK**: Аналогичный адаптер
- **MAX**: Go-сервис с аналогичной логикой

**Что происходит:**
1. Пользователь пишет вопрос: "Какие правила приёма в магистратуру?"
2. Платформа (Telegram Bot API / VK API / MAX API) получает событие `Message`
3. Адаптер определяет тип сообщения через `detect_message_type()`:
   - `text` — текстовое сообщение
   - `voice` — голосовое сообщение
   - `sticker`, `photo`, `video`, `audio`, `document` — медиа
4. Адаптер преобразует в единый формат через `_build_payload()`:

```python
{
    "platform": "telegram",
    "message_type": "text",
    "user_id": "123456789",
    "chat_id": "123456789",
    "text": "Какие правила приёма в магистратуру?",
    "message_id": "42",
    "timestamp": "2024-01-15T10:30:00Z",
    "metadata": {
        "username": "student",
        "first_name": "Иван",
        "last_name": "Иванов",
        "chat_type": "private"
    }
}
```

**Результат:**
- `IncomingMessage` — нормализованное сообщение

---

#### ЭТАП 2: Normalize и отправка в Bot-Core (Platform Adapter)

**Участники:** Platform Adapter → CoreClient

**Описание:**
Адаптер платформы отправляет нормализованное сообщение в bot-core через HTTP.

**Реализация (`bots/telegram/bot.py`):**
```python
class CoreClient:
    async def process_message(self, message: Message) -> dict[str, Any]:
        payload = self._build_payload(message)
        response = await self._client.post("/messages", json=payload)
        return response.json()
```

**Что происходит:**
1. `CoreClient.process_message()` отправляет POST запрос на `/messages`
2. Показывает "Ищу ответ на ваш вопрос..." (pending message) для текстовых сообщений кроме `/start` и `/ping`
3. Обрабатывает ошибки: HTTP 503, 500, таймауты

**Результат:**
- HTTP запрос к bot-core с нормализованным JSON

---

#### ЭТАП 3: Приём и маршрутизация в Bot-Core (API)

**Участники:** Bot-Core FastAPI → BotService

**Описание:**
Bot-Core принимает сообщение и передаёт в бизнес-логику.

**Реализация (`core/services/bot_service.py`):**
```python
def handle_message(self, message: IncomingMessage) -> BotResponse:
    user = self._user_service.upsert_user(message)
    
    if message.message_type == "text":
        return self._handle_text_message(message, user)
    if message.message_type == "voice":
        return self._handle_voice_message(message)
    return self._build_unsupported_message_response(message)
```

**Что происходит:**
1. Принимает POST на `/messages` с нормализованным JSON
2. Создаёт/обновляет пользователя через `UserService.upsert_user()`
3. Маршрутизирует по типу сообщения:
   - `text` → `_handle_text_message()`
   - `voice` → `_handle_voice_message()`
   - другие → `_build_unsupported_message_response()`

**UserService.upsert_user():**
```python
def upsert_user(self, message: IncomingMessage) -> User | None:
    # SELECT * FROM users WHERE platform = ? AND platform_user_id = ?
    user = session.query(User).filter(...).one_or_none()
    
    if user is None:
        # INSERT INTO users (...)
        user = User(platform=..., platform_user_id=...)
    else:
        # UPDATE users SET ...
        user.username = metadata.get("username")
    
    session.commit()
```

**Результат:**
- Пользователь сохранён/обновлён в БД
- Маршрутизация на обработчик

---

#### ЭТАП 4: Обработка текстового сообщения

**Участники:** BotService → QAServiceClient

**Описание:**
Обработка текстового сообщения, включая команды и вопросы к QA-сервису.

**Реализация (`_handle_text_message`):**
```python
def _handle_text_message(self, message: IncomingMessage, user) -> BotResponse:
    normalized_text = (message.text or "").strip()
    lowered_text = normalized_text.lower()

    if lowered_text == "/start":
        return self._build_start_response(message, user)
    if lowered_text == "/ping":
        reply_text = "pong"
    else:
        reply_text = self._ask_qa_service(normalized_text)

    return BotResponse(actions=[
        OutgoingAction(type=ActionType.send_text, text=reply_text,
                       buttons=self._build_feedback_buttons())
    ])
```

**Обрабатываемые команды:**
- `/start` — приветствие с inline кнопками "Начать новый диалог" и "Подписаться/Отписаться"
- `/ping` — возвращает "pong"
- любой другой текст → отправка в QA-сервис

**Голосовые сообщения (`_handle_voice_message`):**
```python
return BotResponse(actions=[
    OutgoingAction(
        type=ActionType.send_text,
        text="Я получил голосовое сообщение. Скоро здесь будет распознавание речи."
    )
])
```

**Результат:**
- Текст ответа для отправки пользователю
- Кнопки feedback (like/dislike) — **реализованы, но обработчики не подключены**

---

#### ЭТАП 5: Отправка в QA-Service (QAServiceClient)

**Участники:** QAServiceClient (Retry Logic)

**Описание:**
Клиент отправляет вопрос в QA-сервис с логикой повторных попыток.

**Реализация (`services/qa_service_client.py`):**
```python
class QAServiceClient:
    MAX_RETRIES = 3
    INITIAL_BACKOFF = 1.0
    MAX_BACKOFF = 8.0

    def ask(self, question: str, context: str | None = None) -> str:
        for attempt in range(self._max_retries):
            try:
                response = self._client.post("/qa", json={
                    "question": question,
                    "context": context,
                })
                
                # Retry на 503, 500, timeout, 429
                # ОбрабатываетConnectError
                
                response.raise_for_status()
                return response.json()["answer"]
            except Exception as e:
                # Логирование + backoff
                time.sleep(backoff)
                backoff = min(backoff * 2, MAX_BACKOFF)
        
        raise last_error
```

**Логика retry:**
- **503 (Unavailable)**: Exponential backoff, до 3 попыток
- **500 (Internal Error)**: Exponential backoff
- **429 (Rate Limited)**: Увеличенный backoff (x2)
- **Timeout**: Exponential backoff
- **Connect Error**: Exponential backoff

**Результат:**
- Ответ от QA-сервиса или исключение (`QAServiceTimeout`, `QAServiceUnavailable`, `QAServiceError`)

---

#### ЭТАП 6: Обработка вопроса в QA-Service (QA API)

**Участники:** QA FastAPI → Embedding → Search → LLM Pool

**Описание:**
QA-service получает вопрос, выполняет векторный поиск и генерирует ответ через LLM.

**Реализация (`api/routes/qa.py`):**
```python
@router.post("", response_model=QAResponse)
async def ask_question(request: QARequest) -> QAResponse:
    llm_pool = get_llm_pool()
    
    provider_name = llm_pool.select_model()
    if not provider_name:
        raise HTTPException(status_code=503, detail="No available LLM providers")

    try:
        context = ""
        sources: list[str] = []

        # Векторный поиск
        query_embedding = get_embedding(request.question)
        chunks = await search_chunks(
            query=request.question,
            embedding=query_embedding,
            top_k=3,  # Топ-3 чанка (не 5 как в документации!)
        )
        
        if chunks:
            context = build_context_from_chunks(chunks)
            sources = [c["source_url"] for c in chunks if c.get("source_url")]

        # Сборка промпта
        if context:
            prompt = f"{SYSTEM_PROMPT_WITH_CONTEXT}\n\nКонтекст из документов ТюмГУ:\n{context}\n\nВопрос: {request.question}"
        else:
            prompt = f"{SYSTEM_PROMPT}\n\nВопрос: {request.question}"

        # Вызов LLM
        response = await llm_pool.call(prompt=prompt)

        return QAResponse(
            answer=response.content,
            model=response.model,
            sources=sources,
        )
```

**Результат:**
- `QAResponse` с answer, model, sources

---

#### ЭТАП 7: Генерация эмбеддинга

**Участники:** Embedding Model (sentence-transformers)

**Описание:**
Текст вопроса преобразуется в 1024-мерный вектор для семантического поиска.

**Реализация (`kb/embedding.py`):**
```python
_model: Optional[SentenceTransformer] = None

def get_embedding_model() -> SentenceTransformer:
    global _model
    if _model is None:
        config = get_kb_config()
        _model = SentenceTransformer(config.embedding_model)  # deepvk/USER-bge-m3
    return _model

def get_embedding(text: str) -> list[float]:
    model = get_embedding_model()
    embedding = model.encode(text, normalize_embeddings=True)
    return embedding.tolist()  # 1024-мерный вектор
```

**Модель:** `deepvk/USER-bge-m3` (1024 dimensions)

**Результат:**
- Нормализованный вектор (list[float] длиной 1024)

---

#### ЭТАП 8: Векторный поиск в базе знаний

**Участники:** QA → PostgreSQL (pgvector)

**Описание:**
Выполняется семантический поиск по чанкам с использованием косинусного сходства pgvector.

**Реализация (`kb/search.py`):**
```python
async def search_chunks(
    query: str,
    embedding: list[float],
    top_k: int = 5,
) -> list[dict]:
    engine = get_engine()
    embedding_str = "[" + ",".join(map(str, embedding)) + "]"

    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT 
                c.id, 
                c.text, 
                c.title, 
                c.source_url,
                (e.embedding_vector <=> cast(:embedding as vector)) as similarity
            FROM chunks c
            JOIN embeddings e ON c.id = e.chunk_id
            WHERE e.embedding_vector IS NOT NULL
            ORDER BY e.embedding_vector <=> cast(:embedding as vector)
            LIMIT :top_k
        """), {"embedding": embedding_str, "top_k": top_k})

        chunks = []
        for row in result:
            chunks.append({
                "id": str(row.id),
                "text": row.text,
                "title": row.title,
                "source_url": row.source_url,
                "similarity": float(row.similarity),
            })

    return chunks
```

**SQL запрос:**
```sql
SELECT c.id, c.text, c.title, c.source_url,
       (e.embedding_vector <=> cast(:embedding as vector)) as similarity
FROM chunks c
JOIN embeddings e ON c.id = e.chunk_id
WHERE e.embedding_vector IS NOT NULL
ORDER BY e.embedding_vector <=> cast(:embedding as vector)
LIMIT 3;
```

**Оператор `<=>`**: Косинусное сходство pgvector

**Важно:** В коде используется `top_k=3`, а не 5 как в документации!

**Результат:**
- Список из 3 чанков с текстом, названием, source_url и similarity

---

#### ЭТАП 9: Построение контекста для LLM

**Участники:** QA (build_context_from_chunks)

**Описание:**
Из найденных чанков формируется контекст для промпта LLM.

**Реализация (`kb/search.py`):**
```python
def build_context_from_chunks(chunks: list[dict]) -> str:
    if not chunks:
        return ""

    context_parts = []
    for i, chunk in enumerate(chunks, 1):
        source = chunk.get("source_url", "Unknown")
        title = chunk.get("title", "Untitled")
        text = chunk["text"]

        context_parts.append(
            f"--- Документ {i} ---\n"
            f"Источник: {source}\n"
            f"Название: {title}\n"
            f"Содержание: {text}\n"
        )

    return "\n\n".join(context_parts)
```

**Результат:**
- Текст контекста для LLM, например:
```
--- Документ 1 ---
Источник: https://abiturient.utmn.ru/magistr
Название: Правила приёма в магистратуру
Содержание: При приёме в магистратуру...
```

---

#### ЭТАП 10: Генерация ответа LLM Pool

**Участники:** LLM Pool → Mistral / GigaChat / OpenRouter

**Описание:**
Собранный промпт отправляется в LLM Pool с fallback логикой между провайдерами.

**Реализация (`llm/pool.py`):**
```python
class LLMPool:
    def __init__(self, config: LLMConfig | None = None):
        self._providers = {
            "mistral": MistralProvider(...),
            "openrouter": OpenRouterProvider(...),
            "gigaсhat": GigaChatProvider(...),
        }

    async def call(self, prompt: str, ...) -> LLMResponse:
        available = self.get_available_providers()
        providers_to_try = [p for p in self._config.model_priority if p in available]

        for prov_name in providers_to_try:
            provider = self._providers.get(prov_name)
            try:
                response = await provider.generate(prompt=prompt, ...)
                return response
            except Exception as e:
                continue  # Пробуем следующий провайдер

        raise ValueError("All providers failed")
```

**Промпт (config/prompts.py):**
```python
SYSTEM_PROMPT = """Ты — Виртуальный ассистент Тюменского государственного университета (ТюмГУ). 
Твоя задача — помогать студентам и абитуриентам с вопросами об университете.
Отвечай кратко и по существу. Если не знаешь ответ — честно скажи об этом.
Не называй себя ChatGPT, Claude или другой моделью. Ты — помощник ТюмГУ."""

SYSTEM_PROMPT_WITH_CONTEXT = """Ты — Виртуальный ассистент Тюменского государственного университета (ТюмГУ). 
Твоя задача — помогать студентам и абитуриентам с вопросами об университете.
Отвечай кратко и по существу. Если не знаешь ответ — честно скажи об этом.
Не называй себя ChatGPT, Claude или другой моделью. Ты — помощник ТюмГУ.

При ответе на вопрос ИСПОЛЬЗУЙ ТОЛЬКО информацию из предоставленного контекста.
Не добавляй информацию, которой нет в контексте.
Если в контексте недостаточно информации — скажи об этом."""
```

**Fallback порядок:** Mistral → GigaChat → OpenRouter (по умолчанию)

**Результат:**
- `LLMResponse` с content, model, usage

---

#### ЭТАП 11: Формирование ответа пользователю

**Участники:** BotService → Platform Adapter → Пользователь

**Описание:**
Формируется итоговый ответ и отправляется через платформу.

**Реализация:**
```python
# В qa_service_client.ask()
return payload["answer"]  # Просто текст ответа

# В bot_service._handle_text_message()
reply_text = self._ask_qa_service(normalized_text)

return BotResponse(actions=[
    OutgoingAction(
        type=ActionType.send_text,
        text=reply_text,
        buttons=self._build_feedback_buttons(),
    )
])
```

**Platform adapter:**
```python
# bots/telegram/bot.py
for action in bot_response.get("actions", []):
    if action.get("type") == "send_text" and action.get("text"):
        await message.answer(
            action["text"],
            reply_markup=build_inline_keyboard(action.get("buttons", [])),
        )
```

**Кнопки feedback:**
```python
def _build_feedback_buttons(self) -> list[list[InlineButton]]:
    return [
        [
            InlineButton(text="👍", callback_data="feedback:like"),
            InlineButton(text="👎", callback_data="feedback:dislike"),
        ]
    ]
```

**Важно:** Кнопки создаются, но обработчики `feedback:like` и `feedback:dislike` **не реализованы** в `handle_callback()`.

**Результат:**
- Пользователь получает ответ с кнопками 👍/👎

---

## Что реализовано vs Что в документации

| Компонент | В коде | В документации |
|-----------|--------|----------------|
| `/qa/categorize` endpoint | ❌ Нет | ✅ Есть |
| Категоризация вопроса (greeting/kb_query/clarification) | ❌ Нет | ✅ Есть |
| Session/History management | ❌ Нет | ✅ Есть |
| Логирование вопросов-ответов в БД | ❌ Нет | ✅ Есть |
| Feedback обработка (like/dislike) | ⚠️ Кнопки есть, обработка нет | ✅ Есть |
| top_k для поиска | 3 | 5 |
| STT для голосовых | ⚠️ Заглушка | ✅ Описано |

---

## Таблицы базы данных

| Таблица | Назначение |
|---------|------------|
| `users` | Пользователи платформ (platform, platform_user_id, username, first_name, last_name, is_subscribed) |
| `subscriptions` | История подписок (user_id, subscribed_at, unsubscribed_at) |
| `chunks` | Текстовые чанки из документов (text, title, source_url) |
| `embeddings` | Векторные представления чанков (chunk_id, embedding_vector) |
| `holidays` | Праздники для рассылки |

---

## API Endpoints

### Bot-Core

| Метод | Путь | Назначение |
|-------|------|------------|
| POST | /messages | Приём нормализованных сообщений |
| POST | /callbacks | Приём callback событий |
| GET | /health | Проверка здоровья |

### QA-Service

| Метод | Путь | Назначение |
|-------|------|------------|
| POST | /qa | Основной endpoint для вопросов |
| GET | /health | Проверка здоровья |
| GET | /kb/chunks | Просмотр чанков (для админки) |

---

## Технологический стек

| Компонент | Технология |
|-----------|------------|
| Backend | Python 3.12, FastAPI |
| Bot Framework | aiogram 3.x |
| Database | PostgreSQL + pgvector |
| Embeddings | deepvk/USER-bge-m3 (1024 dimensions) |
| LLM Pool | Mistral, GigaChat, OpenRouter |
| Containerization | Docker, Docker Compose |

---

## Жизненный цикл запроса (Timeline)

```
Время    | Компонент       | Действие
---------|-----------------|----------------------------------
0ms      | Пользователь    | Отправляет вопрос в Telegram
10ms     | Telegram Adapter| normalize_message() → IncomingMessage
20ms     | CoreClient      | POST /messages → bot-core
30ms     | BotCore API     | Принимает POST /messages
40ms     | BotService      | handle_message()
50ms     | UserService     | upsert_user() → users table
60ms     | BotService      | _handle_text_message()
70ms     | QAServiceClient | POST /qa → qa-service (с retry)
80ms     | QA API          | ask_question()
90ms     | Embedding       | get_embedding() → 1024-vector
100ms    | Search          | search_chunks() → Top-3 чанка
110ms    | BuildContext    | build_context_from_chunks()
120ms    | LLM Pool        | select_model() → Mistral
130ms    | Mistral API     | POST /chat/completions
150ms    | Mistral API     | response JSON
160ms    | QA Service      | Формирует QAResponse
170ms    | QAServiceClient | Возвращает answer
180ms    | BotService      | Формирует BotResponse
190ms    | Telegram Adapter| sendMessage с кнопками
200ms    | Пользователь    | Получает ответ
```

---

## Особенности реализации

### Обработка ошибок QA-Service

```python
def _ask_qa_service(self, question: str) -> str:
    try:
        return self._qa_service_client.ask(question=question)
    except QAServiceTimeout:
        return "Поиск ответа занимает дольше обычного. Попробуйте переформулировать вопрос."
    except QAServiceUnavailable:
        return "Сервис временно недоступен. Мы уже работаем над устранением проблемы."
    except QAServiceError:
        return "Не удалось сформировать ответ. Попробуйте переформулировать вопрос."
    except Exception:
        return "Что-то пошло не так. Попробуйте повторить запрос позже."
```

### Retry логика

- Максимум 3 попытки
- Exponential backoff: 1s → 2s → 4s → 8s (max)
- Rate limited (429): удвоенный backoff

### Инициализация при старте

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Preload embedding model
    get_embedding_model()
    
    # Инициализация LLM Pool
    llm_pool = get_llm_pool()
    available = llm_pool.get_available_providers()
    
    # Опционально LightRAG
    if os.getenv("USE_LIGHT_RAG") == "true":
        await init_lightrag()
    
    yield
    # Shutdown
```

---

## Технологический стек

| Компонент | Технология |
|-----------|------------|
| Backend | Python 3.12, FastAPI |
| Bot Framework | aiogram 3.x |
| Database | PostgreSQL + pgvector |
| Embeddings | deepvk/USER-bge-m3 (1024 dimensions) |
| LLM Pool | Mistral, GigaChat, OpenRouter |
| Containerization | Docker, Docker Compose |
