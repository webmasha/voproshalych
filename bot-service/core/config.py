"""Объекты конфигурации для core-сервиса."""

from dataclasses import dataclass
import os


@dataclass(slots=True)
class Settings:
    """Настройки запуска FastAPI core-сервиса."""

    app_name: str = os.getenv("BOT_CORE_APP_NAME", "bot-core")
    app_version: str = os.getenv("BOT_CORE_APP_VERSION", "0.1.0")
    postgres_host: str = os.getenv("POSTGRES_HOST", "localhost")
    postgres_port: str = os.getenv("POSTGRES_PORT", "5432")
    postgres_db: str = os.getenv("POSTGRES_DB", "voproshalych")
    postgres_user: str = os.getenv("POSTGRES_USER", "voproshalych")
    postgres_password: str = os.getenv("POSTGRES_PASSWORD", "voproshalych")
    qa_service_url: str = os.getenv("QA_SERVICE_URL", "http://qa-service:8004")
    qa_service_timeout_seconds: float = float(
        os.getenv("QA_SERVICE_TIMEOUT_SECONDS", "30")
    )


settings = Settings()
