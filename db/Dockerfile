FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml ./

RUN pip install uv && \
    uv sync

COPY . .

ENV PYTHONPATH=/app/src

EXPOSE 8000

CMD ["uv", "run", "alembic", "upgrade", "head"]
