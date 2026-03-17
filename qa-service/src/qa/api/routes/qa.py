"""API роут для QA."""

import logging

from fastapi import APIRouter, HTTPException

from ...models.request import QARequest, QAResponse
from ...llm import get_llm_pool

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/qa", tags=["qa"])


@router.post("", response_model=QAResponse)
async def ask_question(request: QARequest) -> QAResponse:
    """Задать вопрос QA сервису.

    Args:
        request: QARequest с вопросом

    Returns:
        QAResponse с ответом от LLM

    Raises:
        HTTPException: При ошибке генерации
    """
    llm_pool = get_llm_pool()

    provider_name = llm_pool.select_model()
    if not provider_name:
        raise HTTPException(status_code=503, detail="No available LLM providers")

    try:
        prompt = request.question
        if request.context:
            prompt = f"Контекст: {request.context}\n\nВопрос: {request.question}"

        response = await llm_pool.call(prompt=prompt)

        return QAResponse(
            answer=response.content,
            model=response.model,
            sources=[],
        )
    except Exception as e:
        logger.error(f"Error generating answer: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to generate answer: {str(e)}"
        )
