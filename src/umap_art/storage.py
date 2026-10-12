"""Content addressing and atomic JSON storage."""

from __future__ import annotations

import hashlib
import json
import os
import uuid
from pathlib import Path
from typing import Any

from platformdirs import user_cache_path


def canonical(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def atomic_json(path: Path, value: Any):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        temporary.write_bytes(canonical(value))
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def cache_root() -> Path:
    path = Path(os.environ.get("UMAP_CACHE_DIR", str(user_cache_path("umap-art"))))
    path.mkdir(parents=True, exist_ok=True)
    return path
