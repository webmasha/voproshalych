FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app

COPY pyproject.toml ./

ENV UV_SYSTEM_PYTHON=1

RUN uv sync

COPY src/ ./src/

ENV PYTHONPATH=/app/src

EXPOSE 8004

CMD ["uv", "run", "uvicorn", "qa.main:app", "--host", "0.0.0.0", "--port", "8004"]
