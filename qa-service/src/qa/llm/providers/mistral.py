"""Mistral AI провайдер."""

import httpx
import logging

from .base import BaseLLMProvider, LLMResponse
from ..config import get_llm_config

logger = logging.getLogger(__name__)

class MistralProvider(BaseLLMProvider):
    """Провайдер Mistral AI.

    Attributes:
        api_key: API ключ Mistral
        model: Модель для использования
    """

    def __init__(self, api_key: str | None = None, model: str | None = None):
        """Инициализировать провайдер.

        Args:
            api_key: API ключ (опционально, берется из конфига)
            model: Модель (опционально, берется из конфига)
        """
        config = get_llm_config()
        self._api_key = api_key or config.mistral_api_key
        self._model = model or config.mistral_model

    @property
    def name(self) -> str:
        """Имя провайдера."""
        return "mistral"

    def is_available(self) -> bool:
        """Проверить доступность провайдера."""
        return bool(self._api_key)
    
    async def check_health(self) -> bool:
        """Проверить доступность API через эндпоинт /models."""
        if not self.is_available():
            return False
            
        headers = {"Authorization": f"Bearer {self._api_key}"}
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    "https://api.mistral.ai/v1/models",
                    headers=headers
                )
                return response.status_code == 200
        except Exception as e:
            logger.warning(f"Mistral health check failed: {e}")
            return False

    async def generate(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> LLMResponse:
        """Генерировать ответ через Mistral API.

        Args:
            prompt: Промпт для LLM
            temperature: Температура генерации
            max_tokens: Максимальное количество токенов

        Returns:
            LLMResponse с ответом

        Raises:
            httpx.HTTPStatusError: При ошибке API
        """
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {self._api_key}",
        }

        payload = {
            "model": self._model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "https://api.mistral.ai/v1/chat/completions",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()

            data = response.json()

            return LLMResponse(
                content=data["choices"][0]["message"]["content"],
                model=self._model,
                usage={
                    "prompt_tokens": data.get("usage", {}).get("prompt_tokens", 0),
                    "completion_tokens": data.get("usage", {}).get(
                        "completion_tokens", 0
                    ),
                    "total_tokens": data.get("usage", {}).get("total_tokens", 0),
                },
            )
