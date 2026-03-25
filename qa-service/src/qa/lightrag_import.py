"""Функции для интеграции существующей Базы Знаний с LightRAG."""

import logging
from typing import Optional

from sqlalchemy import create_engine, text

logger = logging.getLogger(__name__)

_engine = None


def _get_engine():
    global _engine
    if _engine is None:
        db_url = "postgresql://voproshalych:voproshalych@postgres:5432/voproshalych"
        _engine = create_engine(db_url)
    return _engine


def get_existing_chunks(limit: Optional[int] = None) -> list[dict]:
    """Получить все существующие чанки из БД.

    Args:
        limit: Лимит количества чанков (None = все)

    Returns:
        Список чанков с текстом и метаданными
    """
    engine = _get_engine()

    query = """
        SELECT c.id, c.text, c.title, c.source_url, c.source_type
        FROM chunks c
        ORDER BY c.created_at
    """

    if limit:
        query += f" LIMIT {limit}"

    with engine.connect() as conn:
        result = conn.execute(text(query))

        chunks = []
        for row in result:
            chunks.append(
                {
                    "id": str(row.id),
                    "text": row.text,
                    "title": row.title or "Untitled",
                    "source_url": row.source_url,
                    "source_type": row.source_type,
                }
            )

    logger.info(f"Retrieved {len(chunks)} chunks from database")
    return chunks


async def import_chunks_to_lightrag(
    chunk_ids: Optional[list[str]] = None,
    limit: Optional[int] = None,
) -> dict:
    """Импортировать существующие чанки в LightRAG.

    Извлекает чанки из текущей БД и добавляет их в индекс LightRAG.
    При добавлении LightRAG автоматически создаёт эмбеддинги и извлекает
    сущности для knowledge graph.

    Args:
        chunk_ids: Список ID чанков для импорта (None = все)
        limit: Лимит количества чанков

    Returns:
        Статистика импорта
    """
    from .lightrag_adapter import create_lightrag_config
    from .main import get_lightrag

    rag = get_lightrag()

    if rag is None:
        raise RuntimeError("LightRAG not initialized. Set USE_LIGHT_RAG=true")

    config = create_lightrag_config()

    logger.info("Starting import of existing chunks to LightRAG...")

    if chunk_ids:
        chunks = []
        engine = _get_engine()
        with engine.connect() as conn:
            result = conn.execute(
                text(
                    """
                SELECT c.id, c.text, c.title, c.source_url, c.source_type
                FROM chunks c
                WHERE c.id::text = ANY(:chunk_ids)
            """
                ),
                {"chunk_ids": chunk_ids},
            )
            for row in result:
                chunks.append(
                    {
                        "id": str(row.id),
                        "text": row.text,
                        "title": row.title or "Untitled",
                        "source_url": row.source_url,
                        "source_type": row.source_type,
                    }
                )
    else:
        chunks = get_existing_chunks(limit=limit)

    if not chunks:
        return {"status": "no_chunks", "imported": 0}

    documents = {}
    for chunk in chunks:
        doc_id = chunk["id"]
        content = f"{chunk['title']}\n\n{chunk['text']}"
        documents[doc_id] = content

    try:
        await rag.ainsert(documents)

        logger.info(f"Successfully imported {len(documents)} chunks to LightRAG")

        return {
            "status": "success",
            "imported": len(documents),
            "message": f"Imported {len(documents)} chunks. "
            f"Knowledge graph will be built automatically.",
        }

    except Exception as e:
        logger.error(f"Failed to import chunks to LightRAG: {e}")
        raise RuntimeError(f"Import failed: {e}")


async def rebuild_knowledge_graph() -> dict:
    """Перестроить knowledge graph из всех документов.

    Использует LLM для извлечения сущностей и связей из всех
    документов в индексе LightRAG.

    Returns:
        Статистика перестроения
    """
    from .main import get_lightrag

    rag = get_lightrag()

    if rag is None:
        raise RuntimeError("LightRAG not initialized. Set USE_LIGHT_RAG=true")

    logger.info("Starting knowledge graph rebuild...")

    try:
        await rag.aextract_entities()

        logger.info("Knowledge graph rebuilt successfully")

        return {
            "status": "success",
            "message": "Knowledge graph rebuilt successfully",
        }

    except Exception as e:
        logger.error(f"Failed to rebuild knowledge graph: {e}")
        raise RuntimeError(f"Rebuild failed: {e}")
