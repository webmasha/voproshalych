"""Основное приложение FastAPI."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from .api import qa_router, health_router
from .llm import get_llm_pool

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управление жизненным циклом."""
    logger.info("Starting QA service...")

    llm_pool = get_llm_pool()
    available = llm_pool.get_available_providers()
    logger.info(f"Available LLM providers: {available}")

    yield

    logger.info("Shutting down QA service...")


def create_app() -> FastAPI:
    """Создать приложение FastAPI."""
    app = FastAPI(
        title="QA Service",
        description="QA Service with LLM Pool",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.include_router(health_router)
    app.include_router(qa_router)

    return app


app = create_app()
