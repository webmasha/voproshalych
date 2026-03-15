"""Telegram-адаптер на базе aiogram.

Модуль принимает обновления Telegram, нормализует их к общему контракту core,
отправляет в FastAPI-сервис и выполняет возвращенные действия.
"""

from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass
from datetime import datetime, UTC
from typing import Any

import httpx
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message


logging.basicConfig(level=logging.INFO)


@dataclass(slots=True)
class Settings:
    """Настройки запуска Telegram-адаптера."""

    telegram_bot_token: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    bot_core_url: str = os.getenv("BOT_CORE_URL", "http://127.0.0.1:8000")
    request_timeout_seconds: float = float(
        os.getenv("BOT_CORE_TIMEOUT_SECONDS", "10")
    )


class CoreClient:
    """Асинхронный HTTP-клиент для общего bot core."""

    def __init__(self, settings: Settings) -> None:
        """Инициализирует HTTP-клиент.

        Args:
            settings: Настройки запуска Telegram-адаптера.
        """

        self._settings = settings
        self._client = httpx.AsyncClient(
            base_url=settings.bot_core_url.rstrip("/"),
            timeout=settings.request_timeout_seconds,
        )

    async def close(self) -> None:
        """Закрывает внутренний HTTP-клиент."""

        await self._client.aclose()

    async def process_message(self, message: Message) -> dict[str, Any]:
        """Отправляет нормализованное сообщение Telegram в core-сервис.

        Args:
            message: Сообщение Telegram, полученное через aiogram.

        Returns:
            dict[str, Any]: JSON-ответ от core-сервиса.
        """

        payload = self._build_payload(message)
        response = await self._client.post("/messages", json=payload)
        response.raise_for_status()
        return response.json()

    def _build_payload(self, message: Message) -> dict[str, Any]:
        """Преобразует сообщение Telegram в общий контракт core.

        Args:
            message: Сообщение Telegram, полученное через aiogram.

        Returns:
            dict[str, Any]: JSON-полезная нагрузка по входной схеме core.
        """

        sent_at = (
            message.date.astimezone(UTC).isoformat()
            if message.date
            else datetime.now(UTC).isoformat()
        )

        return {
            "platform": "telegram",
            "user_id": str(message.from_user.id),
            "chat_id": str(message.chat.id),
            "text": message.text or "",
            "message_id": str(message.message_id),
            "timestamp": sent_at,
            "metadata": {
                "username": message.from_user.username,
                "first_name": message.from_user.first_name,
                "last_name": message.from_user.last_name,
                "chat_type": message.chat.type,
            },
        }


def build_dispatcher(core_client: CoreClient) -> Dispatcher:
    """Создает dispatcher aiogram и подключает обработчики сообщений.

    Args:
        core_client: HTTP-клиент для общего core-сервиса.

    Returns:
        Dispatcher: Настроенный dispatcher aiogram.
    """

    dispatcher = Dispatcher()

    @dispatcher.message(Command("start", "ping"))
    @dispatcher.message(F.text)
    async def handle_text_message(message: Message) -> None:
        """Проксирует текстовые сообщения в core-сервис и выполняет действия.

        Args:
            message: Сообщение Telegram, полученное через aiogram.
        """

        if not message.text or not message.from_user:
            return

        try:
            bot_response = await core_client.process_message(message)
        except httpx.HTTPError:
            logging.exception("Failed to process Telegram message via core")
            await message.answer("Сервис временно недоступен.")
            return

        for action in bot_response.get("actions", []):
            if action.get("type") == "send_text" and action.get("text"):
                await message.answer(action["text"])

    return dispatcher


async def main() -> None:
    """Запускает polling Telegram и пересылает сообщения в core-сервис."""

    settings = Settings()

    if not settings.telegram_bot_token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not set")

    bot = Bot(token=settings.telegram_bot_token)
    core_client = CoreClient(settings)
    dispatcher = build_dispatcher(core_client)

    try:
        await dispatcher.start_polling(bot)
    finally:
        await core_client.close()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
