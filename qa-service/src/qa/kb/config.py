"""KB configuration."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv


def _find_env_file() -> Path | None:
    """Find .env file."""
    current = Path(__file__).parent
    for _ in range(5):
        env_path = current / ".env"
        if env_path.exists():
            return env_path
        current = current.parent
    return None


if env_file := _find_env_file():
    load_dotenv(env_file)


class KBConfig(BaseSettings):
    """Knowledge Base configuration."""

    embedding_model: str = "deepvk/USER-bge-m3"
    chunk_size: int = 1000
    chunk_overlap: int = 200
    min_chunk_size: int = 100

    model_config = SettingsConfigDict(
        env_prefix="",
        case_sensitive=False,
    )


_config: KBConfig | None = None


def get_kb_config() -> KBConfig:
    """Get KB configuration."""
    global _config
    if _config is None:
        _config = KBConfig()
    return _config
