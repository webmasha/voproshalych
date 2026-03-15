"""Точка входа в бизнес-логику для обработки нормализованных сообщений."""

from models.message import IncomingMessage
from models.response import ActionType, BotResponse, OutgoingAction


class BotService:
    """Обрабатывает нормализованные сообщения и возвращает платформенно-независимые действия."""

    def handle_message(self, message: IncomingMessage) -> BotResponse:
        """Обрабатывает сообщение и возвращает действия для адаптера платформы.

        Args:
            message: Нормализованное входящее сообщение от адаптера платформы.

        Returns:
            BotResponse: Действия, которые нужно выполнить на исходной платформе.
        """

        normalized_text = message.text.strip()
        lowered_text = normalized_text.lower()

        if lowered_text == "/start":
            reply_text = (
                "Привет. Я получил ваше сообщение через общий core-сервис."
            )
        elif lowered_text == "/ping":
            reply_text = "pong"
        else:
            reply_text = f"Echo: {normalized_text}"

        return BotResponse(
            actions=[
                OutgoingAction(
                    type=ActionType.send_text,
                    text=reply_text,
                )
            ]
        )
