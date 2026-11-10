# Build from repository root:
#   docker build -f backend/Dockerfile .
FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    SHELFMATE_DOCKER=1 \
    POLICIES_DIR=/app/docs/policies \
    STORAGE_DIR=/app/storage

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
# China-friendly PyPI mirror (Tsinghua); falls back cleanly on other networks.
RUN pip install -i https://pypi.tuna.tsinghua.edu.cn/simple \
    --trusted-host pypi.tuna.tsinghua.edu.cn \
    -r requirements.txt

COPY backend/app ./app
COPY backend/scripts ./scripts
COPY docs/policies ./docs/policies

RUN mkdir -p /app/storage/escalations

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
