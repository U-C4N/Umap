"""Fail-closed release provenance and exact-byte promotion contracts; no network."""
from __future__ import annotations

import hashlib
import importlib.util
import io
import json
import os
import re
import subprocess
import sys
import tarfile
import textwrap
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
MODULE_SPEC = importlib.util.spec_from_file_location(
    "check_release_candidate", ROOT / "scripts/check_release_candidate.py")
candidate = importlib.util.module_from_spec(MODULE_SPEC)
sys.path.insert(0, str(ROOT / "scripts"))
try:
    MODULE_SPEC.loader.exec_module(candidate)
finally:
    sys.path.pop(0)

SHA = "a" * 40
VERSION = "0.2.0"


def packages(version=VERSION):
    metadata = f"Metadata-Version: 2.4\nName: umap-art\nVersion: {version}\n".encode()
    wheel = io.BytesIO()
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr(f"umap_art-{version}.dist-info/METADATA", metadata)
    source = io.BytesIO()
    with tarfile.open(fileobj=source, mode="w:gz") as archive:
        member = tarfile.TarInfo(f"umap_art-{version}/PKG-INFO")
        member.size = len(metadata)
        archive.addfile(member, io.BytesIO(metadata))
    return {"wheel": wheel.getvalue(), "sdist": source.getvalue()}


def with_waivers(manifest, gates=("pilot", "performance")):
    manifest["schema_version"] = "2"
    for gate in gates:
        manifest["manual"][gate] = {
            "status": "waived", "reason": "Release owner removed this release requirement."}
    manifest["release_owner_authorization"] = {
        "actor": "U-C4N", "version": VERSION, "decision": "waive_manual_gates",
        "gates": list(gates), "authorized_at": "2026-10-23T14:15:16+03:00",
        "source": "explicit_user_confirmation",
        "source_reference": "release-owner-confirmation-2026-10-23",
        "statement": "Evet, bu iki koşulu kaldır ve yayımla",
    }
    return manifest


@pytest.fixture
def manifest(request):
    content = packages()
    value = {
        "schema_version": "1", "version": VERSION, "candidate_sha": SHA,
        "ci_run_id": 123, "artifact_id": 456,
        "files": {
            kind: {"name": f"umap_art-{VERSION}" + (
                "-py3-none-any.whl" if kind == "wheel" else ".tar.gz"),
                "sha256": hashlib.sha256(body).hexdigest()}
            for kind, body in content.items()},
        "manual": {
            "inkscape": {"status": "passed", "evidence": "https://example.com/inkscape"},
            "pilot": {"status": "passed", "results": [
                {"participant_id": f"pilot-{i}", "status": "passed",
                 "evidence": f"https://example.com/pilot/{i}"} for i in range(3)]},
            "performance": {"status": "passed", "reports": [
                {"status": "passed", "evidence": f"https://example.com/perf/{i}"}
                for i in range(3)]},
        },
    }
    return with_waivers(value) if getattr(request, "param", "1") == "2" else value


@pytest.fixture
def run():
    return {"id": 123, "repository": {"full_name": candidate.REPOSITORY},
            "head_repository": {"full_name": candidate.REPOSITORY},
            "path": candidate.WORKFLOW, "event": "push", "head_branch": "main",
            "head_sha": SHA, "status": "completed", "conclusion": "success"}


@pytest.fixture
def artifact():
    return {"id": 456, "name": candidate.ARTIFACT_NAME, "expired": False,
            "workflow_run": {"id": 123, "head_sha": SHA}, "size_in_bytes": 1000}


def artifact_zip(manifest, content=None):
    content = content or packages()
    result = io.BytesIO()
    with zipfile.ZipFile(result, "w") as archive:
        for kind, body in content.items():
            archive.writestr("dist/" + manifest["files"][kind]["name"], body)
        archive.writestr("../../outside.txt", "must never be extracted")
        archive.writestr(".cache/test-results.xml", "unrelated CI evidence")
    return result.getvalue()


def change(value, path, replacement):
    for key in path[:-1]:
        value = value[key]
    value[path[-1]] = replacement


