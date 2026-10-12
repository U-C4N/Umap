"""Workspace transaction, process ownership, and containment acceptance tests."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

from umap_art.errors import UmapError
from umap_art.models import Dataset, Feature, MapSpec
from umap_art.service import _snapshot_id
from umap_art.workspace import Workspace


def recipe(root: Path) -> dict:
    dataset = Dataset(bbox=(28.0, 40.0, 30.0, 42.0), sources=[{
        "provider": "test", "license": "CC0", "attribution": "Synthetic test data"}],
        features=[Feature(id="test/building", layer="buildings", geometry={
            "type": "Polygon", "coordinates": [[[28.99, 41.0], [28.991, 41.0],
                [28.991, 41.001], [28.99, 41.001], [28.99, 41.0]]]}, properties={"building": "yes"})])
    snapshot = root / "input.json"
    snapshot.parent.mkdir(parents=True, exist_ok=True)
    snapshot.write_text(json.dumps({"schema_version": "1", "dataset_id": _snapshot_id(dataset),
                                   "dataset": dataset.model_dump(mode="json")}), encoding="utf-8")
    return MapSpec(area={"center": [28.99, 41.0]}, page={"size": "A4", "dpi": 72},
                   source={"snapshot": str(snapshot), "offline": True},
                   formats=["svg"], bundle=False).model_dump(mode="json")


def wait_for(workspace: Workspace, job_id: str, states=None, timeout=30):
    states = states or {"succeeded", "failed", "cancelled", "interrupted"}
    stop = time.monotonic() + timeout
    while time.monotonic() < stop:
        result = workspace.get_job(job_id)
        if result["state"] in states:
            return result
        time.sleep(0.04)
    pytest.fail(f"Job did not reach {states}: {workspace.get_job(job_id)}")


def test_idempotence_revision_queue_transaction_and_restart(tmp_path):
    spec = recipe(tmp_path)
    with Workspace(tmp_path, start_worker=False) as workspace:
        created = workspace.create_map(spec, request_id="create-1")
        assert workspace.create_map(spec, request_id="create-1") == created
        changed = {**spec, "title": "Different"}
        with pytest.raises(UmapError, match="different arguments"):
            workspace.create_map(changed, request_id="create-1")
        first_edit = workspace.edit_map(created["map_id"], 1, {"title": "İstanbul"}, request_id="edit-1")
        assert first_edit["revision"] == 2
        assert workspace.edit_map(created["map_id"], 1, {"title": "İstanbul"}, request_id="edit-1") == first_edit
        with pytest.raises(UmapError) as conflict:
            workspace.edit_map(created["map_id"], 1, {"title": "Old"})
        assert conflict.value.code == "REVISION_CONFLICT"
        workspace.render_map(created["map_id"])
        workspace.render_map(created["map_id"])
        with pytest.raises(UmapError) as full:
            workspace.edit_map(created["map_id"], 2, {"title": "Must roll back"})
        assert full.value.code == "QUEUE_FULL"
        assert workspace.inspect_map(created["map_id"])["revision"] == 2
    with Workspace(tmp_path, start_worker=False) as reopened:
        assert reopened.get_job(created["job_id"])["state"] == "interrupted"
        assert reopened.inspect_map(created["map_id"])["spec"]["title"] == "İstanbul"
        assert reopened.create_map(spec, request_id="create-1") == created


def test_restore_preserves_history_and_only_known_fields_are_editable(tmp_path):
    with Workspace(tmp_path, start_worker=False) as workspace:
        created = workspace.create_map(recipe(tmp_path))
        workspace.edit_map(created["map_id"], 1, {"style": {"layers": {"roads": {"width_mm": 0.8}}}})
        restored = workspace.edit_map(created["map_id"], 2, restore_revision=1)
        assert restored["revision"] == 3
        assert workspace.inspect_map(created["map_id"])["spec"]["style"]["layers"] == {}
        with pytest.raises(UmapError) as unsafe:
            workspace.edit_map(created["map_id"], 3, {"source": {"snapshot": "outside"}})
        assert unsafe.value.code == "INVALID_EDIT"
        with pytest.raises(UmapError):
            workspace.edit_map(created["map_id"], 3, {"style": {"rules": [{
                "layer": "roads", "when": {"eval": "1+1"}, "paint": {}}]}})
        assert workspace.inspect_map(created["map_id"])["revision"] == 3


def test_provider_and_snapshot_paths_are_workspace_scoped(tmp_path):
    with Workspace(tmp_path / "workspace", start_worker=False) as workspace:
        spec = recipe(workspace.root)
        spec["source"]["photon_url"] = "http://127.0.0.1:1234"
        with pytest.raises(UmapError) as blocked:
            workspace.create_map(spec)
        assert blocked.value.code == "PROVIDER_NOT_ALLOWED"
        spec["source"].pop("photon_url")
        spec["source"]["snapshot"] = str(tmp_path / "outside.json")
        with pytest.raises(UmapError) as outside:
            workspace.create_map(spec)
        assert outside.value.code == "PATH_OUTSIDE_WORKSPACE"
    with Workspace(tmp_path / "configured", provider_urls={"photon_url": "http://localhost:1234"}, start_worker=False) as configured:
        created = configured.create_map(recipe(configured.root))
        assert configured.inspect_map(created["map_id"])["spec"]["source"]["photon_url"] == "http://localhost:1234"


def test_symlink_snapshot_escape(tmp_path):
    root = tmp_path / "workspace"
    spec = recipe(root)
    target = tmp_path / "outside"
    target.mkdir()
    link = root / "link"
    try:
        link.symlink_to(target, target_is_directory=True)
    except OSError:
        if os.name != "nt":
            pytest.skip("Creating symlinks is unavailable on this host")
        import _winapi
        _winapi.CreateJunction(str(target), str(link))
    spec["source"]["snapshot"] = str(link / "secret.json")
    with Workspace(root, start_worker=False) as workspace, pytest.raises(UmapError) as blocked:
        workspace.create_map(spec)
    assert blocked.value.code == "PATH_OUTSIDE_WORKSPACE"
    link.rmdir() if link.is_junction() else link.unlink()


def test_exclusive_workspace_owner(tmp_path):
    with Workspace(tmp_path):
        with pytest.raises(UmapError) as error:
            Workspace(tmp_path)
        assert error.value.code == "WORKSPACE_BUSY"


SLOW_WORKER = (
    "import sys,time,os,json,threading; "
    "request=json.loads(sys.stdin.buffer.readline()); "
    "threading.Thread(target=lambda:(sys.stdin.buffer.read(),os._exit(143)),daemon=True).start(); "
    "time.sleep(60)"
)


def test_cancel_running_and_queued_jobs_cleanup_process(tmp_path):
    with Workspace(tmp_path, worker_command=[sys.executable, "-c", SLOW_WORKER]) as workspace:
        first = workspace.create_map(recipe(tmp_path))
        wait_for(workspace, first["job_id"], {"running"})
        stop = time.monotonic() + 5
        while workspace._process is None and time.monotonic() < stop:
            time.sleep(0.01)
        process = workspace._process
        assert process is not None
        second = workspace.render_map(first["map_id"])
        assert workspace.cancel_job(second["job_id"])["state"] == "cancelled"
        workspace.cancel_job(first["job_id"])
        assert wait_for(workspace, first["job_id"])["state"] == "cancelled"
        assert process.poll() is not None
        assert workspace.get_job(first["job_id"])["artifacts"] == []


def test_timeout_and_owner_close_leave_no_worker(tmp_path):
    workspace = Workspace(tmp_path, worker_command=[sys.executable, "-c", SLOW_WORKER], job_timeout=0.3)
    created = workspace.create_map(recipe(tmp_path))
    failed = wait_for(workspace, created["job_id"])
    assert failed["state"] == "failed"
    assert failed["error"]["code"] == "JOB_TIMEOUT"
    second = workspace.render_map(created["map_id"])
    wait_for(workspace, second["job_id"], {"running"})
    workspace.close()
    assert workspace._process is None or workspace._process.poll() is not None
    with Workspace(tmp_path, start_worker=False) as reopened:
        assert reopened.get_job(second["job_id"])["state"] == "interrupted"


def test_worker_crash_has_no_public_artifacts(tmp_path):
    with Workspace(tmp_path, worker_command=[sys.executable, "-c", "import os; os._exit(2)"]) as workspace:
        created = workspace.create_map(recipe(tmp_path))
        failed = wait_for(workspace, created["job_id"])
        assert failed["state"] == "failed"
        assert failed["artifacts"] == []


def test_real_worker_pins_snapshot_and_style_revision(tmp_path):
    with Workspace(tmp_path) as workspace:
        created = workspace.create_map(recipe(tmp_path))
        first = wait_for(workspace, created["job_id"])
        assert first["state"] == "succeeded", first
        initial = workspace.inspect_map(created["map_id"])
        assert initial["dataset_id"]
        assert initial["spec"]["source"]["snapshot"] != str(tmp_path / "input.json")
        svg = next(a for a in first["artifacts"] if a["mime_type"] == "image/svg+xml")
        assert b"svg" in workspace.read_artifact(svg["artifact_id"])
        assert workspace.read_artifact_chunk(svg["artifact_id"], 0) == workspace.read_artifact(svg["artifact_id"])
        assert workspace.read_artifact_chunk(svg["artifact_id"], svg["size_bytes"]) == b""
        with pytest.raises(UmapError):
            workspace.read_artifact_chunk(svg["artifact_id"], -1)
        changed = workspace.edit_map(created["map_id"], 1, {"style": {"layers": {"buildings": {"fill": "#FF0000"}}}})
        preview = wait_for(workspace, changed["job_id"])
        assert preview["state"] == "succeeded", preview
        assert preview["result"]["dataset_id"] == first["result"]["dataset_id"]
        png = next(a for a in preview["artifacts"] if a["mime_type"] == "image/png")
        assert workspace.get_artifact(png["artifact_id"], include_preview=True)["preview_base64"]


def test_refresh_conflict_cannot_overwrite_newer_revision(tmp_path):
    # Simulate a completed acquisition racing a user edit. Publication must be atomic.
    from umap_art.models import RenderResult
    from umap_art.service import render
    with Workspace(tmp_path, start_worker=False) as workspace:
        spec = recipe(tmp_path)
        created = workspace.create_map(spec)
        refresh = workspace.refresh_map_data(created["map_id"], 1)
        workspace.edit_map(created["map_id"], 1, {"title": "Newer"})
        output = workspace.root / "jobs" / refresh["job_id"] / "output"
        result: RenderResult = render(spec, output_dir=output)
        job = workspace._db.execute("SELECT * FROM jobs WHERE id=?", (refresh["job_id"],)).fetchone()
        with pytest.raises(UmapError) as error:
            workspace._publish(job, result, output)
        assert error.value.code == "REVISION_CONFLICT"
        assert workspace.inspect_map(created["map_id"])["spec"]["title"] == "Newer"
        assert workspace.get_job(refresh["job_id"])["artifacts"] == []


def test_abrupt_owner_exit_closes_worker_pipe(tmp_path):
    import psutil
    spec = recipe(tmp_path)
    script = """
import json,sys,time
from umap_art.workspace import Workspace
request=json.loads(sys.stdin.readline())
workspace=Workspace(request['root'],worker_command=request['command'])
workspace.create_map(request['spec'])
while workspace._process is None:
    time.sleep(0.01)
print(workspace._process.pid,flush=True)
sys.stdin.read()
"""
    kwargs = {"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {}
    owner = subprocess.Popen([sys.executable, "-c", script], stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, **kwargs)
    worker = None
    try:
        owner.stdin.write(json.dumps({"root": str(tmp_path), "spec": spec,
                                      "command": [sys.executable, "-c", SLOW_WORKER]}) + "\n")
        owner.stdin.flush()
        # The owner announces the child without waiting for its render to complete.
        worker = psutil.Process(int(owner.stdout.readline()))
        owner.kill()
        owner.wait(timeout=5)
        worker.wait(timeout=5)
        assert not worker.is_running()
    finally:
        if owner.poll() is None:
            owner.kill()
            owner.wait(timeout=5)
        if worker is not None and worker.is_running():
            worker.kill()
