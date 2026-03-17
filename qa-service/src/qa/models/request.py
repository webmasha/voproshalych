"""Модели запросов и ответов."""

from pydantic import BaseModel, Field


class QARequest(BaseModel):
    """Запрос к QA сервису.

    Attributes:
        question: Вопрос пользователя
        context: Дополнительный контекст (опционально)
    """

    question: str = Field(..., min_length=1, max_length=10000)
    context: str | None = None


class QAResponse(BaseModel):
    """Ответ от QA сервиса.

    Attributes:
        answer: Ответ от LLM
        model: Использованная модель
        sources: Источники (если есть)
    """

    answer: str
    model: str
    sources: list[str] = Field(default_factory=list)


class HealthResponse(BaseModel):
    """Ответ health check."""

    status: str
    version: str
