"""Yandex Cloud (YandexGPT) провайдер."""

import httpx
import logging

from .base import BaseLLMProvider, LLMResponse
from ..config import get_llm_config

logger = logging.getLogger(__name__)

class YandexCloudProvider(BaseLLMProvider):
    """Провайдер Yandex Cloud.

    Attributes:
        api_key: API ключ
        folder_id: ID каталога Yandex Cloud
        model: Модель для использования
    """

    def __init__(self, api_key: str | None = None, folder_id: str | None = None):
        """Инициализировать провайдер."""
        config = get_llm_config()
        self._api_key = api_key or config.yandex_cloud_api_key
        self._folder_id = folder_id or config.yandex_cloud_folder
        self._model = f"gpt://{self._folder_id}/gpt-oss-20b/latest"

    @property
    def name(self) -> str:
        """Имя провайдера."""
        return "yandexcloud"

    def is_available(self) -> bool:
        """Проверить доступность провайдера."""
        return bool(self._api_key and self._folder_id)
    
    async def check_health(self) -> bool:
        """Проверить доступность API через эндпоинт /models."""
        if not self.is_available():
            return False
            
        headers = {"Authorization": f"Bearer {self._api_key}"}
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    "https://llm.api.cloud.yandex.net/v1/models",
                    headers=headers
                )
                return response.status_code == 200
        except Exception as e:
            logger.warning(f"Yandex Cloud health check failed: {e}")
            return False

    async def generate(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> LLMResponse:
        """Генерировать ответ через Yandex Cloud API.
        
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
        }

        payload = {
            "model": self._model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                response = await client.post(
                    "https://ai.api.cloud.yandex.net/v1/chat/completions",
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
                        "completion_tokens": data.get("usage", {}).get("completion_tokens", 0),
                        "total_tokens": data.get("usage", {}).get("total_tokens", 0),
                    },
                )
            except Exception as e:
                logger.error(f"Yandex Cloud API error: {e}")
                raise
