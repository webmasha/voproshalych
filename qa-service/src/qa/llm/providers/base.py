"""Провайдеры LLM."""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class LLMResponse:
    """Ответ от LLM.

    Attributes:
        content: Текст ответа
        model: Название модели
        usage: Количество использованных токенов
    """

    content: str
    model: str
    usage: dict[str, int]


class BaseLLMProvider(ABC):
    """Базовый класс провайдера LLM."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Имя провайдера."""
        pass

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> LLMResponse:
        """Генерировать ответ.

        Args:
            prompt: Промпт для LLM
            temperature: Температура генерации
            max_tokens: Максимальное количество токенов

        Returns:
            LLMResponse с ответом
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Проверить доступность провайдера."""
        pass
