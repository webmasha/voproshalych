"""Общие выходные модели, которые возвращает core-сервис бота."""

from enum import Enum

from pydantic import BaseModel, Field


class ActionType(str, Enum):
    """Поддерживаемые типы действий, которые возвращает core."""

    send_text = "send_text"


class InlineButton(BaseModel):
    """Inline-кнопка, которую должен показать адаптер платформы.

    Attributes:
        text: Текст на кнопке.
        callback_data: Данные callback-события.
    """

    text: str = Field(..., description="Текст кнопки")
    callback_data: str = Field(..., description="Данные callback-события")


class OutgoingAction(BaseModel):
    """Действие, которое должен выполнить адаптер платформы.

    Attributes:
        type: Тип действия, понятный платформенным адаптерам.
        text: Текстовая нагрузка для текстовых действий.
        buttons: Inline-кнопки для отображения под сообщением.
    """

    type: ActionType
    text: str | None = Field(
        default=None,
        description="Текстовая нагрузка для текстовых действий",
    )
    buttons: list[list[InlineButton]] = Field(
        default_factory=list,
        description="Inline-кнопки для платформенных адаптеров",
    )


class BotResponse(BaseModel):
    """Ответ слоя бизнес-логики core."""

    actions: list[OutgoingAction] = Field(default_factory=list)
