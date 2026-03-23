"""Генерация эмбеддингов с помощью sentence-transformers."""

import logging
from typing import Optional

import numpy as np
from sentence_transformers import SentenceTransformer

from qa.kb.config import get_kb_config

logger = logging.getLogger(__name__)

_model: Optional[SentenceTransformer] = None


def get_embedding_model() -> SentenceTransformer:
    """Получить или создать модель эмбеддингов.

    Returns:
        Модель SentenceTransformer
    """
    global _model
    if _model is None:
        config = get_kb_config()
        logger.info(f"Loading embedding model: {config.embedding_model}")
        _model = SentenceTransformer(config.embedding_model)
        logger.info("Embedding model loaded")
    return _model


def get_embedding(text: str) -> list[float]:
    """Сгенерировать эмбеддинг для текста.

    Args:
        text: Текст для эмбеддинга

    Returns:
        Вектор эмбеддинга как список float
    """
    model = get_embedding_model()
    embedding = model.encode(text, normalize_embeddings=True)
    return embedding.tolist()


def get_embeddings_batch(texts: list[str]) -> list[list[float]]:
    """Сгенерировать эмбеддинги для нескольких текстов.

    Args:
        texts: Список текстов для эмбеддингов

    Returns:
        Список векторов эмбеддингов
    """
    model = get_embedding_model()
    embeddings = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
    return embeddings.tolist()


def get_embedding_dimension() -> int:
    """Получить размерность вектора эмбеддинга.

    Returns:
        Размерность эмбеддинга
    """
    model = get_embedding_model()
    return model.get_sentence_embedding_dimension()
