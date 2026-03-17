"""Database models for Voproshalych."""

from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    Boolean,
    ForeignKey,
    Index,
)
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from voproshalych_db.models.base import Base


class User(Base):
    """Пользователь платформы."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    platform = Column(String(20), nullable=False)  # telegram, vk, max
    platform_user_id = Column(String(100), nullable=False)
    username = Column(String(255), nullable=True)
    first_name = Column(String(255), nullable=True)
    last_name = Column(String(255), nullable=True)
    is_subscribed = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        Index("idx_users_platform", "platform"),
        Index("idx_users_platform_user_id", "platform", "platform_user_id"),
    )


class Session(Base):
    """Сессия пользователя."""

    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    state = Column(String(20), default="START")  # START, DIALOG, WAITING_ANSWER
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    last_message_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", backref="sessions")


class Message(Base):
    """Сообщение в чате."""

    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False)
    role = Column(String(10), nullable=False)  # user, assistant
    content = Column(Text, nullable=False)
    model_used = Column(String(50), nullable=True)
    used_chunk_ids = Column(ARRAY(UUID), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    session = relationship("Session", backref="messages")


class QuestionAnswer(Base):
    """Пара вопрос-ответ."""

    __tablename__ = "questions_answers"

    id = Column(Integer, primary_key=True, index=True)
    question_id = Column(Integer, ForeignKey("messages.id"), nullable=False)
    answer_id = Column(Integer, ForeignKey("messages.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Chunk(Base):
    """Чанк базы знаний."""

    __tablename__ = "chunks"

    id = Column(
        UUID(as_uuid=True), primary_key=True, default=lambda: __import__("uuid").uuid4()
    )
    text = Column(Text, nullable=False)
    source_url = Column(String(500), nullable=True)
    source_type = Column(String(50), nullable=True)
    title = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Embedding(Base):
    """Вектор эмбеддинга."""

    __tablename__ = "embeddings"

    id = Column(Integer, primary_key=True, index=True)
    chunk_id = Column(
        UUID(as_uuid=True), ForeignKey("chunks.id", ondelete="CASCADE"), nullable=False
    )
    # vector(1024) - будет создано через миграцию alembic
    embedding = Column(Text, nullable=False)  # храним как JSON/массив для совместимости
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    chunk = relationship("Chunk", backref="embeddings")


class Subscription(Base):
    """Подписка на рассылку."""

    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    subscribed_at = Column(DateTime(timezone=True), server_default=func.now())
    unsubscribed_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", backref="subscriptions")


class Holiday(Base):
    """Праздник."""

    __tablename__ = "holidays"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    date = Column(DateTime, nullable=True)  # Конкретная дата
    month = Column(Integer, nullable=True)  # Для повторяющихся (1-12)
    day_of_month = Column(Integer, nullable=True)  # Для повторяющихся (1-31)
    type = Column(String(20), nullable=True)
    male_holiday = Column(Boolean, default=False)
    female_holiday = Column(Boolean, default=False)
    template_prompt = Column(Text, nullable=True)


class TelemetryLog(Base):
    """Логи телеметрии."""

    __tablename__ = "telemetry_logs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    level = Column(String(10), nullable=True)  # INFO, WARNING, ERROR
    request_id = Column(UUID(as_uuid=True), nullable=True)
    service = Column(String(50), nullable=True)
    payload = Column(Text, nullable=True)  # JSON


class AgentTrace(Base):
    """Трассировка агента."""

    __tablename__ = "agent_traces"

    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(UUID(as_uuid=True), nullable=True)
    step = Column(Integer, nullable=True)
    phase = Column(String(20), nullable=True)  # reasoning, acting, evaluation
    thought = Column(Text, nullable=True)
    action = Column(String(50), nullable=True)
    action_input = Column(Text, nullable=True)
    observation = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
