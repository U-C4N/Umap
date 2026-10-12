"""Bounded HTTP, provider locks and content-addressed provenance storage."""
from __future__ import annotations

import hashlib
import json
import os
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import urlparse

import httpx
from filelock import FileLock, Timeout
from platformdirs import user_cache_path

from ..errors import UmapError

USER_AGENT = "umap-art/0.1 (+https://github.com/U-C4N/Umap)"


def cache_root(path: Path | None) -> Path:
    root = Path(path or os.environ.get("UMAP_CACHE_DIR") or user_cache_path("umap-art"))
    root.mkdir(parents=True, exist_ok=True)
    return root


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def atomic_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        temporary.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True), encoding="utf-8")
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def validate_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in {"https", "http"} or not parsed.netloc or parsed.username:
        raise UmapError("invalid_source_url", "Provider URLs must be HTTP(S) URLs without credentials")
    return url


class Budget:
    def __init__(self, seconds: float = 180, max_bytes: int = 150 * 1024**2):
        self.deadline = time.monotonic() + seconds
        self.max_bytes = max_bytes
        self.bytes_read = 0

    def remaining(self) -> float:
        remaining = self.deadline - time.monotonic()
        if remaining <= 0:
            raise UmapError("source_timeout", "The data acquisition time budget was exceeded")
        return remaining

    def consume(self, count: int) -> None:
        self.bytes_read += count
        if self.bytes_read > self.max_bytes:
            raise UmapError("source_too_large", "The data acquisition byte budget was exceeded")
        self.remaining()


@contextmanager
def provider_lock(root: Path, provider: str, budget: Budget):
    lock_dir = root / "locks"
    lock_dir.mkdir(parents=True, exist_ok=True)
    try:
        with FileLock(lock_dir / f"{provider}.lock", timeout=budget.remaining()):
            budget.remaining()
            yield
    except Timeout as exc:
        raise UmapError("source_timeout", f"Timed out waiting for {provider}") from exc


def store_raw(root: Path, data: bytes, suffix: str) -> dict:
    digest = hashlib.sha256(data).hexdigest()
    path = root / "raw" / f"{digest}{suffix}"
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
        try:
            temporary.write_bytes(data)
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)
    return {"path": str(path.resolve()), "sha256": digest, "size_bytes": len(data)}


def request_bytes(client: httpx.Client, method: str, url: str, budget: Budget,
                  *, max_bytes: int | None = None, retries: int = 2, **kwargs) -> tuple[bytes, dict]:
    """Count decompressed response bytes and bound retry sleeps by a common deadline."""
    validate_url(url)
    last_error = None
    for attempt in range(retries + 1):
        try:
            timeout = httpx.Timeout(min(30, budget.remaining()), connect=min(10, budget.remaining()))
            with client.stream(method, url, timeout=timeout, **kwargs) as response:
                if response.status_code in {429, 502, 503, 504} and attempt < retries:
                    try:
                        delay = max(1.0, float(response.headers.get("retry-after", 2**attempt)))
                    except ValueError:
                        try:
                            retry_at = parsedate_to_datetime(response.headers["retry-after"])
                            delay = max(1.0, retry_at.timestamp() - time.time())
                        except (TypeError, ValueError, KeyError):
                            delay = float(2**attempt)
                    if delay >= budget.remaining():
                        raise UmapError("source_timeout", "Provider retry exceeds remaining time budget")
                    time.sleep(delay)
                    continue
                if response.status_code >= 400:
                    raise UmapError("source_unavailable", f"Provider returned HTTP {response.status_code}",
                                    {"status": response.status_code, "url": url})
                chunks = []
                received = 0
                for chunk in response.iter_bytes():
                    budget.consume(len(chunk))
                    received += len(chunk)
                    if max_bytes is not None and received > max_bytes:
                        raise UmapError("source_too_large", "Provider response exceeds its size limit")
                    chunks.append(chunk)
                return b"".join(chunks), {"status": response.status_code, **dict(response.headers)}
        except httpx.HTTPError as exc:
            last_error = exc
            if attempt < retries:
                delay = min(float(2**attempt), budget.remaining())
                time.sleep(delay)
    raise UmapError("source_unavailable", "Could not read the online provider", {"url": url}) from last_error


def new_client() -> httpx.Client:
    return httpx.Client(headers={"User-Agent": USER_AGENT, "Accept-Encoding": "identity"},
                        follow_redirects=True)
