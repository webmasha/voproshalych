"""FastAPI-приложение, которое отдает общую бизнес-логику бота."""

from fastapi import FastAPI

from config import settings
from models.message import IncomingMessage
from models.response import BotResponse
from services.bot_service import BotService


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
)
bot_service = BotService()


@app.get("/health")
def healthcheck() -> dict[str, str]:
    """Возвращает статус доступности сервиса."""

    return {"status": "ok"}


@app.post("/messages", response_model=BotResponse)
def process_message(message: IncomingMessage) -> BotResponse:
    """Обрабатывает нормализованное сообщение через общую бизнес-логику.

    Args:
        message: Нормализованное сообщение, полученное от адаптера платформы.

    Returns:
        BotResponse: Действия, которые должен выполнить вызывающий адаптер.
    """

    return bot_service.handle_message(message)
