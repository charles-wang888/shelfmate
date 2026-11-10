#!/bin/sh
set -e

echo "ShelfMate backend starting..."
echo "  WEAVIATE_URL=${WEAVIATE_URL:-http://weaviate:8080}"
echo "  OLLAMA_BASE_URL=${OLLAMA_BASE_URL:-http://ollama:11434}"

# Optional: wait for Weaviate HTTP readiness (best-effort).
if [ "${WAIT_FOR_WEAVIATE:-1}" = "1" ]; then
  i=0
  until curl -fsS "${WEAVIATE_URL:-http://weaviate:8080}/v1/.well-known/ready" >/dev/null 2>&1; do
    i=$((i + 1))
    if [ "$i" -ge 60 ]; then
      echo "Weaviate not ready after 60s — continuing anyway."
      break
    fi
    echo "Waiting for Weaviate..."
    sleep 2
  done
fi

exec uvicorn app.main:app --host 0.0.0.0 --port 8000
