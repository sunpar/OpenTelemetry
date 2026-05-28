FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/services/auth-api/src \
    AUTH_API_HOST=0.0.0.0 \
    AUTH_API_PORT=8000 \
    AUTH_DB_PATH=/data/auth-api.sqlite3

WORKDIR /app

COPY packages/auth-core ./packages/auth-core
COPY services/auth-api ./services/auth-api
RUN pip install --no-cache-dir ./packages/auth-core ./services/auth-api

RUN mkdir -p /data

WORKDIR /app/services/auth-api

EXPOSE 8000

CMD ["sh", "-c", "exec uvicorn auth_api.app:app --host ${AUTH_API_HOST} --port ${AUTH_API_PORT}"]
