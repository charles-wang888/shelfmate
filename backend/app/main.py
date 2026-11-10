"""FastAPI entrypoint for ShelfMate.

Development: API on :8000; Vite frontend proxies /api.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.auth_routes import router as auth_router
from app.api.chat_routes import router as chat_router
from app.api.escalation_routes import router as escalation_router
from app.api.eval_routes import router as eval_router
from app.api.knowledge_routes import router as knowledge_router
from app.api.settings_routes import router as settings_router
from app.core.auth import decode_token, extract_bearer
from app.core.config import settings
from app.core.model_settings import load_model_settings
from app.core.paths import ensure_data_dirs


@asynccontextmanager
async def lifespan(_app: FastAPI):
    import asyncio
    import os

    import httpx

    ensure_data_dirs()
    load_model_settings()

    # Docker: wait briefly for Weaviate before optional auto-reindex.
    if os.getenv("SHELFMATE_DOCKER") == "1":
        weaviate_url = os.getenv("WEAVIATE_URL", "http://weaviate:8080").rstrip("/")
        for _ in range(30):
            try:
                async with httpx.AsyncClient(timeout=2.0) as client:
                    resp = await client.get(f"{weaviate_url}/v1/.well-known/ready")
                    if resp.status_code < 400:
                        break
            except Exception:  # noqa: BLE001
                pass
            await asyncio.sleep(2)

    if os.getenv("SHELFMATE_AUTO_REINDEX", "0") == "1":
        try:
            from app.rag import weaviate_store
            from app.rag.ingest import reindex_policies

            health = weaviate_store.health()
            if health.get("ok") and int(health.get("object_count") or 0) == 0:
                await reindex_policies()
        except Exception:  # noqa: BLE001
            # Startup must not crash if Ollama models are still pulling.
            pass
    yield


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="NovaMart internal AI assistant — docs, order tools, Ops escalation",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix=settings.api_prefix)
app.include_router(chat_router, prefix=settings.api_prefix)
app.include_router(escalation_router, prefix=settings.api_prefix)
app.include_router(eval_router, prefix=settings.api_prefix)
app.include_router(settings_router, prefix=settings.api_prefix)
app.include_router(knowledge_router, prefix=settings.api_prefix)

_PUBLIC_PATHS = {
    f"{settings.api_prefix}/auth/login",
    f"{settings.api_prefix}/auth/logout",
    f"{settings.api_prefix}/auth/me",
    f"{settings.api_prefix}/health",
}


@app.middleware("http")
async def auth_gate(request: Request, call_next):
    """Reject unauthenticated access to protected API routes."""
    path = request.url.path
    if request.method == "OPTIONS":
        return await call_next(request)
    if not path.startswith(settings.api_prefix):
        return await call_next(request)
    if path in _PUBLIC_PATHS:
        return await call_next(request)

    token = extract_bearer(request.headers.get("authorization"))
    if not token:
        return JSONResponse(status_code=401, content={"detail": "Not authenticated"})
    try:
        payload = decode_token(token)
    except Exception:  # noqa: BLE001
        return JSONResponse(
            status_code=401, content={"detail": "Invalid or expired token"}
        )
    request.state.user = payload
    return await call_next(request)