@pytest.mark.parametrize("manifest", ["1", "2"], indirect=True)
def test_complete_evidence_accepts_only_recorded_candidate(manifest):
    assert candidate.validate_manifest(manifest, VERSION, SHA) == manifest
    with pytest.raises(ValueError, match="SHA"):
        candidate.validate_manifest(manifest, VERSION, "b" * 40)
    with pytest.raises(ValueError, match="version"):
        candidate.validate_manifest(manifest, "0.3.0", SHA)


@pytest.mark.parametrize("path,value", [
    (("schema_version",), "2"), (("ci_run_id",), True), (("artifact_id",), 0),
    (("files", "wheel", "name"), "../evil.whl"),
    (("files", "sdist", "name"), "umap_art-0.1.0.tar.gz"),
    (("files", "wheel", "sha256"), "0" * 64),
    (("manual", "inkscape", "status"), "pending"),
    (("manual", "inkscape", "evidence"), "file:///acceptance.txt"),
    (("manual", "pilot", "results"), []),
    (("manual", "pilot", "results", 1, "participant_id"), "pilot-0"),
    (("manual", "pilot", "results", 2, "status"), "failed"),
    (("manual", "performance", "reports", 2, "status"), "pending"),
    (("manual", "performance", "reports", 1, "evidence"), "https://example.com/perf/0"),
])
def test_incomplete_or_misbound_evidence_is_rejected(manifest, path, value):
    change(manifest, path, value)
    with pytest.raises(ValueError):
        candidate.validate_manifest(manifest, VERSION, SHA)


def test_missing_acceptance_and_pending_template_fail_closed(manifest):
    del manifest["manual"]["performance"]
    with pytest.raises(ValueError, match="manual acceptance"):
        candidate.validate_manifest(manifest, VERSION, SHA)
    template = json.loads((ROOT / "docs/release-evidence.example.json").read_text("utf-8"))
    with pytest.raises(ValueError):
        candidate.validate_manifest(template, VERSION, SHA)


@pytest.mark.parametrize("gates", [
    ("pilot",), ("performance",), ("pilot", "performance"),
    ("inkscape",), ("inkscape", "pilot", "performance"),
])
def test_schema_two_accepts_only_explicitly_scoped_waivers(manifest, gates):
    with_waivers(manifest, gates)
    assert candidate.validate_manifest(manifest, VERSION, SHA) == manifest
    for gate in {"inkscape", "pilot", "performance"} - set(gates):
        assert manifest["manual"][gate]["status"] == "passed"


@pytest.mark.parametrize("mutation", ["waiver", "authorization", "waiver_with_results", "inkscape"])
def test_schema_one_cannot_use_waivers_or_authorization(manifest, mutation):
    if mutation == "authorization":
        manifest["release_owner_authorization"] = with_waivers({"manual": {}})[
            "release_owner_authorization"]
    elif mutation == "inkscape":
        manifest["manual"]["inkscape"] = {"status": "waived", "reason": "Owner request"}
    elif mutation == "waiver":
        manifest["manual"]["pilot"] = {"status": "waived", "reason": "Owner request"}
    else:
        manifest["manual"]["pilot"]["status"] = "waived"
    with pytest.raises(ValueError):
        candidate.validate_manifest(manifest, VERSION, SHA)


@pytest.mark.parametrize("field,value", [
    ("actor", "other-owner"), ("version", "0.3.0"), ("decision", "approved"),
    ("source", "inferred_user_intent"), ("source_reference", "  "), ("statement", ""),
    ("gates", []), ("gates", ["pilot"]), ("gates", ["pilot", "pilot", "performance"]),
    ("gates", ["pilot", "performance", "inkscape"]), ("gates", "pilot,performance"),
    ("gates", ["pilot", "performance", "ci"]),
    ("gates", ["pilot", {}]), ("authorized_at", None),
    ("authorized_at", "2026-10-23"), ("authorized_at", "2026-10-23T14:15:16"),
    ("authorized_at", "2026-02-30T14:15:16Z"),
    ("authorized_at", "2026-10-23T14:15:16+24:00"),
    ("authorized_at", "2026-10-23T14:15:16+01:60"),
])
def test_schema_two_rejects_invalid_authorization(manifest, field, value):
    with_waivers(manifest)
    manifest["release_owner_authorization"][field] = value
    with pytest.raises(ValueError):
        candidate.validate_manifest(manifest, VERSION, SHA)


