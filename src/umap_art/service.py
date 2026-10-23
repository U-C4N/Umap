"""The single map production pipeline used by Python, CLI and MCP."""

from __future__ import annotations

import importlib.metadata
import json
import os
import shutil
import threading
import time
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from filelock import FileLock

from .errors import UmapError
from .geometry import PreparedGeometry, compute_extent, prepare_geometry
from .models import (
    AreaSpec,
    Artifact,
    Dataset,
    Diagnostic,
    Feature,
    MapSpec,
    RenderResult,
    validate_spec,
)
from .storage import atomic_json, cache_root, digest, file_hash

_RENDER_LOCK = threading.RLock()


def _snapshot_id(dataset: Dataset) -> str:
    return digest(dataset.model_dump(mode="json"))


def _source_profile(spec: MapSpec) -> dict:
    return {
        k: getattr(spec.source, k)
        for k in ("overpass_url", "overture_catalog_url", "include_ocean")
    }


def _check_snapshot_sources(path: Path, data: Dataset, spec: MapSpec):
    envelope = json.loads(path.read_text(encoding="utf-8"))
    profile = envelope.get("source_profile")
    if profile is None and any(s.get("provider") == "overpass" for s in data.sources):
        profile = {"include_ocean": any(s.get("provider") == "overture" for s in data.sources)}
        for source in data.sources:
            key = {"overpass": "overpass_url", "overture": "overture_catalog_url"}.get(
                source.get("provider")
            )
            if key and source.get("endpoint"):
                profile[key] = source["endpoint"]
    if profile and any(
        getattr(spec.source, key) != value
        for key, value in profile.items()
        if key in _source_profile(spec)
    ):
        raise UmapError(
            "SNAPSHOT_SOURCES",
            "The requested providers differ from the pinned snapshot; refresh data explicitly",
        )


def load_snapshot(path: Path) -> tuple[Dataset, str]:
    try:
        envelope = json.loads(path.read_text(encoding="utf-8"))
        if envelope.get("schema_version") != "1":
            raise UmapError("SNAPSHOT_VERSION", "Unsupported snapshot schema")
        data = Dataset.model_validate(envelope["dataset"])
        identity = _snapshot_id(data)
        if envelope.get("dataset_id") != identity:
            raise UmapError("SNAPSHOT_INTEGRITY", "Snapshot content hash does not match")
        return data, identity
    except UmapError:
        raise
    except (OSError, ValueError, KeyError) as exc:
        raise UmapError(
            "SNAPSHOT_INVALID",
            "Unable to read dataset snapshot",
            {"path": str(path), "reason": str(exc)},
        ) from exc


def _get_data(spec: MapSpec, bbox, cache: Path, refresh: bool) -> tuple[Dataset, str]:
    if spec.source.snapshot and not refresh:
        data, identity = load_snapshot(Path(spec.source.snapshot))
        _check_snapshot_sources(Path(spec.source.snapshot), data, spec)
        w, s, e, n = data.bbox
        qw, qs, qe, qn = bbox
        eps = 1e-7
        if qw < w - eps or qs < s - eps or qe > e + eps or qn > n + eps:
            raise UmapError(
                "SNAPSHOT_EXTENT",
                "Snapshot does not cover the requested map; refresh data for the new extent",
            )
        return data, identity
    key = digest(
        {
            "bbox": [round(x, 9) for x in bbox],
            "overpass": spec.source.overpass_url,
            "overture": spec.source.overture_catalog_url,
            "ocean": spec.source.include_ocean,
            "normalizer": "1",
        }
    )
    index = cache / "queries" / f"{key}.json"
    index.parent.mkdir(parents=True, exist_ok=True)
    with FileLock(str(index) + ".lock", timeout=spec.limits.acquisition_seconds):
        if not refresh and index.exists():
            entry = json.loads(index.read_text(encoding="utf-8"))
            saved = cache / "snapshots" / f"{entry['dataset_id']}.json"
            if saved.exists() and (spec.source.offline or time.time() - entry["saved_at"] < 86400):
                return load_snapshot(saved)
        if spec.source.offline:
            raise UmapError("OFFLINE_DATA_MISSING", "No saved data covers this map")
        from .sources import acquire

        data = acquire(spec, bbox, cache_dir=cache)
        if len(data.features) > spec.limits.max_features:
            raise UmapError("FEATURE_LIMIT", "The source contains too many features")
        ids = [(f.layer, f.id) for f in data.features]
        if len(set(ids)) != len(ids):
            raise UmapError("DUPLICATE_FEATURE_ID", "Source returned duplicate feature identities")
        data = data.model_copy(
            update={"features": sorted(data.features, key=lambda f: (f.layer, f.id))}
        )
        identity = _snapshot_id(data)
        atomic_json(
            cache / "snapshots" / f"{identity}.json",
            {
                "schema_version": "1",
                "dataset_id": identity,
                "source_profile": _source_profile(spec),
                "dataset": data.model_dump(mode="json"),
            },
        )
        atomic_json(index, {"dataset_id": identity, "saved_at": time.time()})
        return data, identity


