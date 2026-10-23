"""Promote only the exact CI distributions named by this release's human evidence.

Evidence URLs are records for the release reviewer; this script never fetches them
or claims to independently verify the human acceptance tests.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
import subprocess
import tarfile
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from datetime import datetime
from email.parser import BytesParser
from pathlib import Path

from check_release import check_release

REPOSITORY = "U-C4N/Umap"
WORKFLOW = ".github/workflows/ci.yml"
ARTIFACT_NAME = "umap-ubuntu-24.04-py3.14"
API = "https://api.github.com"
MAX_PACKAGE_BYTES = 100 * 1024 * 1024


def require(condition, message):
    if not condition:
        raise ValueError(message)


def fields(value, names, label):
    require(isinstance(value, dict) and set(value) == set(names),
            f"Invalid {label} fields")


def positive_id(value, label):
    require(type(value) is int and value > 0, f"Invalid {label}")


def evidence(value):
    require(isinstance(value, str) and len(value) <= 2048, "Invalid evidence reference")
    url = urllib.parse.urlsplit(value)
    require(url.scheme == "https" and url.netloc and not url.username,
            "Evidence must be an HTTPS reference")


def nonblank(value, label):
    require(isinstance(value, str) and value.strip() and len(value) <= 2048,
            f"Invalid {label}")


def validate_authorization(value, version, waived):
    fields(value, {"actor", "version", "decision", "gates", "authorized_at", "source",
                   "source_reference", "statement"}, "release owner authorization")
    require(value["actor"] == "U-C4N" and value["version"] == version,
            "Release owner authorization identity/version mismatch")
    require(value["decision"] == "waive_manual_gates"
            and value["source"] == "explicit_user_confirmation",
            "An explicit release owner waiver is required")
    gates = value["gates"]
    require(isinstance(gates, list) and gates and all(isinstance(g, str) for g in gates)
            and len(set(gates)) == len(gates) and set(gates) == waived,
            "Authorization gates must exactly match the waived manual gates")
    for key in ("source_reference", "statement"):
        nonblank(value[key], f"authorization {key}")
    timestamp = value["authorized_at"]
    require(isinstance(timestamp, str) and re.fullmatch(
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?"
        r"(?:Z|[+-](?:[01]\d|2[0-3]):[0-5]\d)",
        timestamp), "Authorization timestamp must include an ISO 8601 timezone")
    require(datetime.fromisoformat(timestamp).utcoffset() is not None,
            "Authorization timestamp must include a timezone")


def validate_manifest(value, version, commit):
    require(isinstance(value, dict) and value.get("schema_version") in ("1", "2"),
            "Unsupported evidence schema")
    schema = value["schema_version"]
    required = {"schema_version", "version", "candidate_sha", "ci_run_id", "artifact_id",
                "files", "manual"}
    if schema == "2":
        required.add("release_owner_authorization")
    fields(value, required, "manifest")
    require(re.fullmatch(r"\d+\.\d+\.\d+", version) is not None,
            "Only stable release versions are supported")
    require(value["version"] == version, "Evidence version does not match release")
    require(isinstance(commit, str) and re.fullmatch(r"[0-9a-f]{40}", commit)
            and commit != "0" * 40 and value["candidate_sha"] == commit,
            "Candidate SHA does not match the resolved release commit")
    positive_id(value["ci_run_id"], "CI run ID")
    positive_id(value["artifact_id"], "artifact ID")
    fields(value["files"], {"wheel", "sdist"}, "distribution")
    for kind, record in value["files"].items():
        fields(record, {"name", "sha256"}, kind)
        name, sha = record["name"], record["sha256"]
        require(isinstance(name, str) and Path(name).name == name
                and "/" not in name and "\\" not in name, "Unsafe distribution filename")
        expected = (rf"umap_art-{re.escape(version)}-[A-Za-z0-9_.]+-[A-Za-z0-9_.]+-"
                    rf"[A-Za-z0-9_.]+\.whl") if kind == "wheel" else (
                        rf"umap_art-{re.escape(version)}\.tar\.gz")
        require(re.fullmatch(expected, name), "Distribution filename/version mismatch")
        require(isinstance(sha, str) and re.fullmatch(r"[0-9a-f]{64}", sha)
                and sha != "0" * 64, "Invalid distribution SHA-256")
    manual = value["manual"]
    fields(manual, {"inkscape", "pilot", "performance"}, "manual acceptance")
    waived = set()
    for group, key in (("inkscape", "evidence"), ("pilot", "results"), ("performance", "reports")):
        record = manual[group]
        if schema == "2" and isinstance(record, dict) and record.get("status") == "waived":
            fields(record, {"status", "reason"}, group)
            nonblank(record["reason"], f"{group} waiver reason")
            waived.add(group)
            continue
        fields(record, {"status", key}, group)
        require(record["status"] == "passed", f"{group} acceptance is not passed")
        if group == "inkscape":
            evidence(record[key])
            continue
        records = record[key]
        require(isinstance(records, list) and len(records) == 3,
                f"{group} requires exactly three acceptance records")
        identities = set()
        for item in records:
            required = {"status", "evidence"} | ({"participant_id"} if group == "pilot" else set())
            fields(item, required, group)
            require(item["status"] == "passed", f"{group} record is not passed")
            evidence(item["evidence"])
            identity = item.get("participant_id", item["evidence"])
            require(isinstance(identity, str) and identity.strip() and identity not in identities,
                    f"{group} records must have distinct identities")
            identities.add(identity)
    if schema == "2":
        require(waived, "Schema 2 requires at least one explicit manual waiver")
        validate_authorization(value["release_owner_authorization"], version, waived)
    return value


def validate_run(run, manifest):
    require(run.get("id") == manifest["ci_run_id"], "CI run ID mismatch")
    require(run.get("repository", {}).get("full_name") == REPOSITORY
            and run.get("head_repository", {}).get("full_name") == REPOSITORY,
            "CI run must belong to this repository, not a fork")
    workflow_path = run.get("path")
    require(isinstance(workflow_path, str), "Unexpected candidate workflow")
    path, separator, ref = workflow_path.partition("@")
    require(path == WORKFLOW and (not separator or ref in {
        "main", "refs/heads/main", manifest["candidate_sha"]}), "Unexpected candidate workflow")
    require(run.get("event") in {"push", "workflow_dispatch"}
            and run.get("head_branch") == "main", "Untrusted candidate event or branch")
    require(run.get("head_sha") == manifest["candidate_sha"], "CI run commit mismatch")
    require(run.get("status") == "completed" and run.get("conclusion") == "success",
            "Candidate CI run has not completed successfully")


def validate_artifact(artifact, manifest):
    require(artifact.get("id") == manifest["artifact_id"]
            and artifact.get("name") == ARTIFACT_NAME, "Candidate artifact identity mismatch")
    require(artifact.get("expired") is False, "Candidate artifact is expired")
    run = artifact.get("workflow_run", {})
    require(run.get("id") == manifest["ci_run_id"]
            and run.get("head_sha") == manifest["candidate_sha"],
            "Artifact does not belong to the candidate run/commit")
    require(0 < artifact.get("size_in_bytes", 0) <= MAX_PACKAGE_BYTES,
            "Candidate artifact size is invalid")


def verify_metadata(body, kind, version):
    if kind == "wheel":
        with zipfile.ZipFile(io.BytesIO(body)) as archive:
            members = [m for m in archive.infolist() if m.filename.endswith(".dist-info/METADATA")]
            require(len(members) == 1 and members[0].file_size <= 1024 * 1024,
                    "Wheel must contain one bounded METADATA file")
            metadata = archive.read(members[0])
    else:
        with tarfile.open(fileobj=io.BytesIO(body), mode="r:gz") as archive:
            members = [m for m in archive if m.name.count("/") == 1
                       and m.name.endswith("/PKG-INFO")]
            require(len(members) == 1 and members[0].isfile() and members[0].size <= 1024 * 1024,
                    "Source distribution must contain one bounded PKG-INFO file")
            metadata = archive.extractfile(members[0]).read()
    parsed = BytesParser().parsebytes(metadata)
    require(len(parsed.get_all("Name", [])) == 1 and len(parsed.get_all("Version", [])) == 1,
            "Ambiguous package metadata")
    require(re.sub(r"[-_.]+", "-", parsed.get("Name", "")).lower() == "umap-art"
            and parsed.get("Version") == version, "Distribution package metadata mismatch")


def verified_distributions(body, manifest):
    require(len(body) <= MAX_PACKAGE_BYTES, "Candidate artifact is too large")
    result = {}
    with zipfile.ZipFile(io.BytesIO(body)) as archive:
        for kind, record in manifest["files"].items():
            expected = "dist/" + record["name"]
            members = [m for m in archive.infolist() if m.filename == expected]
            require(len(members) == 1 and members[0].file_size <= MAX_PACKAGE_BYTES,
                    f"Artifact must contain exactly one bounded {expected}")
            content = archive.read(members[0])
            require(hashlib.sha256(content).hexdigest() == record["sha256"],
                    f"Distribution hash mismatch: {record['name']}")
            verify_metadata(content, kind, manifest["version"])
            result[record["name"]] = content
    return result


def verified_download(directory, manifest):
    """Inspect the official download action's files without importing their code."""
    require(directory.is_dir() and not directory.is_symlink(), "Invalid download directory")
    dist = directory / "dist"
    require(dist.is_dir() and not dist.is_symlink()
            and dist.resolve().parent == directory.resolve(), "Invalid downloaded dist directory")
    expected = {record["name"] for record in manifest["files"].values()}
    members = list(dist.iterdir())
    require(len(members) == 2 and {path.name for path in members} == expected,
            "Downloaded dist must contain exactly the two accepted distributions")
    result = {}
    for kind, record in manifest["files"].items():
        path = dist / record["name"]
        require(path.is_file() and not path.is_symlink() and path.resolve().parent == dist.resolve()
                and path.stat().st_size <= MAX_PACKAGE_BYTES, "Invalid downloaded distribution")
        content = path.read_bytes()
        require(hashlib.sha256(content).hexdigest() == record["sha256"],
                f"Distribution hash mismatch: {record['name']}")
        verify_metadata(content, kind, manifest["version"])
        result[record["name"]] = content
    return result


class SafeRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        require(urllib.parse.urlsplit(newurl).scheme == "https", "Non-HTTPS download redirect")
        redirected = super().redirect_request(request, fp, code, msg, headers, newurl)
        if redirected is not None:
            redirected.remove_header("Authorization")
        return redirected


class GitHub:
    def __init__(self, token):
        require(bool(token), "GITHUB_TOKEN is required")
        self.token = token
        self.opener = urllib.request.build_opener(SafeRedirect())

    def read(self, path, *, binary=False, maximum=1024 * 1024):
        require(path.startswith(f"/repos/{REPOSITORY}/"), "Unexpected GitHub API path")
        request = urllib.request.Request(API + path, headers={
            "Authorization": "Bearer " + self.token, "User-Agent": "umap-release-check",
            "Accept": "application/octet-stream" if binary else "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        })
        with self.opener.open(request, timeout=30) as response:
            body = response.read(maximum + 1)
        require(len(body) <= maximum, "GitHub response exceeds its size limit")
        return body if binary else json.loads(body)


def collect_candidate(event, client, version, commit):
    require(event.get("repository", {}).get("full_name") == REPOSITORY
            and event.get("action") == "published", "Unexpected release event")
    release_id = event.get("release", {}).get("id")
    positive_id(release_id, "release ID")
    prefix = f"/repos/{REPOSITORY}"
    release = client.read(f"{prefix}/releases/{release_id}")
    require(release.get("id") == release_id and release.get("tag_name") == f"v{version}"
            and release.get("draft") is False
            and release.get("prerelease") is False, "Expected the published stable release")
    tag = client.read(f"{prefix}/git/ref/tags/v{version}")["object"]
    for _ in range(5):
        if tag.get("type") == "commit":
            break
        require(tag.get("type") == "tag" and re.fullmatch(r"[0-9a-f]{40}", tag.get("sha", "")),
                "Invalid annotated tag")
        tag = client.read(f"{prefix}/git/tags/{tag['sha']}")["object"]
    require(tag.get("type") == "commit" and tag.get("sha") == commit,
            "Remote release tag does not match checked-out commit")
    assets = client.read(f"{prefix}/releases/{release_id}/assets?per_page=100")
    matches = [a for a in assets if a.get("name") == "release-evidence.json"]
    require(len(matches) == 1, "Attach exactly one release-evidence.json to this release")
    asset = matches[0]
    positive_id(asset.get("id"), "evidence asset ID")
    require(0 < asset.get("size", 0) <= 256 * 1024, "Invalid evidence asset size")
    manifest = validate_manifest(json.loads(client.read(
        f"{prefix}/releases/assets/{asset['id']}", binary=True, maximum=256 * 1024)), version, commit)
    run = client.read(f"{prefix}/actions/runs/{manifest['ci_run_id']}")
    validate_run(run, manifest)
    candidates = client.read(
        f"{prefix}/actions/runs/{manifest['ci_run_id']}/artifacts?per_page=100")["artifacts"]
    matches = [a for a in candidates if a.get("id") == manifest["artifact_id"]]
    require(len(matches) == 1, "Artifact is not a member of the candidate CI run")
    validate_artifact(matches[0], manifest)
    return manifest


def write_outputs(path, manifest, files=None):
    if path is None:
        return
    hashes = ({name: hashlib.sha256(content).hexdigest() for name, content in files.items()}
              if files is not None else {
                  record["name"]: record["sha256"] for record in manifest["files"].values()})
    with path.open("a", encoding="utf-8") as outputs:
        outputs.write(f"run_id={manifest['ci_run_id']}\n")
        outputs.write(f"artifact_id={manifest['artifact_id']}\n")
        outputs.write("distributions=" + json.dumps(hashes, sort_keys=True) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--event", type=Path)
    mode.add_argument("--verify-download", type=Path)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--github-output", type=Path)
    args = parser.parse_args()
    try:
        root = Path(__file__).resolve().parents[1]
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root,
                                         text=True).strip()
        if args.event:
            require(args.output is None, "Use --output only with --verify-download")
            event = json.loads(args.event.read_text("utf-8"))
            version = check_release(root, event.get("release", {}).get("tag_name", ""))
            manifest = collect_candidate(event, GitHub(os.environ.get("GITHUB_TOKEN")),
                                         version, commit)
            require(not args.manifest.exists(), "Choose a new validated manifest path")
            args.manifest.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
            write_outputs(args.github_output, manifest)
            print(f"Verified candidate provenance for {version} at {commit}; download via action")
            return 0
        require(args.output is not None, "--verify-download requires --output")
        manifest = json.loads(args.manifest.read_text("utf-8"))
        version = check_release(root, f"v{manifest.get('version', '')}")
        validate_manifest(manifest, version, commit)
        files = verified_download(args.verify_download, manifest)
        require(not args.output.exists(), "Choose a new, empty promotion output directory")
        args.output.mkdir(parents=True)
        for name, content in files.items():
            (args.output / name).write_bytes(content)
            print(f"Accepted {name}: sha256={hashlib.sha256(content).hexdigest()}")
        write_outputs(args.github_output, manifest, files)
        print(f"Verified {len(files)} exact candidate distributions for {version} at {commit}")
        return 0
    except (ValueError, KeyError, TypeError, OSError, urllib.error.URLError,
            zipfile.BadZipFile, tarfile.TarError, subprocess.CalledProcessError) as exc:
        print(f"Candidate release validation failed: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
