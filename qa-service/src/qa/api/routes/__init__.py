"""API роутеры."""

from .qa import router as qa_router
from .health import router as health_router

__all__ = ["qa_router", "health_router"]
