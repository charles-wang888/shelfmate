"""Persisted LLM / embedding / Weaviate settings (runtime-editable from Settings UI)."""

from __future__ import annotations

import json
import os
from copy import deepcopy
from pathlib import Path
from threading import Lock
from typing import Any

from app.core.config import settings

_LOCK = Lock()

_LOCAL_DEFAULTS: dict[str, Any] = {
    # DeepSeek chat + Tencent TokenHub embedding (local demo defaults).
    "llm": {
        "provider": "deepseek",
        "model": "deepseek-chat",
        "base_url": "https://api.deepseek.com",
        "api_key": "",
        "timeout_seconds": 120,
    },
    "embedding": {
        "provider": "openai",
        "model": "kinfra-text-embedding-0.6b",
        "base_url": "https://tokenhub.tencentmaas.com/v1",
        "api_key": "",
        "dimensions": 1024,
    },
    "vector_store": {
        "url": "http://127.0.0.1:8088",
        "api_key": "shelfmate-dev-key",
        "collection": "ShelfMatePolicyChunk",
    },
}


def _apply_env_overrides(data: dict[str, Any]) -> dict[str, Any]:
    """Prefer env keys so secrets stay in backend/.env (gitignored)."""
    deepseek_key = os.getenv("DEEPSEEK_API_KEY") or os.getenv("LLM_API_KEY")
    if deepseek_key:
        data["llm"]["api_key"] = deepseek_key

    llm_base = os.getenv("LLM_BASE_URL")
    if llm_base:
        data["llm"]["base_url"] = llm_base
    llm_model = os.getenv("LLM_MODEL")
    if llm_model:
        data["llm"]["model"] = llm_model
    llm_provider = os.getenv("LLM_PROVIDER")
    if llm_provider:
        data["llm"]["provider"] = llm_provider

    emb_key = (
        os.getenv("TOKENHUB_API_KEY")
        or os.getenv("SEMANTIC_EMBEDDING_API_KEY")
        or os.getenv("EMBEDDING_API_KEY")
    )
    if emb_key:
        data["embedding"]["api_key"] = emb_key
    emb_base = os.getenv("SEMANTIC_EMBEDDING_BASE_URL") or os.getenv("EMBEDDING_BASE_URL")
    if emb_base:
        data["embedding"]["base_url"] = emb_base
    emb_model = os.getenv("SEMANTIC_EMBEDDING_MODEL") or os.getenv("EMBEDDING_MODEL")
    if emb_model:
        data["embedding"]["model"] = emb_model
    emb_dims = os.getenv("SEMANTIC_EMBEDDING_DIMENSIONS") or os.getenv("EMBEDDING_DIMENSIONS")
    if emb_dims:
        try:
            data["embedding"]["dimensions"] = int(emb_dims)
        except ValueError:
            pass
    emb_provider = os.getenv("EMBEDDING_PROVIDER")
    if emb_provider:
        data["embedding"]["provider"] = emb_provider

    weaviate = os.getenv("WEAVIATE_URL")
    if weaviate:
        data["vector_store"]["url"] = weaviate
    weaviate_key = os.getenv("WEAVIATE_API_KEY")
    if weaviate_key:
        data["vector_store"]["api_key"] = weaviate_key
    return data


def _default_settings() -> dict[str, Any]:
    """Cloud defaults locally; docker Ollama only when SHELFMATE_USE_CLOUD_MODELS!=1."""
    data = deepcopy(_LOCAL_DEFAULTS)
    if os.getenv("SHELFMATE_DOCKER") == "1":
        weaviate = os.getenv("WEAVIATE_URL", "http://weaviate:8080")
        data["vector_store"]["url"] = weaviate
        data["vector_store"]["api_key"] = os.getenv(
            "WEAVIATE_API_KEY", data["vector_store"]["api_key"]
        )
        if os.getenv("SHELFMATE_USE_CLOUD_MODELS") != "1":
            ollama = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")
            data["llm"] = {
                "provider": "ollama",
                "model": os.getenv("OLLAMA_MODEL", "qwen3:8b"),
                "base_url": ollama,
                "api_key": "",
                "timeout_seconds": 120,
            }
            data["embedding"] = {
                "provider": "ollama",
                "model": os.getenv("OLLAMA_EMBED_MODEL", "qwen3-embedding"),
                "base_url": ollama,
                "api_key": "ollama",
                "dimensions": int(os.getenv("EMBEDDING_DIMENSIONS", "4096")),
            }
    return _apply_env_overrides(data)


# Backward-compatible name used elsewhere
DEFAULT_SETTINGS = _default_settings()


def _path() -> Path:
    return settings.storage_dir / "model_settings.json"


def _deep_merge(base: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    out = deepcopy(base)
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = value
    return out


def load_model_settings() -> dict[str, Any]:
    path = _path()
    defaults = _default_settings()
    with _LOCK:
        if not path.exists():
            # Persist non-secret shape; secrets come from env overrides.
            public_defaults = deepcopy(defaults)
            public_defaults["llm"]["api_key"] = ""
            public_defaults["embedding"]["api_key"] = ""
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(public_defaults, indent=2), encoding="utf-8")
            return deepcopy(defaults)
        data = json.loads(path.read_text(encoding="utf-8"))
        merged = _deep_merge(defaults, data)
        return _apply_env_overrides(merged)


def save_model_settings(patch: dict[str, Any]) -> dict[str, Any]:
    """Merge patch into stored settings. Empty api_key means keep previous."""
    current = load_model_settings()
    cleaned = deepcopy(patch)
    for section in ("llm", "embedding", "vector_store"):
        if section in cleaned and isinstance(cleaned[section], dict):
            if cleaned[section].get("api_key") == "":
                cleaned[section].pop("api_key", None)
    merged = _deep_merge(current, cleaned)
    path = _path()
    with _LOCK:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(merged, indent=2), encoding="utf-8")
    return merged


def public_model_settings() -> dict[str, Any]:
    """Return settings with api keys masked for the UI."""
    data = load_model_settings()
    for section in ("llm", "embedding", "vector_store"):
        key = data.get(section, {}).get("api_key") or ""
        data[section]["api_key"] = ""
        data[section]["api_key_set"] = bool(key)
        data[section]["api_key_hint"] = (
            ("••••" + key[-4:]) if len(key) >= 4 else ("set" if key else "")
        )
    data["providers"] = {
        "llm": ["deepseek", "ollama", "openai", "anthropic", "google"],
        "embedding": ["openai", "ollama"],
    }
    return data
