"""API роут для health check."""

from fastapi import APIRouter

from ...models.request import HealthResponse
from ...llm import get_llm_pool

router = APIRouter(prefix="", tags=["health"])

__version__ = "0.1.0"


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Проверить здоровье сервиса.

    Returns:
        HealthResponse с статусом
    """
    llm_pool = get_llm_pool()
    available_providers = llm_pool.get_available_providers()

    return HealthResponse(
        status="ok" if available_providers else "degraded",
        version=__version__,
    )


@router.get("/health/ready", response_model=HealthResponse)
async def readiness_check() -> HealthResponse:
    """Проверить готовность сервиса.

    Returns:
        HealthResponse с статусом
    """
    llm_pool = get_llm_pool()
    available_providers = llm_pool.get_available_providers()

    if not available_providers:
        return HealthResponse(
            status="no_providers",
            version=__version__,
        )

    return HealthResponse(
        status="ok",
        version=__version__,
    )
