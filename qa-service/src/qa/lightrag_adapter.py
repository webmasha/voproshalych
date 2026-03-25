"""Адаптеры для интеграции LightRAG с существующим LLM Pool и embedding моделью."""

import logging
import os
from typing import Any

import numpy as np

from qa.llm import get_llm_pool
from qa.kb.embedding import get_embeddings_batch

logger = logging.getLogger(__name__)


async def llm_model_func(
    prompt: str,
    system_prompt: str | None = None,
    history_messages: list | None = None,
    keyword_extraction: bool = False,
    **kwargs: Any,
) -> str:
    """Кастомная LLM функция для LightRAG.

    Использует существующий LLM Pool (Mistral -> GigaChat -> OpenRouter).
    """
    llm_pool = get_llm_pool()

    full_prompt = prompt
    if system_prompt:
        full_prompt = f"{system_prompt}\n\n{prompt}"

    try:
        response = await llm_pool.call(prompt=full_prompt)
        return response.content
    except Exception as e:
        logger.error(f"LLM call failed in LightRAG: {e}")
        if keyword_extraction:
            return "[]"
        raise


async def _embedding_func(texts: list[str]) -> np.ndarray:
    """Async функция эмбеддингов для LightRAG.

    Args:
        texts: Список текстов для эмбеддингов

    Returns:
        NumPy массив эмбеддингов
    """
    embeddings = get_embeddings_batch(texts)
    return np.array(embeddings)


def create_lightrag_config() -> dict:
    """Создать конфигурацию для LightRAG."""
    return {
        "working_dir": os.getenv("LIGHT_RAG_WORKING_DIR", "/app/lightrag_data"),
        "storage_type": os.getenv("LIGHT_RAG_STORAGE_TYPE", "PostgreSQL"),
        "postgres_uri": os.getenv(
            "LIGHT_RAG_POSTGRES_URI",
            "postgresql://voproshalych:voproshalych@postgres:5432/voproshalych",
        ),
        "embedding_dimension": 1024,
    }
