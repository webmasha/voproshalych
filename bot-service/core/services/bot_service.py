"""Точка входа в бизнес-логику для обработки нормализованных сообщений."""

import os

import httpx
from models.message import IncomingMessage
from models.response import ActionType, BotResponse, OutgoingAction


class BotService:
    """Обрабатывает нормализованные сообщения и возвращает платформенно-независимые действия."""

    def __init__(self):
        """Инициализировать сервис."""
        self.qa_service_url = os.getenv("QA_SERVICE_URL", "http://qa-service:8004")

    def handle_message(self, message: IncomingMessage) -> BotResponse:
        """Обработать сообщение и вернуть действия для адаптера платформы.

        Args:
            message: Нормализованное входящее сообщение от адаптера платформы.

        Returns:
            BotResponse: Действия, которые нужно выполнить на исходной платформе.
        """
        normalized_text = message.text.strip()
        lowered_text = normalized_text.lower()

        if lowered_text == "/start":
            reply_text = (
                "Привет! Я — виртуальный помощник ТюмГУ. Могу ответить на вопросы "
                "о документах, правилах, поступлении и других темах. Задай вопрос!"
            )
        elif lowered_text == "/ping":
            reply_text = "pong"
        else:
            reply_text = self._call_qa_service(normalized_text)

        return BotResponse(
            actions=[
                OutgoingAction(
                    type=ActionType.send_text,
                    text=reply_text,
                )
            ]
        )

    def _call_qa_service(self, question: str) -> str:
        """Вызвать QA-сервис для получения ответа от LLM.

        Args:
            question: Вопрос пользователя

        Returns:
            Ответ от LLM
        """
        try:
            with httpx.Client(timeout=60.0) as client:
                response = client.post(
                    f"{self.qa_service_url}/qa",
                    json={"question": question},
                )
                response.raise_for_status()
                data = response.json()
                return data.get("answer", "Не удалось получить ответ")
        except Exception as e:
            return f"Ошибка при получении ответа: {e}"
