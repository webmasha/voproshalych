"""Точка входа в бизнес-логику для обработки нормализованных сообщений."""

from config import settings
from models.callback import CallbackEvent
from models.message import IncomingMessage
from models.response import ActionType, BotResponse, InlineButton, OutgoingAction
from services.holiday_newsletter import HolidayNewsletterService
from services.qa_service_client import QAServiceClient
from services.user_service import UserService


class BotService:
    """Обрабатывает нормализованные сообщения и возвращает платформенно-независимые действия."""

    def __init__(self) -> None:
        """Инициализирует зависимости бизнес-логики."""

        self._qa_service_client = QAServiceClient(
            base_url=settings.qa_service_url,
            timeout_seconds=settings.qa_service_timeout_seconds,
        )
        self._user_service = UserService()
        self._holiday_newsletter_service = HolidayNewsletterService()

    def handle_message(self, message: IncomingMessage) -> BotResponse:
        """Обрабатывает сообщение и возвращает действия для адаптера платформы.

        Args:
            message: Нормализованное входящее сообщение от адаптера платформы.

        Returns:
            BotResponse: Действия, которые нужно выполнить на исходной платформе.
        """

        user = self._user_service.upsert_user(message)

        if message.message_type == "text":
            return self._handle_text_message(message, user)
        if message.message_type == "voice":
            return self._handle_voice_message(message)
        return self._build_unsupported_message_response(message)

    def handle_callback(self, event: CallbackEvent) -> BotResponse:
        """Обрабатывает callback-событие платформы.

        Args:
            event: Нормализованное callback-событие.

        Returns:
            BotResponse: Ответ для callback-события.
        """

        if event.callback_data == "subscription:toggle":
            user = self._user_service.toggle_subscription(event)
            if user is None:
                return BotResponse(
                    actions=[
                        OutgoingAction(
                            type=ActionType.send_text,
                            text="Не удалось изменить статус подписки.",
                        )
                    ]
                )

            return BotResponse(
                actions=[
                    OutgoingAction(
                        type=ActionType.send_text,
                        text=(
                            "Вы подписаны на праздничную рассылку."
                            if user.is_subscribed
                            else "Вы отписались от праздничной рассылки."
                        ),
                        buttons=self._build_start_buttons(user.is_subscribed),
                    )
                ]
            )

        if event.callback_data == "dialog:start_new":
            return BotResponse(
                actions=[
                    OutgoingAction(
                        type=ActionType.send_text,
                        text="Новый диалог будет доступен после подключения истории сообщений.",
                    )
                ]
            )

        return BotResponse(actions=[])

    def _handle_text_message(self, message: IncomingMessage, user) -> BotResponse:
        """Обрабатывает текстовое сообщение.

        Args:
            message: Нормализованное текстовое сообщение.
            user: Текущий пользователь из БД.

        Returns:
            BotResponse: Ответ для текстового сообщения.
        """

        normalized_text = (message.text or "").strip()
        lowered_text = normalized_text.lower()

        if lowered_text == "/start":
            return self._build_start_response(message, user)
        if lowered_text == "/ping":
            reply_text = "pong"
        else:
            reply_text = self._ask_qa_service(normalized_text)

        return BotResponse(
            actions=[
                OutgoingAction(
                    type=ActionType.send_text,
                    text=reply_text,
                    buttons=self._build_feedback_buttons(),
                )
            ]
        )

    def _handle_voice_message(self, message: IncomingMessage) -> BotResponse:
        """Обрабатывает голосовое сообщение.

        Args:
            message: Нормализованное голосовое сообщение.

        Returns:
            BotResponse: Заглушка до интеграции STT.
        """

        return BotResponse(
            actions=[
                OutgoingAction(
                    type=ActionType.send_text,
                    text=(
                        "Я получил голосовое сообщение. "
                        "Скоро здесь будет распознавание речи."
                    ),
                )
            ]
        )

    def _build_unsupported_message_response(
        self,
        message: IncomingMessage,
    ) -> BotResponse:
        """Возвращает ответ для неподдерживаемого типа сообщения.

        Args:
            message: Нормализованное входящее сообщение.

        Returns:
            BotResponse: Сообщение о неподдерживаемом формате.
        """

        reply_text = (
            f"Формат сообщения {message.message_type} пока не поддерживается."
        )

        return BotResponse(
            actions=[
                OutgoingAction(
                    type=ActionType.send_text,
                    text=reply_text,
                )
            ]
        )

    def _ask_qa_service(self, question: str) -> str:
        """Отправляет вопрос в QA-сервис и возвращает ответ.

        Args:
            question: Текст вопроса пользователя.

        Returns:
            str: Ответ QA-сервиса или fallback-текст.
        """

        try:
            return self._qa_service_client.ask(question=question)
        except Exception:
            return (
                "Сейчас не удалось получить ответ от QA-сервиса. "
                "Попробуйте повторить запрос позже."
            )

    def _build_start_response(self, message: IncomingMessage, user) -> BotResponse:
        """Возвращает стартовое сообщение и базовые inline-кнопки.

        Args:
            message: Нормализованное входящее сообщение.
            user: Текущий пользователь из БД.

        Returns:
            BotResponse: Ответ для команды `/start`.
        """

        is_subscribed = bool(user.is_subscribed) if user is not None else False

        return BotResponse(
            actions=[
                OutgoingAction(
                    type=ActionType.send_text,
                    text=(
                        "Привет. Я помогу начать новый диалог и подготовлен "
                        "для подписки на рассылку."
                    ),
                    buttons=self._build_start_buttons(is_subscribed),
                )
            ]
        )

    def _build_start_buttons(self, is_subscribed: bool) -> list[list[InlineButton]]:
        """Возвращает кнопки стартового сообщения.

        Args:
            is_subscribed: Текущий статус подписки.

        Returns:
            list[list[InlineButton]]: Кнопки стартового сообщения.
        """

        subscription_text = (
            "Отписаться от рассылки" if is_subscribed else "Подписаться на рассылку"
        )

        return [
            [
                InlineButton(
                    text="Начать новый диалог",
                    callback_data="dialog:start_new",
                )
            ],
            [
                InlineButton(
                    text=subscription_text,
                    callback_data="subscription:toggle",
                )
            ],
        ]

    def _build_feedback_buttons(self) -> list[list[InlineButton]]:
        """Возвращает inline-кнопки для оценки ответа.

        Returns:
            list[list[InlineButton]]: Кнопки лайка и дизлайка.
        """

        return [
            [
                InlineButton(text="👍", callback_data="feedback:like"),
                InlineButton(text="👎", callback_data="feedback:dislike"),
            ]
        ]