@pytest.mark.parametrize("timestamp", ["2026-10-23T11:15:16Z", "2026-10-23T11:15:16.123+00:00"])
def test_waiver_timestamp_accepts_valid_timezone_formats(manifest, timestamp):
    with_waivers(manifest)
    manifest["release_owner_authorization"]["authorized_at"] = timestamp
    candidate.validate_manifest(manifest, VERSION, SHA)


@pytest.mark.parametrize("mutation", [
    "missing_authorization", "missing_statement", "extra_authorization_field", "no_waivers",
    "blank_reason", "passed_with_reason", "waived_with_results", "inkscape_waived_with_evidence",
    "unwaived_pilot_incomplete", "pending_template",
])
def test_schema_two_never_implies_manual_test_success(manifest, mutation):
    with_waivers(manifest, () if mutation == "no_waivers" else ("performance",))
    if mutation == "missing_authorization":
        del manifest["release_owner_authorization"]
    elif mutation == "missing_statement":
        del manifest["release_owner_authorization"]["statement"]
    elif mutation == "extra_authorization_field":
        manifest["release_owner_authorization"]["override_ci"] = True
    elif mutation == "blank_reason":
        manifest["manual"]["performance"]["reason"] = "  "
    elif mutation == "passed_with_reason":
        manifest["manual"]["performance"]["status"] = "passed"
    elif mutation == "waived_with_results":
        manifest["manual"]["performance"]["reports"] = []
    elif mutation == "inkscape_waived_with_evidence":
        manifest["manual"]["inkscape"]["status"] = "waived"
    elif mutation == "unwaived_pilot_incomplete":
        manifest["manual"]["pilot"]["results"] = []
    elif mutation == "pending_template":
        manifest = json.loads((ROOT / "docs/release-evidence-waiver.example.json").read_text("utf-8"))
    with pytest.raises(ValueError):
        candidate.validate_manifest(manifest, VERSION, SHA)


@pytest.mark.parametrize("mutation", [
    "missing_authorization", "scope_mismatch", "extra_gate", "false_passed", "fake_waiver_data",
])
def test_all_manual_waivers_still_require_exact_authorization(manifest, mutation):
    with_waivers(manifest, ("inkscape", "pilot", "performance"))
    if mutation == "missing_authorization":
        del manifest["release_owner_authorization"]
    elif mutation == "scope_mismatch":
        manifest["release_owner_authorization"]["gates"] = ["pilot", "performance"]
    elif mutation == "extra_gate":
        manifest["release_owner_authorization"]["gates"].append("ci")
    elif mutation == "false_passed":
        manifest["manual"]["inkscape"] = {"status": "passed", "evidence": None}
        manifest["release_owner_authorization"]["gates"].remove("inkscape")
    elif mutation == "fake_waiver_data":
        manifest["manual"]["inkscape"]["evidence"] = "https://example.com/fake-success"
    with pytest.raises(ValueError):
        candidate.validate_manifest(manifest, VERSION, SHA)


@pytest.mark.parametrize("path,value", [
    (("candidate_sha",), "b" * 40), (("ci_run_id",), True), (("artifact_id",), 0),
    (("files", "wheel", "sha256"), "0" * 64),
    (("files", "sdist", "name"), "umap_art-0.1.0.tar.gz"),
])
def test_waivers_do_not_change_candidate_identity_requirements(manifest, path, value):
    with_waivers(manifest)
    change(manifest, path, value)
    with pytest.raises(ValueError):
        candidate.validate_manifest(manifest, VERSION, SHA)


@pytest.mark.parametrize("manifest", ["1", "2"], indirect=True)
@pytest.mark.parametrize("field,value", [
    ("id", 999), ("repository", {"full_name": "other/Umap"}),
    ("head_repository", {"full_name": "fork/Umap"}),
    ("path", ".github/workflows/other.yml"), ("event", "pull_request"),
    ("head_branch", "feature"), ("head_sha", "b" * 40),
    ("status", "in_progress"), ("conclusion", "failure"),
])
def test_untrusted_ci_run_is_rejected(manifest, run, field, value):
    run[field] = value
    with pytest.raises(ValueError):
        candidate.validate_run(run, manifest)


@pytest.mark.parametrize("suffix", ["", "@main", "@refs/heads/main", "@" + SHA])
def test_expected_workflow_accepts_api_ref_suffixes(manifest, run, suffix):
    run["path"] = candidate.WORKFLOW + suffix
    candidate.validate_run(run, manifest)