def _prepared(data: Dataset, identity: str, spec: MapSpec, extent, cache: Path):
    key = digest(
        {
            "dataset": identity,
            "crs": extent.crs,
            "bounds": extent.bounds,
            "policy": spec.geometry_policy,
            "geometry_version": file_hash(Path(__file__).with_name("geometry.py")),
            "shapely": importlib.metadata.version("shapely"),
            "pyproj": importlib.metadata.version("pyproj"),
        }
    )
    target = cache / "geometry" / f"{key}.json"
    if target.exists():
        try:
            value = json.loads(target.read_text(encoding="utf-8"))
            return PreparedGeometry(
                [Feature.model_validate(f) for f in value["features"]],
                extent.crs,
                extent.bounds,
                extent.scale_denominator,
                [Diagnostic.model_validate(d) for d in value["diagnostics"]],
                extent.projection_distortion,
            )
        except (ValueError, KeyError, OSError):
            pass  # Derived cache is disposable; the verified snapshot is authoritative.
    result = prepare_geometry(data, spec, extent)
    atomic_json(
        target,
        {
            "features": [f.model_dump(mode="json") for f in result.features],
            "diagnostics": [d.model_dump(mode="json") for d in result.diagnostics],
        },
    )
    return result


def _artifact(path: Path, mime: str, view=None) -> Artifact:
    return Artifact(
        path=str(path.resolve()),
        mime_type=mime,
        sha256=file_hash(path),
        size_bytes=path.stat().st_size,
        view=view,
    )


def _resolve(spec: MapSpec, cache: Path) -> MapSpec:
    if spec.area.place:
        if spec.source.offline:
            raise UmapError("OFFLINE_LOCATION", "Use a saved recipe or coordinates when offline")
        from .sources import find_locations

        candidates = find_locations(
            spec.area.place, cache_dir=cache, endpoint=spec.source.photon_url
        )
        if not candidates:
            raise UmapError("LOCATION_NOT_FOUND", "No place matched the query")
        if len(candidates) != 1:
            raise UmapError(
                "AMBIGUOUS_LOCATION",
                "Choose a location candidate and use its coordinates",
                {"candidates": candidates},
            )
        spec = spec.model_copy(
            update={
                "area": AreaSpec(
                    center=candidates[0]["center"], scale_denominator=spec.area.scale_denominator
                )
            }
        )
    return spec


