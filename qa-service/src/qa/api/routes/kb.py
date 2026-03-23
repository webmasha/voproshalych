"""API роуты для работы с Базой Знаний."""

import json
import logging
import uuid
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, HttpUrl
from sqlalchemy import create_engine, text

from qa.kb.chunking import Chunk, TextChunker
from qa.kb.config import get_kb_config
from qa.kb.embedding import get_embedding
from qa.kb.parsers.web import WebPageParser


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/kb", tags=["kb"])

_parser = WebPageParser()
_chunker = TextChunker(
    chunk_size=get_kb_config().chunk_size,
    chunk_overlap=get_kb_config().chunk_overlap,
    min_chunk_size=get_kb_config().min_chunk_size,
)

_engine = None


def get_engine():
    """Получить движок базы данных."""
    global _engine
    if _engine is None:
        db_url = "postgresql://voproshalych:voproshalych@postgres:5432/voproshalych"
        _engine = create_engine(db_url)
    return _engine


class DocumentRequest(BaseModel):
    """Запрос на скачивание документа."""

    url: HttpUrl


class ChunkResponse(BaseModel):
    """Ответ с данными чанка."""

    id: str
    text: str
    source_url: str
    title: str
    chunk_index: int


class DocumentResponse(BaseModel):
    """Ответ со скачанным документом."""

    url: str
    title: str
    chunks_count: int


async def _save_chunk_to_db(chunk: Chunk, embedding: list[float]) -> None:
    """Сохранить чанк и эмбеддинг в базу данных."""
    engine = get_engine()
    chunk_id = uuid.uuid4()

    with engine.connect() as conn:
        conn.execute(
            text("""
                INSERT INTO chunks (id, text, source_url, source_type, title)
                VALUES (:id, :text, :source_url, :source_type, :title)
            """),
            {
                "id": str(chunk_id),
                "text": chunk.text,
                "source_url": chunk.source_url,
                "source_type": "web",
                "title": chunk.title,
            },
        )
        conn.commit()

        conn.execute(
            text("""
                INSERT INTO embeddings (chunk_id, embedding)
                VALUES (:chunk_id, :embedding)
            """),
            {
                "chunk_id": str(chunk_id),
                "embedding": json.dumps(embedding),
            },
        )
        conn.commit()


@router.post("/documents", response_model=DocumentResponse)
async def download_document(request: DocumentRequest) -> DocumentResponse:
    """Скачать и распарсить веб-страницу или PDF, затем чанкировать и создать эмбеддинги.

    Args:
        request: DocumentRequest с URL документа для скачивания

    Returns:
        DocumentResponse с информацией о распарсенном документе
    """
    try:
        parsed = await _parser.parse(str(request.url))
        logger.info(f"Распарсен документ: {parsed.title}")

        chunks_count = 0
        for chunk in _chunker.chunk_text(
            text=parsed.text_content,
            source_url=parsed.url,
            title=parsed.title,
        ):
            embedding = get_embedding(chunk.text)
            await _save_chunk_to_db(chunk, embedding)
            chunks_count += 1
            logger.info(f"Создан чанк {chunks_count}: {chunk.text[:50]}...")

        return DocumentResponse(
            url=parsed.url,
            title=parsed.title,
            chunks_count=chunks_count,
        )

    except Exception as e:
        logger.error(f"Не удалось обработать документ: {e}")
        raise HTTPException(
            status_code=400, detail=f"Не удалось обработать документ: {e}"
        )


@router.get("/health")
async def kb_health():
    """Проверка работоспособности KB сервиса."""
    return {"status": "ok", "embedding_model": get_kb_config().embedding_model}
