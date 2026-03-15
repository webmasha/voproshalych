"""Общие выходные модели, которые возвращает core-сервис бота."""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ActionType(str, Enum):
    """Поддерживаемые типы действий, которые возвращает core."""

    send_text = "send_text"


class OutgoingAction(BaseModel):
    """Действие, которое должен выполнить адаптер платформы.

    Attributes:
        type: Тип действия, понятный платформенным адаптерам.
        text: Текстовая нагрузка для текстовых действий.
        metadata: Дополнительные параметры для адаптера платформы.
    """

    type: ActionType
    text: str | None = Field(
        default=None,
        description="Текстовая нагрузка для текстовых действий",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Необязательные параметры действия для платформенных адаптеров",
    )


class BotResponse(BaseModel):
    """Ответ слоя бизнес-логики core."""

    actions: list[OutgoingAction] = Field(default_factory=list)