@pytest.mark.parametrize("path", [
    ".github/workflows/other.yml@main", ".github/workflows/ci.yml.evil@main",
    ".github/workflows/ci.yml@feature", ".github/workflows/ci.yml@refs/tags/main",
    ".github/workflows/ci.yml@", ".github/workflows/ci.yml@main@main",
    ".github/workflows/ci.yml@" + "b" * 40,
])
def test_other_workflow_or_ref_is_rejected(manifest, run, path):
    run["path"] = path
    with pytest.raises(ValueError, match="Unexpected candidate workflow"):
        candidate.validate_run(run, manifest)


@pytest.mark.parametrize("manifest", ["1", "2"], indirect=True)
@pytest.mark.parametrize("field,value", [
    ("id", 789), ("name", "wrong-package"), ("expired", True),
    ("workflow_run", {"id": 789, "head_sha": SHA}),
    ("workflow_run", {"id": 123, "head_sha": "b" * 40}),
    ("size_in_bytes", candidate.MAX_PACKAGE_BYTES + 1),
])
def test_untrusted_artifact_is_rejected(manifest, artifact, field, value):
    artifact[field] = value
    with pytest.raises(ValueError):
        candidate.validate_artifact(artifact, manifest)


def test_promoted_bytes_are_unchanged_and_unrelated_members_are_ignored(manifest):
    content = packages()
    # Tar gzip headers can contain time; bind the actual input bytes explicitly.
    for kind, body in content.items():
        manifest["files"][kind]["sha256"] = hashlib.sha256(body).hexdigest()
    result = candidate.verified_distributions(artifact_zip(manifest, content), manifest)
    assert result == {manifest["files"][kind]["name"]: body for kind, body in content.items()}


@pytest.mark.parametrize("manifest", ["1", "2"], indirect=True)
def test_mismatched_hash_rejects_packages(manifest):
    manifest["files"]["wheel"]["sha256"] = "f" * 64
    with pytest.raises(ValueError, match="hash mismatch"):
        candidate.verified_distributions(artifact_zip(manifest), manifest)


@pytest.mark.parametrize("manifest", ["1", "2"], indirect=True)
@pytest.mark.parametrize("kind", ["wheel", "sdist"])
def test_matching_hash_does_not_excuse_wrong_package_metadata(manifest, kind):
    content = packages()
    content[kind] = packages("9.9.9")[kind]
    for key, body in content.items():
        manifest["files"][key]["sha256"] = hashlib.sha256(body).hexdigest()
    with pytest.raises(ValueError, match="metadata mismatch"):
        candidate.verified_distributions(artifact_zip(manifest, content), manifest)


class FakeGitHub:
    def __init__(self, data):
        self.data = data
        self.calls = []

    def read(self, path, **kwargs):
        self.calls.append(path)
        return self.data[path]


def fake_release(manifest, run, artifact):
    content = packages()
    for kind, body in content.items():
        manifest["files"][kind]["sha256"] = hashlib.sha256(body).hexdigest()
    prefix = "/repos/" + candidate.REPOSITORY
    data = {
        f"{prefix}/releases/7": {"id": 7, "tag_name": "v0.2.0", "draft": False,
                                 "prerelease": False},
        f"{prefix}/git/ref/tags/v0.2.0": {"object": {"type": "tag", "sha": "c" * 40}},
        f"{prefix}/git/tags/{'c' * 40}": {"object": {"type": "commit", "sha": SHA}},
        f"{prefix}/releases/7/assets?per_page=100": [
            {"id": 8, "name": "release-evidence.json", "size": 2000,
             "browser_download_url": "https://untrusted.invalid/never-fetch"}],
        f"{prefix}/releases/assets/8": json.dumps(manifest).encode(),
        f"{prefix}/actions/runs/123": run,
        f"{prefix}/actions/runs/123/artifacts?per_page=100": {"artifacts": [artifact]},
    }
    event = {"action": "published", "repository": {"full_name": candidate.REPOSITORY},
             "release": {"id": 7, "tag_name": "v0.2.0"}}
    return event, FakeGitHub(data)


