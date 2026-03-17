"""Mistral AI провайдер."""

import httpx
from pydantic import Field

from .base import BaseLLMProvider, LLMResponse
from ..config import get_llm_config


class MistralProvider(BaseLLMProvider):
    """Провайдер Mistral AI.

    Attributes:
        api_key: API ключ Mistral
        model: Модель для использования
    """

    def __init__(self, api_key: str | None = None):
        """Инициализировать провайдер.

        Args:
            api_key: API ключ (опционально, берется из конфига)
        """
        config = get_llm_config()
        self._api_key = api_key or config.mistral_api_key
        self._model = "open-mistral-nemo"

    @property
    def name(self) -> str:
        """Имя провайдера."""
        return "mistral"

    def is_available(self) -> bool:
        """Проверить доступность провайдера."""
        return bool(self._api_key)

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
