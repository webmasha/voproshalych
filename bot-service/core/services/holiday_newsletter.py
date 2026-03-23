"""Сервис праздничной рассылки."""

from __future__ import annotations

from datetime import date

from sqlalchemy import and_, extract, or_

from db import Holiday, User, get_session


class HolidayNewsletterService:
    """Подготавливает данные для праздничной рассылки."""

    def get_today_holiday(self, today: date | None = None) -> Holiday | None:
        """Возвращает праздник на указанную дату.

        Args:
            today: Дата проверки.

        Returns:
            Holiday | None: Праздник или `None`.
        """

        today = today or date.today()
        session = get_session()
        try:
            return (
                session.query(Holiday)
                .filter(
                    or_(
                        and_(
                            Holiday.month == today.month,
                            Holiday.day_of_month == today.day,
                        ),
                        and_(
                            extract("month", Holiday.date) == today.month,
                            extract("day", Holiday.date) == today.day,
                        ),
                    )
                )
                .order_by(Holiday.id.asc())
                .first()
            )
        finally:
            session.close()

    def get_subscribed_users(self) -> list[User]:
        """Возвращает подписанных пользователей для будущей рассылки.

        Returns:
            list[User]: Подписанные пользователи.
        """

        session = get_session()
        try:
            return session.query(User).filter(User.is_subscribed.is_(True)).all()
        finally:
            session.close()
