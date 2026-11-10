"""Weaviate helpers for ShelfMate policy chunks (bring-your-own vectors)."""

from __future__ import annotations

import logging
from typing import Any
from urllib.parse import urlparse

from app.core.model_settings import load_model_settings

logger = logging.getLogger(__name__)

COLLECTION = "ShelfMatePolicyChunk"


def _cfg() -> dict[str, Any]:
    return load_model_settings()["vector_store"]


def _parse_url(url: str) -> tuple[str, int, bool]:
    parsed = urlparse(url if "://" in url else f"http://{url}")
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or (443 if parsed.scheme == "https" else 8080)
    secure = parsed.scheme == "https"
    return host, port, secure


def get_client():
    """Open a short-lived Weaviate client."""
    import weaviate
    from weaviate.classes.init import Auth

    cfg = _cfg()
    url = str(cfg.get("url") or "http://127.0.0.1:8080").rstrip("/")
    api_key = cfg.get("api_key") or "shelfmate-dev-key"
    host, port, secure = _parse_url(url)
    # Compose network talks to weaviate:50051; host-mapped demos use 8088→50058.
    if host in {"weaviate", "shelfmate-weaviate"}:
        grpc_port = 50051
    elif port == 8088 or (
        port in {8080, 8088} and host in {"127.0.0.1", "localhost"}
    ):
        grpc_port = 50058 if port == 8088 else 50051
    else:
        grpc_port = 50051
    return weaviate.connect_to_custom(
        http_host=host,
        http_port=port,
        http_secure=secure,
        grpc_host=host,
        grpc_port=grpc_port,
        grpc_secure=False,
        auth_credentials=Auth.api_key(api_key),
        skip_init_checks=True,
    )


def health() -> dict[str, Any]:
    cfg = _cfg()
    try:
        client = get_client()
        try:
            ready = client.is_ready()
            name = cfg.get("collection") or COLLECTION
            exists = client.collections.exists(name)
            count = 0
            if exists:
                count = (
                    client.collections.get(name).aggregate.over_all().total_count or 0
                )
            return {
                "ok": bool(ready),
                "url": cfg.get("url"),
                "collection": name,
                "collection_exists": exists,
                "object_count": count,
            }
        finally:
            client.close()
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "url": cfg.get("url"),
            "error": str(exc),
            "collection": cfg.get("collection") or COLLECTION,
            "collection_exists": False,
            "object_count": 0,
        }


def replace_all_chunks(chunks: list[dict[str, Any]], vectors: list[list[float]]) -> int:
    """Delete collection contents and insert new chunk vectors."""
    from weaviate.classes.config import Configure, DataType, Property

    if len(chunks) != len(vectors):
        raise ValueError("chunks/vectors length mismatch")

    cfg = _cfg()
    name = cfg.get("collection") or COLLECTION
    dims = len(vectors[0]) if vectors else 1024
    client = get_client()
    try:
        if client.collections.exists(name):
            client.collections.delete(name)
        client.collections.create(
            name=name,
            vectorizer_config=Configure.Vectorizer.none(),
            properties=[
                Property(name="chunk_id", data_type=DataType.TEXT),
                Property(name="doc_id", data_type=DataType.TEXT),
                Property(name="title", data_type=DataType.TEXT),
                Property(name="chunk_index", data_type=DataType.INT),
                Property(name="text", data_type=DataType.TEXT),
            ],
        )
        coll = client.collections.get(name)
        with coll.batch.dynamic() as batch:
            for chunk, vector in zip(chunks, vectors):
                batch.add_object(
                    properties={
                        "chunk_id": chunk["chunk_id"],
                        "doc_id": chunk["doc_id"],
                        "title": chunk["title"],
                        "chunk_index": int(chunk["chunk_index"]),
                        "text": chunk["text"],
                    },
                    vector=vector,
                )
        logger.info("Ingested %s chunks into %s (dims=%s)", len(chunks), name, dims)
        return len(chunks)
    finally:
        client.close()


def near_vector_search(vector: list[float], *, limit: int = 5) -> list[dict[str, Any]]:
    """Return chunk hits with similarity in [0, 1]."""
    from weaviate.classes.query import MetadataQuery

    cfg = _cfg()
    name = cfg.get("collection") or COLLECTION
    client = get_client()
    try:
        if not client.collections.exists(name):
            return []
        coll = client.collections.get(name)
        result = coll.query.near_vector(
            near_vector=vector,
            limit=limit,
            return_metadata=MetadataQuery(distance=True),
        )
        hits: list[dict[str, Any]] = []
        for obj in result.objects:
            distance = obj.metadata.distance if obj.metadata else None
            similarity = 1.0 - float(distance) if distance is not None else 0.0
            similarity = max(0.0, min(1.0, similarity))
            props = obj.properties or {}
            hits.append(
                {
                    "chunk_id": props.get("chunk_id"),
                    "doc_id": props.get("doc_id"),
                    "title": props.get("title"),
                    "chunk_index": props.get("chunk_index"),
                    "text": props.get("text"),
                    "distance": distance,
                    "score": round(similarity, 4),
                    "similarity": round(similarity, 4),
                }
            )
        return hits
    finally:
        client.close()
