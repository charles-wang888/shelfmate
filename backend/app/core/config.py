"""Application settings loaded from environment / .env."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = BACKEND_ROOT.parent

# Ensure DEEPSEEK_API_KEY / TOKENHUB_API_KEY etc. are visible via os.getenv
# (used by model_settings), not only via pydantic field binding.
load_dotenv(BACKEND_ROOT / ".env", override=False)


def _default_policies_dir() -> Path:
    env = os.getenv("POLICIES_DIR")
    if env:
        return Path(env)
    return REPO_ROOT / "docs" / "policies"


def _default_storage_dir() -> Path:
    env = os.getenv("STORAGE_DIR")
    if env:
        return Path(env)
    return BACKEND_ROOT / "storage"


class Settings(BaseSettings):
    """Runtime configuration for the ShelfMate API and agent."""

    model_config = SettingsConfigDict(
        env_file=str(BACKEND_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "ShelfMate"
    api_prefix: str = "/api"
    cors_origins: list[str] = Field(
        default_factory=lambda: ["*"]
        if os.getenv("SHELFMATE_DOCKER") == "1"
        else [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:8080",
            "http://127.0.0.1:8080",
        ]
    )

    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "qwen3:8b"

    auth_secret: str = "shelfmate-dev-secret-change-me"
    auth_token_ttl_minutes: int = 480

    # Max tool-calling rounds per user message
    max_tool_rounds: int = 4

    policies_dir: Path = Field(default_factory=_default_policies_dir)
    data_dir: Path = BACKEND_ROOT / "app" / "data"
    storage_dir: Path = Field(default_factory=_default_storage_dir)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
