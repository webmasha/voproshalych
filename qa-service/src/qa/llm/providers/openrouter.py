"""OpenRouter провайдер."""

import httpx

from .base import BaseLLMProvider, LLMResponse
from ..config import get_llm_config


class OpenRouterProvider(BaseLLMProvider):
    """Провайдер OpenRouter.

    Attributes:
        api_key: API ключ OpenRouter
        model: Модель для использования
    """

    def __init__(self, api_key: str | None = None):
        """Инициализировать провайдер.

        Args:
            api_key: API ключ (опционально, берется из конфига)
        """
        config = get_llm_config()
        self._api_key = api_key or config.openrouter_api_key
        self._model = "openrouter/free"

    @property
    def name(self) -> str:
        """Имя провайдера."""
        return "openrouter"

    def is_available(self) -> bool:
        """Проверить доступность провайдера."""
        return bool(self._api_key)

    async def generate(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> LLMResponse:
        """Генерировать ответ через OpenRouter API.

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
            "Authorization": f"Bearer {self._api_key}",
            "HTTP-Referer": "https://voproshalych.utmn.ru",
            "X-Title": "Voproshalych",
        }

        payload = {
            "model": self._model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()

            data = response.json()

            return LLMResponse(
                content=data["choices"][0]["message"]["content"],
                model=data.get("model", self._model),
                usage={
                    "prompt_tokens": data.get("usage", {}).get("prompt_tokens", 0),
                    "completion_tokens": data.get("usage", {}).get(
                        "completion_tokens", 0
                    ),
                    "total_tokens": data.get("usage", {}).get("total_tokens", 0),
                },
            )
