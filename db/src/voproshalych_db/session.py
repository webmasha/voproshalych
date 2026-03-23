"""Database session management."""

import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from dotenv import load_dotenv


# Найти .env файл
def _find_env_file() -> Path | None:
    current = Path(__file__).parent
    for _ in range(5):
        env_path = current / ".env"
        if env_path.exists():
            return env_path
        current = current.parent
    return None


if env_file := _find_env_file():
    load_dotenv(env_file)

# Конфигурация базы данных
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_DB = os.getenv("POSTGRES_DB", "voproshalych")
POSTGRES_USER = os.getenv("POSTGRES_USER", "voproshalych")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "voproshalych")

DATABASE_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"

engine = create_engine(DATABASE_URL, pool_pre_ping=True, echo=False)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Session:
    """Получить сессию БД."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
