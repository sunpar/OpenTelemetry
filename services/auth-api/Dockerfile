FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src \
    AUTH_API_HOST=0.0.0.0 \
    AUTH_API_PORT=8000 \
    AUTH_DB_PATH=/data/auth-api.sqlite3

WORKDIR /app

COPY pyproject.toml ./
RUN pip install --no-cache-dir .

COPY src ./src
COPY migrations ./migrations

RUN mkdir -p /data

EXPOSE 8000

CMD ["sh", "-c", "exec uvicorn app:app --host ${AUTH_API_HOST} --port ${AUTH_API_PORT}"]
