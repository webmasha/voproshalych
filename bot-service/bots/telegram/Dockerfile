FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY bot-service/pyproject.toml /tmp/pyproject.toml
RUN pip install --no-cache-dir --upgrade pip setuptools wheel
RUN pip install --no-cache-dir --no-build-isolation "/tmp[telegram]"

COPY bot-service/bots/telegram /app

CMD ["python", "bot.py"]