@pytest.mark.parametrize("manifest", ["1", "2"], indirect=True)
def test_release_uses_only_its_own_asset_and_fixed_github_api_paths(manifest, run, artifact):
    event, client = fake_release(manifest, run, artifact)
    result = candidate.collect_candidate(event, client, VERSION, SHA)
    assert result == manifest
    assert all(path.startswith("/repos/U-C4N/Umap/") for path in client.calls)
    assert not any("untrusted" in path or "example.com" in path for path in client.calls)
    assert not any(path.endswith("/zip") for path in client.calls)


@pytest.mark.parametrize("manifest", ["1", "2"], indirect=True)
def test_artifact_membership_is_required(manifest, run, artifact):
    event, client = fake_release(manifest, run, artifact)
    client.data["/repos/U-C4N/Umap/actions/runs/123/artifacts?per_page=100"] = {"artifacts": []}
    with pytest.raises(ValueError, match="not a member"):
        candidate.collect_candidate(event, client, VERSION, SHA)
    assert not any(path.endswith("/zip") for path in client.calls)


@pytest.mark.parametrize("manifest", ["1", "2"], indirect=True)
def test_missing_release_evidence_never_falls_back_to_build(manifest, run, artifact):
    event, client = fake_release(manifest, run, artifact)
    client.data["/repos/U-C4N/Umap/releases/7/assets?per_page=100"] = []
    with pytest.raises(ValueError, match="exactly one"):
        candidate.collect_candidate(event, client, VERSION, SHA)


@pytest.mark.parametrize("manifest", ["1", "2"], indirect=True)
def test_release_tag_cannot_move_after_checkout(manifest, run, artifact):
    event, client = fake_release(manifest, run, artifact)
    client.data[f"/repos/U-C4N/Umap/git/tags/{'c' * 40}"] = {
        "object": {"type": "commit", "sha": "b" * 40}}
    with pytest.raises(ValueError, match="Remote release tag"):
        candidate.collect_candidate(event, client, VERSION, SHA)


def test_redirect_strips_github_token():
    request = candidate.urllib.request.Request("https://api.github.com/repos/U-C4N/Umap/test",
                                                headers={"Authorization": "Bearer secret"})
    redirected = candidate.SafeRedirect().redirect_request(
        request, None, 302, "Found", {}, "https://storage.example.com/artifact")
    assert redirected.get_header("Authorization") is None
    with pytest.raises(ValueError, match="Non-HTTPS"):
        candidate.SafeRedirect().redirect_request(request, None, 302, "Found", {},
                                                  "http://storage.example.com/artifact")


@pytest.mark.parametrize("manifest", ["1", "2"], indirect=True)
def test_provenance_mode_emits_only_validated_download_identity(
        tmp_path, monkeypatch, manifest, run, artifact):
    event, client = fake_release(manifest, run, artifact)
    event_path = tmp_path / "event.json"
    event_path.write_text(json.dumps(event))
    manifest_path = tmp_path / "candidate-evidence.json"
    github_output = tmp_path / "github-output"
    monkeypatch.setattr(candidate, "GitHub", lambda token: client)
    monkeypatch.setattr(candidate.subprocess, "check_output", lambda *a, **k: SHA)
    monkeypatch.setattr(sys, "argv", ["check_release_candidate", "--event", str(event_path),
                                     "--manifest", str(manifest_path),
                                     "--github-output", str(github_output)])
    assert candidate.main() == 0
    assert json.loads(manifest_path.read_text("utf-8")) == manifest
    values = dict(line.split("=", 1) for line in github_output.read_text("utf-8").splitlines())
    assert values["run_id"] == "123" and values["artifact_id"] == "456"
    assert json.loads(values["distributions"]) == {
        item["name"]: item["sha256"] for item in manifest["files"].values()}
    assert not any(path.endswith("/zip") for path in client.calls)


