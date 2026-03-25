"""Основное приложение FastAPI для QA-сервиса.

Содержит endpoints для вопросов-ответов и проверки здоровья сервиса.
"""

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI

from .api import qa_router, health_router
from .kb.embedding import get_embedding_model
from .llm import get_llm_pool

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)

_lightrag = None


def get_lightrag():
    """Получить экземпляр LightRAG.

    Returns:
        Экземпляр LightRAG или None если не инициализирован
    """
    global _lightrag
    return _lightrag


async def init_lightrag():
    """Инициализировать LightRAG."""
    global _lightrag

    try:
        from lightrag import LightRAG
        from lightrag.utils import EmbeddingFunc
        from .lightrag_adapter import (
            llm_model_func,
            _embedding_func,
            create_lightrag_config,
        )

        config = create_lightrag_config()

        logger.info(f"Initializing LightRAG with config: {config}")

        embedding_dimension = config.get("embedding_dimension", 1024)

        _lightrag = LightRAG(
            working_dir=config["working_dir"],
            llm_model_func=llm_model_func,
            embedding_func=EmbeddingFunc(
                embedding_dim=embedding_dimension,
                max_token_size=512,
                func=_embedding_func,
            ),
            graph_storage="NetworkXStorage",
            vector_storage="PGVectorStorage"
            if config["storage_type"] == "PostgreSQL"
            else None,
        )

        if config["storage_type"] == "PostgreSQL":
            await _lightrag.initialize_storages()

        logger.info("LightRAG initialized successfully")

    except Exception as e:
        logger.error(f"Failed to initialize LightRAG: {e}")
        _lightrag = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управление жизненным циклом приложения.

    При старте инициализирует LLM Pool, embedding модель и LightRAG.
    При завершении логирует остановку сервиса.

    Args:
        app: Приложение FastAPI
    """
    logger.info("Starting QA service...")

    logger.info("Preloading embedding model...")
    get_embedding_model()
    logger.info("Embedding model preloaded")

    llm_pool = get_llm_pool()
    available = llm_pool.get_available_providers()
    logger.info(f"Available LLM providers: {available}")

    use_lightrag = os.getenv("USE_LIGHT_RAG", "false").lower() == "true"
    if use_lightrag:
        await init_lightrag()
    else:
        logger.info("LightRAG disabled (set USE_LIGHT_RAG=true to enable)")

    yield

    logger.info("Shutting down QA service...")


def create_app() -> FastAPI:
    """Создать и настроить приложение FastAPI.

    Returns:
        Настроенное приложение FastAPI
    """
    app = FastAPI(
        title="QA Service",
        description="QA Service with LLM Pool and LightRAG",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.include_router(health_router)
    app.include_router(qa_router)

    return app


app = create_app()
