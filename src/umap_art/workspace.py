"""Persistent local map revisions, bounded jobs, and artifact access.

All file paths accepted by this layer stay below the workspace. The Python render
API remains independent of this storage layer.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import sqlite3
import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path
from typing import Any

from filelock import FileLock, Timeout

from .errors import UmapError
from .models import MapSpec, RenderResult, SourceSpec
from .storage import file_hash

_TERMINAL = {"succeeded", "failed", "cancelled", "interrupted"}
_PROVIDERS = ("photon_url", "overpass_url", "overture_catalog_url")
_EDITABLE = {"title", "subtitle", "language", "page", "style", "views"}


def _json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _id(prefix: str) -> str:
    return prefix + "_" + uuid.uuid4().hex


def _merge(original: dict, changes: dict) -> dict:
    result = json.loads(_json(original))
    for key, value in changes.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _merge(result[key], value)
        else:
            result[key] = value
    return result


def _diff(before: Any, after: Any, path: str = "") -> list[dict]:
    if isinstance(before, dict) and isinstance(after, dict):
        result = []
        for key in sorted(before.keys() | after.keys()):
            result.extend(_diff(before.get(key), after.get(key), f"{path}/{key}"))
        return result
    return [] if before == after else [{"path": path, "before": before, "after": after}]


class Workspace:
    """One owner, one render worker, and at most four waiting jobs.

    ``provider_urls`` is trusted startup configuration, never tool input.
    ``worker_command`` and ``job_timeout`` allow bounded integration tests.
    """

    def __init__(self, root: Path | str, *, provider_urls: dict[str, str] | None = None,
                 job_timeout: float = 300, worker_command: list[str] | None = None,
                 start_worker: bool = True):
        self.root = Path(root).expanduser().resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self._guard = threading.RLock()
        self._wake = threading.Event()
        self._closed = threading.Event()
        self._process: subprocess.Popen | None = None
        self._active_job: str | None = None
        self._job_timeout = min(max(float(job_timeout), 0.1), 300)
        self._command = worker_command or [sys.executable, "-m", "umap_art.worker"]
        defaults = SourceSpec().model_dump()
        self._providers = {name: defaults[name] for name in _PROVIDERS}
        if provider_urls:
            if set(provider_urls) - set(_PROVIDERS):
                raise UmapError("INVALID_PROVIDER", "Unknown provider configuration")
            self._providers.update(provider_urls)
        self._lock = FileLock(str(self._safe(self.root / ".workspace.lock")))
        try:
            self._lock.acquire(timeout=0)
        except Timeout as exc:
            raise UmapError("WORKSPACE_BUSY", "This workspace already has an active owner") from exc
        self._db = sqlite3.connect(self._safe(self.root / "workspace.sqlite3"),
                                   check_same_thread=False)
        self._db.row_factory = sqlite3.Row
        self._db.executescript("""
            PRAGMA journal_mode=WAL;
            PRAGMA foreign_keys=ON;
            CREATE TABLE IF NOT EXISTS maps(id TEXT PRIMARY KEY, revision INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS revisions(
                map_id TEXT, revision INTEGER, spec TEXT NOT NULL, snapshot TEXT,
                dataset_id TEXT, created REAL NOT NULL, PRIMARY KEY(map_id,revision));
            CREATE TABLE IF NOT EXISTS jobs(
                id TEXT PRIMARY KEY, map_id TEXT NOT NULL, revision INTEGER NOT NULL,
                kind TEXT NOT NULL, state TEXT NOT NULL, spec TEXT NOT NULL,
                created REAL NOT NULL, started REAL, finished REAL, error TEXT,
                result TEXT, base_revision INTEGER);
            CREATE TABLE IF NOT EXISTS requests(
                id TEXT PRIMARY KEY, fingerprint TEXT NOT NULL, response TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS artifacts(
                id TEXT PRIMARY KEY, job_id TEXT NOT NULL, metadata TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS candidates(id TEXT PRIMARY KEY, value TEXT NOT NULL);
        """)
        self._db.execute(
            "UPDATE jobs SET state='interrupted',finished=?,error=? "
            "WHERE state IN ('queued','running','cancelling')",
            (time.time(), _json({"code": "INTERRUPTED", "message": "Workspace restarted"})))
        self._db.commit()
        self._thread = None
        if start_worker:
            self._thread = threading.Thread(target=self._run, name="umap-job-owner", daemon=True)
            self._thread.start()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def _safe(self, path: Path | str) -> Path:
        path = Path(path)
        if not path.is_absolute():
            path = self.root / path
        resolved = path.resolve()
        if not resolved.is_relative_to(self.root):
            raise UmapError("PATH_OUTSIDE_WORKSPACE", "Path must remain inside the workspace")
        return resolved

    def _ensure_open(self):
        if self._closed.is_set():
            raise UmapError("WORKSPACE_CLOSED", "Workspace is closed")

    def _spec(self, value: dict) -> MapSpec:
        raw = json.loads(_json(value))
        source = raw.setdefault("source", {})
        if not isinstance(source, dict):
            return MapSpec.model_validate(raw)
        for field, url in self._providers.items():
            if field in source and source[field] not in (url, getattr(SourceSpec(), field)):
                raise UmapError("PROVIDER_NOT_ALLOWED", "Provider URLs require startup configuration")
            source[field] = url
        if source.get("snapshot"):
            source["snapshot"] = str(self._safe(source["snapshot"]))
        spec = MapSpec.model_validate(raw)
        from .styles import validate_style
        validate_style(spec.style)
        return spec

    def _existing_request(self, request_id: str | None, payload: dict) -> dict | None:
        self._ensure_open()
        if request_id is None:
            return None
        if not isinstance(request_id, str) or not 1 <= len(request_id) <= 200:
            raise UmapError("INVALID_REQUEST_ID", "request_id must contain 1–200 characters")
        row = self._db.execute("SELECT * FROM requests WHERE id=?", (request_id,)).fetchone()
        if row:
            if row["fingerprint"] != hashlib.sha256(_json(payload).encode()).hexdigest():
                raise UmapError("REQUEST_ID_CONFLICT", "request_id was used with different arguments")
            return json.loads(row["response"])
        return None

    def _remember(self, request_id: str | None, payload: dict, response: dict):
        if request_id:
            self._db.execute("INSERT INTO requests VALUES(?,?,?)",
                             (request_id, hashlib.sha256(_json(payload).encode()).hexdigest(),
                              _json(response)))

    def _revision(self, map_id: str, revision: int | None = None) -> sqlite3.Row:
        current = self._db.execute("SELECT revision FROM maps WHERE id=?", (map_id,)).fetchone()
        if current is None:
            raise UmapError("MAP_NOT_FOUND", "Unknown map_id")
        revision = current["revision"] if revision is None else revision
        row = self._db.execute("SELECT * FROM revisions WHERE map_id=? AND revision=?",
                               (map_id, revision)).fetchone()
        if row is None:
            raise UmapError("REVISION_NOT_FOUND", "Unknown map revision")
        return row

    def _resolved_spec(self, row: sqlite3.Row) -> dict:
        spec = json.loads(row["spec"])
        if row["snapshot"]:
            spec["source"]["snapshot"] = str(self._safe(row["snapshot"]))
            spec["source"]["offline"] = True
        return spec

    def _queue(self, map_id: str, revision: int, kind: str, spec: dict,
               base_revision: int | None = None) -> str:
        waiting = self._db.execute("SELECT COUNT(*) FROM jobs WHERE state='queued'").fetchone()[0]
        if waiting >= 4:
            raise UmapError("QUEUE_FULL", "Four jobs are already waiting")
        job_id = _id("job")
        self._db.execute(
            "INSERT INTO jobs(id,map_id,revision,kind,state,spec,created,base_revision) "
            "VALUES(?,?,?,?,'queued',?,?,?)",
            (job_id, map_id, revision, kind, _json(spec), time.time(), base_revision))
        self._wake.set()
        return job_id

    def create_map(self, spec: dict, request_id: str | None = None) -> dict:
        payload = {"method": "create_map", "spec": spec}
        with self._guard, self._db:
            prior = self._existing_request(request_id, payload)
            if prior:
                return prior
            checked = self._spec(spec).model_dump(mode="json")
            map_id = _id("map")
            self._db.execute("INSERT INTO maps VALUES(?,1)", (map_id,))
            self._db.execute("INSERT INTO revisions VALUES(?,1,?,?,NULL,?)",
                             (map_id, _json(checked), checked["source"]["snapshot"], time.time()))
            job_id = self._queue(map_id, 1, "create", checked)
            result = {"map_id": map_id, "revision": 1, "job_id": job_id}
            self._remember(request_id, payload, result)
            return result

    def inspect_map(self, map_id: str) -> dict:
        with self._guard:
            self._ensure_open()
            row = self._revision(map_id)
            jobs = self._db.execute("SELECT id,state,revision FROM jobs WHERE map_id=? ORDER BY created",
                                    (map_id,)).fetchall()
            complete = self._db.execute(
                "SELECT id,result FROM jobs WHERE map_id=? AND revision=? AND state='succeeded' "
                "ORDER BY finished DESC LIMIT 1", (map_id, row["revision"])).fetchone()
            details = json.loads(complete["result"]) if complete else {}
            artifacts = [json.loads(a[0]) for a in self._db.execute(
                "SELECT metadata FROM artifacts WHERE job_id=?", (complete["id"],))] if complete else []
            return {"map_id": map_id, "revision": row["revision"],
                    "dataset_id": row["dataset_id"], "spec": self._resolved_spec(row),
                    "jobs": [dict(job) for job in jobs],
                    "diagnostics": details.get("diagnostics", []), "artifacts": artifacts}

    def edit_map(self, map_id: str, base_revision: int, changes: dict | None = None,
                 restore_revision: int | None = None, request_id: str | None = None) -> dict:
        payload = {"method": "edit_map", "map_id": map_id, "base_revision": base_revision,
                   "changes": changes, "restore_revision": restore_revision}
        with self._guard, self._db:
            prior = self._existing_request(request_id, payload)
            if prior:
                return prior
            current = self._revision(map_id)
            if current["revision"] != base_revision:
                raise UmapError("REVISION_CONFLICT", "Map changed; inspect the current revision")
            if (changes is None) == (restore_revision is None):
                raise UmapError("INVALID_EDIT", "Provide changes or restore_revision, exclusively")
            if not current["snapshot"]:
                raise UmapError("DATA_NOT_READY", "Wait for the map's initial data acquisition")
            before = self._resolved_spec(current)
            if restore_revision is not None:
                restored = self._revision(map_id, restore_revision)
                if not restored["snapshot"]:
                    raise UmapError("DATA_NOT_READY", "That revision has no pinned data")
                raw = self._resolved_spec(restored)
                dataset_id = restored["dataset_id"]
            else:
                if not changes or set(changes) - _EDITABLE:
                    raise UmapError("INVALID_EDIT", "Only title, subtitle, language, page, style, views are editable")
                raw = _merge(before, changes)
                dataset_id = current["dataset_id"]
            checked = self._spec(raw).model_dump(mode="json")
            # A paper change in center+scale mode can expand acquisition coverage. Fail
            # clearly instead of pretending the old snapshot covers the new extent.
            if checked["page"] != before["page"]:
                from .geometry import compute_extent
                from .service import load_snapshot
                dataset, _ = load_snapshot(Path(checked["source"]["snapshot"]))
                area = compute_extent(MapSpec.model_validate(checked))
                bbox = area.bbox
                if not (dataset.bbox[0] - 1e-7 <= bbox[0] and dataset.bbox[1] - 1e-7 <= bbox[1]
                        and dataset.bbox[2] + 1e-7 >= bbox[2] and dataset.bbox[3] + 1e-7 >= bbox[3]):
                    raise UmapError("SNAPSHOT_COVERAGE", "Page change exceeds saved data; create a map for the new page")
            revision = base_revision + 1
            self._db.execute("INSERT INTO revisions VALUES(?,?,?,?,?,?)",
                             (map_id, revision, _json(checked), checked["source"]["snapshot"], dataset_id, time.time()))
            self._db.execute("UPDATE maps SET revision=? WHERE id=?", (revision, map_id))
            preview_spec = self._preview(checked)
            job_id = self._queue(map_id, revision, "preview", preview_spec)
            result = {"map_id": map_id, "revision": revision, "job_id": job_id,
                      "changes": _diff(before, checked)}
            self._remember(request_id, payload, result)
            return result

    @staticmethod
    def _preview(spec: dict) -> dict:
        return _merge(spec, {"formats": ["png"], "page": {"dpi": 72}, "bundle": False})

    def refresh_map_data(self, map_id: str, base_revision: int,
                         request_id: str | None = None) -> dict:
        payload = {"method": "refresh_map_data", "map_id": map_id, "base_revision": base_revision}
        with self._guard, self._db:
            prior = self._existing_request(request_id, payload)
            if prior:
                return prior
            row = self._revision(map_id)
            if row["revision"] != base_revision:
                raise UmapError("REVISION_CONFLICT", "Map changed; inspect the current revision")
            spec = self._resolved_spec(row)
            spec["source"].update(snapshot=None, offline=False)
            spec = self._spec(spec).model_dump(mode="json")
            job_id = self._queue(map_id, base_revision + 1, "refresh", spec, base_revision)
            result = {"map_id": map_id, "base_revision": base_revision, "job_id": job_id}
            self._remember(request_id, payload, result)
            return result

    def render_map(self, map_id: str, revision: int | None = None,
                   formats: list[str] | None = None, preview: bool = False,
                   request_id: str | None = None) -> dict:
        payload = {"method": "render_map", "map_id": map_id, "revision": revision,
                   "formats": formats, "preview": preview}
        with self._guard, self._db:
            prior = self._existing_request(request_id, payload)
            if prior:
                return prior
            row = self._revision(map_id, revision)
            if not row["snapshot"]:
                raise UmapError("DATA_NOT_READY", "Wait for the map's initial data acquisition")
            spec = self._resolved_spec(row)
            if formats is not None:
                spec["formats"] = formats
            spec = self._spec(spec).model_dump(mode="json")
            if preview:
                spec = self._preview(spec)
            job_id = self._queue(map_id, row["revision"], "preview" if preview else "render", spec)
            result = {"map_id": map_id, "revision": row["revision"], "job_id": job_id}
            self._remember(request_id, payload, result)
            return result

    def get_job(self, job_id: str) -> dict:
        with self._guard:
            self._ensure_open()
            row = self._db.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
            if row is None:
                raise UmapError("JOB_NOT_FOUND", "Unknown job_id")
            result = {key: row[key] for key in ("id", "map_id", "revision", "kind", "state", "created", "started", "finished")}
            result["job_id"] = result.pop("id")
            result["error"] = json.loads(row["error"]) if row["error"] else None
            result["result"] = json.loads(row["result"]) if row["result"] else None
            result["artifacts"] = [json.loads(a[0]) for a in self._db.execute(
                "SELECT metadata FROM artifacts WHERE job_id=?", (job_id,))]
            return result

    def cancel_job(self, job_id: str) -> dict:
        with self._guard, self._db:
            status = self.get_job(job_id)
            if status["state"] == "queued":
                self._db.execute("UPDATE jobs SET state='cancelled',finished=? WHERE id=?", (time.time(), job_id))
            elif status["state"] == "running":
                self._db.execute("UPDATE jobs SET state='cancelling' WHERE id=?", (job_id,))
            self._wake.set()
        return self.get_job(job_id)

    def get_artifact(self, artifact_id: str, include_preview: bool = False) -> dict:
        with self._guard:
            self._ensure_open()
            row = self._db.execute("SELECT metadata FROM artifacts WHERE id=?", (artifact_id,)).fetchone()
            if row is None:
                raise UmapError("ARTIFACT_NOT_FOUND", "Unknown artifact_id")
            result = json.loads(row[0])
            path = self._safe(result["path"])
            if not path.is_file():
                raise UmapError("ARTIFACT_MISSING", "Saved artifact no longer exists")
            result["chunk_size_bytes"] = 1024**2
            result["chunk_uri_template"] = f"umap://artifact-chunks/{artifact_id}/{{offset}}"
            if include_preview and result["mime_type"] == "image/png" and path.stat().st_size <= 1024**2:
                result["preview_base64"] = base64.b64encode(path.read_bytes()).decode("ascii")
            return result

    def read_artifact(self, artifact_id: str) -> bytes:
        metadata = self.get_artifact(artifact_id)
        path = self._safe(metadata["path"])
        if path.stat().st_size > 16 * 1024**2:
            raise UmapError("ARTIFACT_TOO_LARGE", "Use the chunk resource for files above 16 MiB",
                            {"chunk_uri_template": metadata["chunk_uri_template"], "chunk_size_bytes": 1024**2})
        return path.read_bytes()

    def read_artifact_chunk(self, artifact_id: str, offset: int) -> bytes:
        """Read at most 1 MiB at a byte offset, allowing bounded large-file access."""
        metadata = self.get_artifact(artifact_id)
        path = self._safe(metadata["path"])
        if not isinstance(offset, int) or isinstance(offset, bool) or not 0 <= offset <= path.stat().st_size:
            raise UmapError("INVALID_OFFSET", "Chunk offset must be between zero and file size")
        with path.open("rb") as stream:
            stream.seek(offset)
            return stream.read(1024**2)

    def remember_candidates(self, values: list[dict]) -> list[dict]:
        with self._guard, self._db:
            self._ensure_open()
            result = []
            for value in values:
                candidate_id = "location_" + hashlib.sha256(_json(value).encode()).hexdigest()[:24]
                saved = {**value, "candidate_id": candidate_id}
                self._db.execute("INSERT OR REPLACE INTO candidates VALUES(?,?)", (candidate_id, _json(saved)))
                result.append(saved)
            return result

    def resolve_candidate(self, candidate_id: str) -> dict:
        with self._guard:
            row = self._db.execute("SELECT value FROM candidates WHERE id=?", (candidate_id,)).fetchone()
            if row is None:
                raise UmapError("LOCATION_NOT_FOUND", "Search for this location again")
            return json.loads(row[0])

    def _run(self):
        while not self._closed.is_set():
            with self._guard, self._db:
                row = self._db.execute("SELECT * FROM jobs WHERE state='queued' ORDER BY created LIMIT 1").fetchone()
                if row:
                    self._db.execute("UPDATE jobs SET state='running',started=? WHERE id=?", (time.time(), row["id"]))
                    self._active_job = row["id"]
            if row is None:
                self._wake.wait(0.25)
                self._wake.clear()
                continue
            try:
                self._execute(row)
            except Exception as exc:
                error = exc.to_dict() if isinstance(exc, UmapError) else {"code": "WORKER_FAILED", "message": str(exc)}
                with self._guard, self._db:
                    current = self._db.execute("SELECT state FROM jobs WHERE id=?", (row["id"],)).fetchone()[0]
                    state = "interrupted" if self._closed.is_set() else "cancelled" if current == "cancelling" else "failed"
                    self._db.execute("UPDATE jobs SET state=?,finished=?,error=? WHERE id=?",
                                     (state, time.time(), _json(error), row["id"]))
            finally:
                self._process = None
                self._active_job = None

    @staticmethod
    def _stop(process: subprocess.Popen):
        if process.stdin:
            try:
                process.stdin.close()
            except OSError:
                pass
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            process.terminate()
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()

    def _execute(self, job: sqlite3.Row):
        directory = self._safe(self.root / "jobs" / job["id"])
        directory.mkdir(parents=True, exist_ok=False)
        output = self._safe(directory / "output")
        result_file = self._safe(directory / "result.json")
        request = {"spec": json.loads(job["spec"]), "output_dir": str(output), "refresh": job["kind"] == "refresh",
                   "result_file": str(result_file)}
        if request["spec"]["source"].get("snapshot"):
            request["spec"]["source"]["snapshot"] = str(self._safe(request["spec"]["source"]["snapshot"]))
        started = time.monotonic()
        with self._safe(directory / "worker.log").open("wb") as log:
            kwargs = {"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {}
            environment = dict(os.environ)
            environment["UMAP_CACHE_DIR"] = str(self._safe(self.root / "cache"))
            process = subprocess.Popen(self._command, stdin=subprocess.PIPE, stdout=log, stderr=log,
                                       env=environment, **kwargs)
            self._process = process
            try:
                process.stdin.write((_json(request) + "\n").encode())
                process.stdin.flush()
                while process.poll() is None:
                    with self._guard:
                        state = self._db.execute("SELECT state FROM jobs WHERE id=?", (job["id"],)).fetchone()[0]
                    if self._closed.is_set() or state == "cancelling":
                        raise UmapError("CANCELLED", "Job was cancelled")
                    if time.monotonic() - started > self._job_timeout:
                        raise UmapError("JOB_TIMEOUT", "Job exceeded its time budget")
                    self._wake.wait(0.05)
                    self._wake.clear()
                if not result_file.is_file():
                    raise UmapError("WORKER_FAILED", f"Worker exited without result (exit {process.returncode})")
                message = json.loads(result_file.read_text("utf-8"))
                if "error" in message:
                    error = message["error"]
                    raise UmapError(error["code"], error["message"], error.get("details"))
                if process.returncode != 0:
                    raise UmapError("WORKER_FAILED", f"Worker exit {process.returncode}")
                result = RenderResult.model_validate(message["result"])
                self._publish(job, result, output)
            finally:
                self._stop(process)

    def _publish(self, job: sqlite3.Row, result: RenderResult, output: Path):
        # Verify every file before committing even one public artifact.
        records = []
        paths = {artifact.path: artifact.model_dump(mode="json") for artifact in result.artifacts}
        for name in ("manifest_path", "recipe_path", "snapshot_path"):
            paths.setdefault(getattr(result, name), {"mime_type": "application/json"})
        for filename, metadata in paths.items():
            path = self._safe(filename)
            if not path.is_relative_to(output) or not path.is_file():
                raise UmapError("INVALID_WORKER_RESULT", "Worker artifact is outside its output directory")
            digest = file_hash(path)
            if metadata.get("sha256") and metadata["sha256"] != digest:
                raise UmapError("INVALID_WORKER_RESULT", "Artifact hash did not match")
            artifact_id = _id("artifact")
            records.append({**metadata, "artifact_id": artifact_id, "job_id": job["id"],
                            "path": str(path), "sha256": digest, "size_bytes": path.stat().st_size,
                            "uri": f"umap://artifacts/{artifact_id}"})
        with self._guard, self._db:
            current_state = self._db.execute("SELECT state FROM jobs WHERE id=?", (job["id"],)).fetchone()[0]
            if self._closed.is_set() or current_state == "cancelling":
                raise UmapError("CANCELLED", "Job was cancelled before publication")
            if job["kind"] == "refresh":
                current = self._revision(job["map_id"])
                if current["revision"] != job["base_revision"]:
                    raise UmapError("REVISION_CONFLICT", "Map changed while data refreshed; existing revision preserved")
                spec = json.loads(job["spec"])
                spec["source"].update(snapshot=result.snapshot_path, offline=True)
                self._db.execute("INSERT INTO revisions VALUES(?,?,?,?,?,?)",
                                 (job["map_id"], job["revision"], _json(spec), result.snapshot_path,
                                  result.dataset_id, time.time()))
                self._db.execute("UPDATE maps SET revision=? WHERE id=?", (job["revision"], job["map_id"]))
            else:
                # Resolve a place exactly once. The immutable dataset pins the
                # canonical location from the successful recipe thereafter.
                if job["kind"] == "create":
                    recipe = json.loads(self._safe(result.recipe_path).read_text("utf-8"))
                    original = json.loads(job["spec"])
                    original["area"] = recipe["area"]
                    self._db.execute("UPDATE revisions SET spec=?,snapshot=? WHERE map_id=? AND revision=?",
                                     (_json(original), result.snapshot_path, job["map_id"], job["revision"]))
                self._db.execute("UPDATE revisions SET snapshot=COALESCE(snapshot,?),dataset_id=COALESCE(dataset_id,?) "
                                 "WHERE map_id=? AND revision=?",
                                 (result.snapshot_path, result.dataset_id, job["map_id"], job["revision"]))
            for record in records:
                self._db.execute("INSERT INTO artifacts VALUES(?,?,?)", (record["artifact_id"], job["id"], _json(record)))
            self._db.execute("UPDATE jobs SET state='succeeded',finished=?,result=? WHERE id=?",
                             (time.time(), _json(result.model_dump(mode="json")), job["id"]))

    def close(self):
        if self._closed.is_set():
            return
        self._closed.set()
        self._wake.set()
        if self._thread:
            self._thread.join(timeout=8)
        if self._process and self._process.poll() is None:
            self._stop(self._process)
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)
        with self._guard, self._db:
            self._db.execute("UPDATE jobs SET state='interrupted',finished=? WHERE state IN ('queued','running','cancelling')", (time.time(),))
        self._db.close()
        self._lock.release()
