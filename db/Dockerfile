FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app

COPY pyproject.toml ./

ENV UV_SYSTEM_PYTHON=1

RUN uv sync

COPY . .

ENV PYTHONPATH=/app/src

EXPOSE 8000

CMD ["uv", "run", "alembic", "upgrade", "head"]
