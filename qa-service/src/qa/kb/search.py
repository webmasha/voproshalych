"""Векторный поиск в Базе Знаний."""

import json
import logging
import math
from typing import Optional

from sqlalchemy import create_engine, text

logger = logging.getLogger(__name__)

_engine = None


def get_engine():
    """Получить движок БД."""
    global _engine
    if _engine is None:
        db_url = "postgresql://voproshalych:voproshalych@postgres:5432/voproshalych"
        _engine = create_engine(db_url)
    return _engine


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Вычислить косинусное сходство."""
    dot_product = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot_product / (norm_a * norm_b)


async def search_chunks(
    query: str,
    embedding: list[float],
    top_k: int = 5,
) -> list[dict]:
    """Найти похожие чанки по эмбеддингу.

    Args:
        query: Текст запроса
        embedding: Эмбеддинг запроса
        top_k: Количество результатов

    Returns:
        Список чанков с текстом и источником
    """
    engine = get_engine()

    try:
        with engine.connect() as conn:
            result = conn.execute(
                text("""
                    SELECT c.id, c.text, c.title, c.source_url, e.embedding
                    FROM chunks c
                    JOIN embeddings e ON c.id = e.chunk_id
                """),
            )

            chunks_with_scores = []
            for row in result:
                try:
                    chunk_emb = json.loads(row.embedding)
                    similarity = cosine_similarity(embedding, chunk_emb)
                    chunks_with_scores.append(
                        {
                            "id": str(row.id),
                            "text": row.text,
                            "title": row.title,
                            "source_url": row.source_url,
                            "similarity": similarity,
                        }
                    )
                except Exception as e:
                    logger.warning(f"Failed to parse embedding: {e}")
                    continue

            chunks_with_scores.sort(key=lambda x: x["similarity"], reverse=True)
            chunks = chunks_with_scores[:top_k]
    except Exception as e:
        logger.error(f"DB query failed: {e}")
        raise

    logger.info(f"Found {len(chunks)} chunks for query: {query[:50]}...")
    return chunks


def build_context_from_chunks(chunks: list[dict]) -> str:
    """Построить контекст из чанков.

    Args:
        chunks: Список чанков

    Returns:
        Текст контекста для LLM
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
