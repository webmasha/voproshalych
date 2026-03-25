"""Векторный поиск в Базе Знаний.

Осуществляет семантический поиск по чанкам с использованием pgvector
для косинусного сходства на уровне PostgreSQL.
"""

import logging
from typing import Optional

from sqlalchemy import create_engine, text

logger = logging.getLogger(__name__)

_engine = None


def get_engine():
    """Получить движок подключения к БД.

    Returns:
        SQLAlchemy Engine
    """
    global _engine
    if _engine is None:
        db_url = "postgresql://voproshalych:voproshalych@postgres:5432/voproshalych"
        _engine = create_engine(db_url)
    return _engine


async def search_chunks(
    query: str,
    embedding: list[float],
    top_k: int = 5,
) -> list[dict]:
    """Найти похожие чанки по эмбеддингу через pgvector.

    Использует оператор <=> (косинусное сходство) на уровне PostgreSQL
    для эффективного поиска без загрузки всех данных в память.

    Args:
        query: Текст запроса пользователя
        embedding: Вектор эмбеддинга запроса
        top_k: Количество возвращаемых результатов

    Returns:
        Список чанков с текстом, источником и оценкой похожести
    """
    engine = get_engine()

    embedding_str = "[" + ",".join(map(str, embedding)) + "]"

    try:
        with engine.connect() as conn:
            result = conn.execute(
                text("""
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
                """),
                {"embedding": embedding_str, "top_k": top_k},
            )

            chunks = []
            for row in result:
                chunks.append(
                    {
                        "id": str(row.id),
                        "text": row.text,
                        "title": row.title,
                        "source_url": row.source_url,
                        "similarity": float(row.similarity) if row.similarity else 0.0,
                    }
                )

    except Exception as e:
        logger.error(f"Vector search failed: {e}")
        raise

    logger.info(f"Found {len(chunks)} chunks for query: {query[:50]}...")
    return chunks


def build_context_from_chunks(chunks: list[dict]) -> str:
    """Построить контекст из чанков для LLM.

    Формирует текстовый контекст в формате:
    --- Документ N ---
    Источник: ...
    Название: ...
    Содержание: ...

    Args:
        chunks: Список чанков с текстом и метаданными

    Returns:
        Текст контекста для использования в промпте LLM
    """
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
