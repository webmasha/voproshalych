"""API роут для QA."""

import logging

from fastapi import APIRouter, HTTPException

from ...config.prompts import SYSTEM_PROMPT, SYSTEM_PROMPT_WITH_CONTEXT
from ...models.request import QARequest, QAResponse
from ...llm import get_llm_pool
from ...kb.embedding import get_embedding
from ...kb.search import search_chunks, build_context_from_chunks

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
        context = ""
        sources: list[str] = []

        try:
            query_embedding = get_embedding(request.question)
            chunks = await search_chunks(
                query=request.question,
                embedding=query_embedding,
                top_k=3,
            )
            if chunks:
                context = build_context_from_chunks(chunks)
                sources = [c["source_url"] for c in chunks if c.get("source_url")]
                logger.info(f"Found {len(chunks)} relevant chunks")
        except Exception as e:
            logger.warning(f"KB search failed: {e}")

        if context:
            prompt = f"{SYSTEM_PROMPT_WITH_CONTEXT}\n\nКонтекст из документов ТюмГУ:\n{context}\n\nВопрос: {request.question}"
        else:
            prompt = f"{SYSTEM_PROMPT}\n\nВопрос: {request.question}"

        response = await llm_pool.call(prompt=prompt)

        return QAResponse(
            answer=response.content,
            model=response.model,
            sources=sources,
        )
    except Exception as e:
        logger.error(f"Error generating answer: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to generate answer: {str(e)}"
        )
