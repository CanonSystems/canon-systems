# Build from repository root (linux/amd64 for ECS Fargate):
#   docker buildx build --platform linux/amd64 \
#     -f docker/knowledge-api/Dockerfile \
#     -t knowledge-api:local .
FROM python:3.12-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1

RUN apt-get update \
  && apt-get install -y --no-install-recommends build-essential libpq-dev \
  && rm -rf /var/lib/apt/lists/*

COPY backend/shared /app/backend/shared
COPY backend/knowledge-schema /app/backend/knowledge-schema
COPY backend/knowledge-policy /app/backend/knowledge-policy
COPY backend/memory-adapter /app/backend/memory-adapter
COPY backend/state-api /app/backend/state-api
COPY backend/knowledge-api /app/backend/knowledge-api

RUN pip install --no-cache-dir --upgrade pip \
  && pip install --no-cache-dir -e /app/backend/shared \
  && pip install --no-cache-dir -e /app/backend/knowledge-schema \
  && pip install --no-cache-dir -e /app/backend/knowledge-policy \
  && pip install --no-cache-dir -e /app/backend/memory-adapter \
  && pip install --no-cache-dir -e /app/backend/state-api \
  && pip install --no-cache-dir -e /app/backend/knowledge-api

WORKDIR /app/backend/knowledge-api

EXPOSE 8080
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
