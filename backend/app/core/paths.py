"""Filesystem helpers for data and storage directories."""

from __future__ import annotations

from app.core.config import settings


def ensure_data_dirs() -> None:
    """Create storage folders used by escalations and runtime state."""
    settings.storage_dir.mkdir(parents=True, exist_ok=True)
    (settings.storage_dir / "escalations").mkdir(parents=True, exist_ok=True)
