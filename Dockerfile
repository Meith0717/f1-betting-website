FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_ENV=production \
    APP_PORT=8080

WORKDIR /app

# Install dependencies first for better layer caching
COPY src/requirements.txt /app/src/requirements.txt
RUN pip install --no-cache-dir -r /app/src/requirements.txt

# Copy application source (see .dockerignore for exclusions).
# Secrets (.env) are NOT baked into the image — docker-compose loads them
# via env_file at runtime, so a fresh clone builds without a .env present.
COPY src/ /app/src/

WORKDIR /app/src

# Data (JSON stores) and instance (logs, secret key) are volumes —
# mount them to persist across container restarts:
#   -v f1-data:/app/src/app/data -v f1-instance:/app/src/instance
VOLUME ["/app/src/app/data", "/app/src/instance"]

EXPOSE 8080

# Single worker: the in-process event manager (push notification scheduler)
# must not be duplicated across workers.
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "1", "wsgi:app"]
