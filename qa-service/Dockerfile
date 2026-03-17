FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml ./

RUN pip install uv && \
    uv sync

COPY src/ ./src/

ENV PYTHONPATH=/app/src

EXPOSE 8004

CMD ["uv", "run", "uvicorn", "qa.main:app", "--host", "0.0.0.0", "--port", "8004"]
