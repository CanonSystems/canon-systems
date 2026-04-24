# Build from repository root:
#   docker build -f docker/axon-service/Dockerfile -t axon-service:local .
FROM python:3.12-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1

RUN apt-get update \
  && apt-get install -y --no-install-recommends build-essential \
  && rm -rf /var/lib/apt/lists/*

COPY backend/shared /app/backend/shared
COPY backend/axon-service /app/backend/axon-service

RUN pip install --no-cache-dir --upgrade pip \
  && pip install --no-cache-dir -e /app/backend/shared \
  && pip install --no-cache-dir -e /app/backend/axon-service

EXPOSE 8100
CMD ["uvicorn", "axon_service.main:app", "--host", "0.0.0.0", "--port", "8100"]
