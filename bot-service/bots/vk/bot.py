"""VK-адаптер на базе vkbottle.

Модуль принимает события VK, нормализует входящие текстовые сообщения к общему
контракту core, отправляет их в FastAPI-сервис и выполняет возвращенные действия.
"""

from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import httpx
from vkbottle.bot import Bot, Message


logging.basicConfig(level=logging.INFO)


@dataclass(slots=True)
class Settings:
    """Настройки запуска VK-адаптера."""

    vk_bot_token: str = os.getenv("VK_BOT_TOKEN", "")
    bot_core_url: str = os.getenv("BOT_CORE_URL", "http://127.0.0.1:8000")
    request_timeout_seconds: float = float(
        os.getenv("BOT_CORE_TIMEOUT_SECONDS", "10")
    )


class CoreClient:
    """Асинхронный HTTP-клиент для общего bot core."""

    def __init__(self, settings: Settings) -> None:
        """Инициализирует HTTP-клиент.

        Args:
            settings: Настройки запуска VK-адаптера.
        """

        self._client = httpx.AsyncClient(
            base_url=settings.bot_core_url.rstrip("/"),
            timeout=settings.request_timeout_seconds,
        )

    async def close(self) -> None:
        """Закрывает внутренний HTTP-клиент."""

        await self._client.aclose()

    async def process_message(self, message: Message) -> dict[str, Any]:
        """Отправляет нормализованное сообщение VK в core-сервис.

        Args:
            message: Сообщение VK, полученное через vkbottle.

        Returns:
            dict[str, Any]: JSON-ответ от core-сервиса.
        """

        payload = self._build_payload(message)
        response = await self._client.post("/messages", json=payload)
        response.raise_for_status()
        return response.json()

    def _build_payload(self, message: Message) -> dict[str, Any]:
        """Преобразует сообщение VK в общий контракт core.

        Args:
            message: Сообщение VK, полученное через vkbottle.

        Returns:
            dict[str, Any]: JSON-полезная нагрузка по входной схеме core.
        """

        sent_at = datetime.now(UTC).isoformat()
        if message.date is not None:
            sent_at = datetime.fromtimestamp(message.date, tz=UTC).isoformat()

        return {
            "platform": "vk",
            "user_id": str(message.from_id),
            "chat_id": str(message.peer_id),
            "text": message.text or "",
            "message_id": str(message.conversation_message_id)
            if message.conversation_message_id is not None
            else None,
            "timestamp": sent_at,
            "metadata": {
                "peer_id": message.peer_id,
                "conversation_message_id": message.conversation_message_id,
                "group_id": message.group_id,
            },
        }


def build_bot(settings: Settings, core_client: CoreClient) -> Bot:
    """Создает экземпляр VK-бота и подключает обработчики сообщений.

    Args:
        settings: Настройки запуска VK-адаптера.
        core_client: HTTP-клиент для общего core-сервиса.

    Returns:
        Bot: Настроенный VK-бот.
    """

    bot = Bot(settings.vk_bot_token)

    @bot.on.message()
    async def handle_text_message(message: Message) -> None:
        """Проксирует текстовые сообщения в core-сервис и выполняет действия.

        Args:
            message: Сообщение VK, полученное через vkbottle.
        """

        if not message.text:
            return

        try:
            bot_response = await core_client.process_message(message)
        except httpx.HTTPError:
            logging.exception("Не удалось обработать сообщение VK через core")
            await message.answer("Сервис временно недоступен.")
            return

        for action in bot_response.get("actions", []):
            if action.get("type") == "send_text" and action.get("text"):
                await message.answer(action["text"])

    return bot


def main() -> None:
    """Запускает long polling VK и пересылает сообщения в core-сервис."""

    settings = Settings()
    if not settings.vk_bot_token:
        raise RuntimeError("VK_BOT_TOKEN is not set")

    core_client = CoreClient(settings)
    bot = build_bot(settings, core_client)

    try:
        bot.run_forever()
    finally:
        asyncio.run(core_client.close())


if __name__ == "__main__":
    main()