def _render_impl(
    spec: MapSpec | dict | str | Path, *, output_dir="outputs", refresh=False
) -> RenderResult:
    """Render a recipe to a new atomic output directory; refreshing is an explicit service action."""
    started = time.perf_counter()
    recipe_base = Path(spec).resolve().parent if isinstance(spec, (str, Path)) else Path.cwd()
    spec = validate_spec(spec)
    from .styles import validate_style

    validate_style(spec.style)
    if refresh:
        spec = spec.model_copy(
            update={"source": spec.source.model_copy(update={"snapshot": None, "offline": False})}
        )
    if spec.source.snapshot:
        snapshot = Path(spec.source.snapshot)
        if not snapshot.is_absolute():
            snapshot = recipe_base / snapshot
        spec = spec.model_copy(
            update={"source": spec.source.model_copy(update={"snapshot": str(snapshot.resolve())})}
        )
    cache = cache_root()
    spec = _resolve(spec, cache)
    extent = compute_extent(spec)
    data, identity = _get_data(spec, extent.bbox, cache, refresh)
    if len(data.features) > spec.limits.max_features:
        raise UmapError("FEATURE_LIMIT", "The dataset exceeds the requested feature budget")
    ids = [(f.layer, f.id) for f in data.features]
    if len(set(ids)) != len(ids):
        raise UmapError("DUPLICATE_FEATURE_ID", "Dataset contains duplicate feature identities")
    prepared = _prepared(data, identity, spec, extent, cache)
    if any(d.severity == "error" for d in prepared.diagnostics):
        raise UmapError(
            "INCOMPLETE_DATA",
            "Cannot export a dataset with unresolved errors",
            {"diagnostics": [d.model_dump() for d in prepared.diagnostics]},
        )
    from .renderer import render_scene
    from .scene import FONT_PATH, compile_scene

    output = Path(output_dir).resolve()
    output.mkdir(parents=True, exist_ok=True)
    render_id = uuid.uuid4().hex
    staging = output / f".{render_id}.tmp"
    destination = output / render_id
    staging.mkdir()
    diagnostics = list(prepared.diagnostics)
    artifacts = []
    hashes = {}
    versions = {
        name: importlib.metadata.version(name)
        for name in ["umap-art", "shapely", "pyproj", "matplotlib", "osmium", "pyarrow", "pydantic"]
    }
    engine = digest(
        {
            name: file_hash(Path(__file__).with_name(name))
            for name in ("renderer.py", "scene.py", "styles.py", "layout.py")
        }
    )
    font_hash = file_hash(FONT_PATH)
    try:
        for view in spec.views:
            scene = compile_scene(prepared, spec, view)
            semantic_hash = scene.semantic_hash()
            hashes[view] = semantic_hash
            diagnostics.extend(scene.diagnostics)
            render_key = digest(
                {
                    "scene": semantic_hash,
                    "formats": spec.formats,
                    "dpi": spec.page.dpi,
                    "text_mode": spec.page.text_mode,
                    "versions": versions,
                    "font": font_hash,
                    "engine": engine,
                }
            )
            cached = cache / "renders" / render_key
            cached_index = cached / "artifacts.json"
            found = False
            if cached_index.exists():
                try:
                    entries = json.loads(cached_index.read_text(encoding="utf-8"))
                    expected = {f"{view}.{format}" for format in spec.formats}
                    if (
                        len(entries) == len(expected)
                        and {e["name"] for e in entries} == expected
                        and all(
                            (cached / e["name"]).is_file()
                            and file_hash(cached / e["name"]) == e["sha256"]
                            for e in entries
                        )
                    ):
                        for entry in entries:
                            path = staging / entry["name"]
                            shutil.copyfile(cached / entry["name"], path)
                            artifacts.append(_artifact(path, entry["mime_type"], view))
                        found = True
                except (OSError, ValueError, KeyError):
                    pass
            if not found:
                produced = render_scene(scene, spec, staging)
                artifacts.extend(produced)
                cached.mkdir(parents=True, exist_ok=True)
                entries = []
                for a in produced:
                    p = Path(a.path)
                    shutil.copyfile(p, cached / p.name)
                    entries.append({"name": p.name, "sha256": a.sha256, "mime_type": a.mime_type})
                atomic_json(cached_index, entries)
        diagnostics = list({digest(d.model_dump()): d for d in diagnostics}.values())
        snapshot_envelope = {
            "schema_version": "1",
            "dataset_id": identity,
            "source_profile": _source_profile(spec),
            "dataset": data.model_dump(mode="json"),
        }
        atomic_json(staging / "snapshot.json", snapshot_envelope)
        recipe = spec.model_dump(mode="json")
        recipe["source"]["snapshot"] = "snapshot.json"
        recipe["source"]["offline"] = True
        atomic_json(staging / "recipe.json", recipe)
        assets = Path(__file__).parent / "assets"
        if assets.exists():
            shutil.copytree(assets, staging / "assets")
        notices = "Umap code: MIT. Geographic data retains its original license.\nOpenStreetMap contributors: https://www.openstreetmap.org/copyright\nOverture Maps: https://docs.overturemaps.org/attribution/\nSee snapshot.json for per-source provenance and assets/ for font licenses.\n"
        (staging / "DATA-LICENSES.txt").write_text(notices, encoding="utf-8")
        artifacts.extend(
            [
                _artifact(staging / "snapshot.json", "application/json"),
                _artifact(staging / "recipe.json", "application/json"),
            ]
        )
        manifest = {
            "schema_version": "1",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "dataset_id": identity,
            "scene_hashes": hashes,
            "sources": data.sources,
            "coverage": data.coverage,
            "crs": extent.crs,
            "bounds": extent.bounds,
            "scale_denominator": extent.scale_denominator,
            "projection_distortion": extent.projection_distortion,
            "page": spec.page.model_dump(),
            "style": spec.style.model_dump(mode="json"),
            "places": [place.model_dump(mode="json") for place in spec.places],
            "title": spec.title,
            "subtitle": spec.subtitle,
            "versions": versions,
            "elapsed_seconds": time.perf_counter() - started,
            "diagnostics": [d.model_dump() for d in diagnostics],
            "artifacts": [{**a.model_dump(), "path": Path(a.path).name} for a in artifacts],
            "fonts": [
                {"path": str(p.relative_to(staging)).replace("\\", "/"), "sha256": file_hash(p)}
                for p in sorted((staging / "assets").rglob("*.ttf"))
            ]
            if (staging / "assets").exists()
            else [],
        }
        atomic_json(staging / "manifest.json", manifest)
        artifacts.append(_artifact(staging / "manifest.json", "application/json"))
        if spec.bundle:
            with zipfile.ZipFile(
                staging / "project.zip", "w", compression=zipfile.ZIP_DEFLATED
            ) as archive:
                for p in sorted(staging.rglob("*")):
                    if p.is_file() and p.name != "project.zip":
                        archive.write(p, p.relative_to(staging))
            artifacts.append(_artifact(staging / "project.zip", "application/zip"))
        os.replace(staging, destination)
        return RenderResult(
            artifacts=[
                a.model_copy(update={"path": str(destination / Path(a.path).name)})
                for a in artifacts
            ],
            manifest_path=str(destination / "manifest.json"),
            recipe_path=str(destination / "recipe.json"),
            snapshot_path=str(destination / "snapshot.json"),
            dataset_id=identity,
            scene_hashes=hashes,
            diagnostics=diagnostics,
        )
    finally:
        if staging.exists():
            shutil.rmtree(staging)


def render(
    spec: MapSpec | dict | str | Path, *, output_dir="outputs", refresh=False
) -> RenderResult:
    """Render atomically, serializing Matplotlib's process-global state.

    MCP runs each job in a separate owned process. Python callers may use their own
    processes; simultaneous calls within one process are deliberately serialized.
    """
    with _RENDER_LOCK:
        return _render_impl(spec, output_dir=output_dir, refresh=refresh)
