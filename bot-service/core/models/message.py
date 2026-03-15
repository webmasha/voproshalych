"""Общие входные модели для платформенных адаптеров и core-сервиса."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class Platform(str, Enum):
    """Поддерживаемые платформы ботов."""

    telegram = "telegram"
    vk = "vk"
    max = "max"


class IncomingMessage(BaseModel):
    """Нормализованное сообщение, полученное от любого адаптера платформы.

    Attributes:
        platform: Идентификатор исходной платформы.
        user_id: Идентификатор пользователя на конкретной платформе.
        chat_id: Идентификатор чата на конкретной платформе.
        text: Нормализованный текст сообщения.
        message_id: Идентификатор сообщения на конкретной платформе.
        timestamp: Исходное время сообщения, если оно доступно.
        metadata: Дополнительные платформенно-специфичные поля.
    """

    platform: Platform
    user_id: str = Field(..., description="Идентификатор пользователя на платформе")
    chat_id: str = Field(..., description="Идентификатор чата на платформе")
    text: str = Field(..., min_length=1, description="Нормализованный текст сообщения")
    message_id: str | None = Field(
        default=None,
        description="Идентификатор сообщения на платформе",
    )
    timestamp: datetime | None = Field(
        default=None,
        description="Время создания сообщения, если платформа его передает",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Дополнительные поля платформы вне основного контракта core",
    )
