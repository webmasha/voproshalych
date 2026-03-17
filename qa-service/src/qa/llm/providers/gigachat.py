"""GigaChat провайдер."""

import base64
import time

import httpx

from .base import BaseLLMProvider, LLMResponse
from ..config import get_llm_config


class GigaChatProvider(BaseLLMProvider):
    """Провайдер GigaChat (Сбер).

    Attributes:
        client_id: Client ID GigaChat
        client_secret: Client Secret GigaChat
        model: Модель для использования
    """

    def __init__(self, client_id: str | None = None, client_secret: str | None = None):
        """Инициализировать провайдер.

        Args:
            client_id: Client ID (опционально, берется из конфига)
            client_secret: Client Secret (опционально, берется из конфига)
        """
        config = get_llm_config()
        self._client_id = client_id or config.gigachat_client_id
        self._client_secret = client_secret or config.gigachat_client_secret
        self._model = "GigaChat"
        self._access_token: str | None = None
        self._token_expires_at: float = 0

    @property
    def name(self) -> str:
        """Имя провайдера."""
        return "gigachat"

    def is_available(self) -> bool:
        """Проверить доступность провайдера."""
        return bool(self._client_id and self._client_secret)

    async def _get_access_token(self) -> str:
        """Получить access token.

        Returns:
            Access token

        Raises:
            httpx.HTTPStatusError: При ошибке API
        """
        if self._access_token and time.time() < self._token_expires_at:
            return self._access_token

        credentials = f"{self._client_id}:{self._client_secret}"
        encoded = base64.b64encode(credentials.encode()).decode()

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
            "Authorization": f"Basic {encoded}",
        }

        payload = {
            "scope": "GIGACHAT_API_PERS",
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://ngw.devices.sberbank.ru:9443/api/v2/oauth",
                headers=headers,
                data=payload,
            )
            response.raise_for_status()

            data = response.json()
            access_token = data["access_token"]
            self._access_token = access_token
            self._token_expires_at = time.time() + data.get("expires_at", 1800)

            return access_token

    async def generate(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> LLMResponse:
        """Генерировать ответ через GigaChat API.

        Args:
            prompt: Промпт для LLM
            temperature: Температура генерации
            max_tokens: Максимальное количество токенов

        Returns:
            LLMResponse с ответом

        Raises:
            httpx.HTTPStatusError: При ошибке API
        """
        access_token = await self._get_access_token()

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {access_token}",
        }

        payload = {
            "model": self._model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "n": 1,
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "https://ngw.devices.sberbank.ru:9443/api/v2/chat/completions",
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
