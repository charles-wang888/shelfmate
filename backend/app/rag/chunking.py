"""Split NovaMart policy markdown into overlapping text chunks."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any


def chunk_markdown(
    text: str,
    *,
    doc_id: str,
    title: str,
    max_chars: int = 700,
    overlap: int = 120,
) -> list[dict[str, Any]]:
    """Chunk by paragraphs, then hard-split long blocks with overlap."""
    parts = re.split(r"\n\s*\n", text.strip())
    blocks: list[str] = []
    buf = ""
    for part in parts:
        piece = part.strip()
        if not piece:
            continue
        if not buf:
            buf = piece
        elif len(buf) + 2 + len(piece) <= max_chars:
            buf = f"{buf}\n\n{piece}"
        else:
            blocks.append(buf)
            buf = piece
    if buf:
        blocks.append(buf)

    chunks: list[dict[str, Any]] = []
    idx = 0
    for block in blocks:
        if len(block) <= max_chars:
            chunks.append(_make_chunk(doc_id, title, idx, block))
            idx += 1
            continue
        start = 0
        while start < len(block):
            end = min(len(block), start + max_chars)
            piece = block[start:end].strip()
            if piece:
                chunks.append(_make_chunk(doc_id, title, idx, piece))
                idx += 1
            if end >= len(block):
                break
            start = max(0, end - overlap)
    return chunks


def _make_chunk(doc_id: str, title: str, index: int, text: str) -> dict[str, Any]:
    return {
        "chunk_id": f"{doc_id}::{index}",
        "doc_id": doc_id,
        "title": title,
        "chunk_index": index,
        "text": text,
    }


def chunk_policy_dir(policies_dir: Path) -> list[dict[str, Any]]:
    """Load every *.md policy and return flattened chunks."""
    all_chunks: list[dict[str, Any]] = []
    for path in sorted(policies_dir.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        title = path.stem.replace("-", " ")
        all_chunks.extend(chunk_markdown(text, doc_id=path.stem, title=title))
    return all_chunks
