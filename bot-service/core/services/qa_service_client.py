"""Клиент для обращения к QA-сервису."""

import httpx


class QAServiceClient:
    """Синхронный HTTP-клиент для QA-сервиса."""

    def __init__(self, base_url: str, timeout_seconds: float) -> None:
        """Инициализирует клиента QA-сервиса.

        Args:
            base_url: Базовый URL QA-сервиса.
            timeout_seconds: Таймаут запросов в секундах.
        """

        self._client = httpx.Client(
            base_url=base_url.rstrip("/"),
            timeout=timeout_seconds,
        )

    def ask(self, question: str, context: str | None = None) -> str:
        """Отправляет вопрос в QA-сервис и возвращает текст ответа.

        Args:
            question: Вопрос пользователя.
            context: Дополнительный контекст.

        Returns:
            str: Ответ QA-сервиса.
        """

        response = self._client.post(
            "/qa",
            json={
                "question": question,
                "context": context,
            },
        )
        response.raise_for_status()

        payload = response.json()
        return payload["answer"]
