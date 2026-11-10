"""Embedding client — Ollama native or OpenAI-compatible /v1/embeddings."""

from __future__ import annotations

from typing import Any

import httpx

from app.core.model_settings import load_model_settings


class EmbeddingError(RuntimeError):
    """Raised when the embedding endpoint fails."""


async def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed a batch of texts using the configured embedding provider."""
    if not texts:
        return []
    cfg = load_model_settings()["embedding"]
    provider = (cfg.get("provider") or "ollama").lower()
    if provider == "ollama":
        return await _embed_ollama(texts, cfg)
    return await _embed_openai_compatible(texts, cfg)


async def embed_query(text: str) -> list[float]:
    vectors = await embed_texts([text])
    return vectors[0]


def embed_texts_sync(texts: list[str]) -> list[list[float]]:
    """Sync wrapper for MCP tool threads / CLI ingest helpers."""
    import asyncio

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(embed_texts(texts))

    # Already inside an event loop — run in a worker thread.
    from concurrent.futures import ThreadPoolExecutor

    with ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(lambda: asyncio.run(embed_texts(texts))).result()


def embed_query_sync(text: str) -> list[float]:
    return embed_texts_sync([text])[0]


async def _embed_ollama(texts: list[str], cfg: dict[str, Any]) -> list[list[float]]:
    base = str(cfg.get("base_url") or "http://127.0.0.1:11434").rstrip("/")
    model = cfg.get("model") or "qwen3-embedding"
    out: list[list[float]] = []
    async with httpx.AsyncClient(timeout=120.0) as client:
        for text in texts:
            # Prefer OpenAI-compatible route when available; fall back to native.
            try:
                resp = await client.post(
                    f"{base}/v1/embeddings",
                    headers={"Authorization": f"Bearer {cfg.get('api_key') or 'ollama'}"},
                    json={"model": model, "input": text},
                )
                if resp.status_code < 400:
                    data = resp.json()
                    out.append(data["data"][0]["embedding"])
                    continue
            except httpx.HTTPError:
                pass

            resp = await client.post(
                f"{base}/api/embeddings",
                json={"model": model, "prompt": text},
            )
            try:
                resp.raise_for_status()
            except httpx.HTTPError as exc:
                raise EmbeddingError(f"Ollama embedding failed: {exc}") from exc
            payload = resp.json()
            vec = payload.get("embedding")
            if not isinstance(vec, list):
                raise EmbeddingError(f"Unexpected Ollama embedding payload: {payload!r}")
            out.append(vec)
    return out


async def _embed_openai_compatible(texts: list[str], cfg: dict[str, Any]) -> list[list[float]]:
    """OpenAI-compatible embeddings (TokenHub / OpenAI / DashScope, etc.).

    Important: do **not** send ``dimensions`` — Tencent TokenHub
    ``kinfra-*-embedding`` returns HTTP 400 if that field is present.
    """
    base = str(cfg.get("base_url") or "https://api.openai.com/v1").rstrip("/")
    if not base.endswith("/v1"):
        base = f"{base}/v1"
    model = cfg.get("model") or "text-embedding-3-small"
    api_key = cfg.get("api_key") or ""
    if not api_key:
        raise EmbeddingError(
            "Embedding api_key is empty. Set TOKENHUB_API_KEY in backend/.env "
            "(or paste it in Settings → Embedding)."
        )
    headers = {"Authorization": f"Bearer {api_key}"}
    # TokenHub recommends batches ≤ 128; keep modest for policy ingest.
    batch_size = 32
    out: list[list[float]] = []
    async with httpx.AsyncClient(timeout=120.0) as client:
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            resp = await client.post(
                f"{base}/embeddings",
                headers=headers,
                json={"model": model, "input": batch, "encoding_format": "float"},
            )
            try:
                resp.raise_for_status()
            except httpx.HTTPError as exc:
                detail = ""
                try:
                    detail = resp.text[:400]
                except Exception:  # noqa: BLE001
                    detail = ""
                raise EmbeddingError(
                    f"OpenAI-compatible embedding failed: {exc} {detail}"
                ) from exc
            data = resp.json()
            items = sorted(data.get("data", []), key=lambda x: x.get("index", 0))
            out.extend(item["embedding"] for item in items)
    return out