@pytest.mark.parametrize("manifest", ["1", "2"], indirect=True)
def test_hash_outputs_are_bound_to_the_written_candidate_files(tmp_path, monkeypatch, manifest):
    output = tmp_path / "accepted-dist"
    github_output = tmp_path / "github-output"
    download = tmp_path / "download"
    (download / "dist").mkdir(parents=True)
    files = {}
    for kind, body in packages().items():
        item = manifest["files"][kind]
        item["sha256"] = hashlib.sha256(body).hexdigest()
        files[item["name"]] = body
        (download / "dist" / item["name"]).write_bytes(body)
    manifest_path = tmp_path / "candidate-evidence.json"
    manifest_path.write_text(json.dumps(manifest))
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.setattr(candidate.subprocess, "check_output", lambda *a, **k: SHA)
    monkeypatch.setattr(sys, "argv", ["check_release_candidate", "--verify-download", str(download),
                                     "--manifest", str(manifest_path),
                                     "--output", str(output), "--github-output", str(github_output)])
    assert candidate.main() == 0
    lines = github_output.read_text("utf-8").splitlines()
    values = dict(line.split("=", 1) for line in lines)
    assert values["run_id"] == "123" and values["artifact_id"] == "456"
    hashes = json.loads(values["distributions"])
    assert set(hashes) == set(files)
    for name, digest in hashes.items():
        assert (output / name).read_bytes() == files[name]
        assert hashlib.sha256((output / name).read_bytes()).hexdigest() == digest


@pytest.mark.parametrize("manifest", ["1", "2"], indirect=True)
@pytest.mark.parametrize("mutation", ["changed", "missing", "extra", "directory", "metadata"])
def test_download_verification_rejects_unaccepted_packages(tmp_path, manifest, mutation):
    dist = tmp_path / "dist"
    dist.mkdir()
    content = packages()
    if mutation == "metadata":
        content["wheel"] = packages("9.9.9")["wheel"]
    for kind, body in content.items():
        item = manifest["files"][kind]
        item["sha256"] = hashlib.sha256(body).hexdigest()
        (dist / item["name"]).write_bytes(body)
    first = dist / manifest["files"]["wheel"]["name"]
    if mutation == "changed":
        first.write_bytes(b"changed")
    elif mutation == "missing":
        first.unlink()
    elif mutation == "extra":
        (dist / "extra.whl").write_bytes(b"extra")
    elif mutation == "directory":
        first.unlink()
        first.mkdir()
    with pytest.raises(ValueError):
        candidate.verified_download(tmp_path, manifest)


def test_cross_run_download_action_uses_validated_identity():
    workflow = (ROOT / ".github/workflows/publish.yml").read_text("utf-8")
    block = workflow.split("      - name: Download the exact artifact from the accepted candidate run\n",
                           1)[1].split("      - name:", 1)[0]
    assert "actions/download-artifact@9000827ccba6bdab643e8b6fd33ac0654aef8333" in block
    assert "artifact-ids: ${{ steps.candidate-check.outputs.artifact_id }}" in block
    assert "run-id: ${{ steps.candidate-check.outputs.run_id }}" in block
    assert "github-token: ${{ github.token }}" in block
    assert "repository: U-C4N/Umap" in block


@pytest.mark.parametrize("mutation", [None, "changed", "missing", "extra", "directory"])
def test_publishing_job_verifies_final_downloaded_bytes(tmp_path, mutation):
    workflow = (ROOT / ".github/workflows/publish.yml").read_text("utf-8")
    block = re.search(r"(?ms)^          python3 - <<'PY'\n(.*?)^          PY$", workflow)
    assert block is not None, "Publishing job must include its fixed inline hash verifier"
    script = textwrap.dedent(block.group(1))
    contents = {"umap_art-0.2.0-py3-none-any.whl": b"wheel bytes",
                "umap_art-0.2.0.tar.gz": b"source bytes"}
    folder = tmp_path / "release-artifacts"
    folder.mkdir()
    for name, body in contents.items():
        (folder / name).write_bytes(body)
    first = folder / next(iter(contents))
    if mutation == "changed":
        first.write_bytes(b"different bytes")
    elif mutation == "missing":
        first.unlink()
    elif mutation == "extra":
        (folder / "unexpected.txt").write_text("unexpected")
    elif mutation == "directory":
        first.unlink()
        first.mkdir()
    environment = dict(os.environ, EXPECTED_DISTRIBUTIONS=json.dumps({
        name: hashlib.sha256(body).hexdigest() for name, body in contents.items()}))
    result = subprocess.run([sys.executable, "-I", "-"], input=script, cwd=tmp_path,
                            env=environment, text=True, capture_output=True, timeout=15)
    assert (result.returncode == 0) is (mutation is None), result.stdout + result.stderr
