"""Install a built wheel with binary dependencies, then verify it outside editable source.

CI: uv run python scripts/wheel_smoke.py --install dist --environment .cache/wheel-venv
Existing wheel environment: <python> -I scripts/wheel_smoke.py --verify --work-dir <scratch>
"""
from __future__ import annotations

import argparse
import asyncio
import base64
import hashlib
import importlib.metadata
import importlib.util
import json
import os
import runpy
import shutil
import subprocess
import sys
import tarfile
import tempfile
import uuid
import zipfile
from importlib.resources import files
from pathlib import Path


def inspect_distributions(directory: Path) -> Path:
    wheels = sorted(directory.glob("umap_art-*.whl"))
    sources = sorted(directory.glob("umap_art-*.tar.gz"))
    if len(wheels) != 1 or len(sources) != 1:
        raise RuntimeError("Build exactly one Umap wheel and source distribution before this check")
    needed = {"umap_art/assets/fonts/DejaVuSans.ttf", "umap_art/assets/fonts/LICENSE_DEJAVU",
              "umap_art/sources/overture.py", "umap_art/mcp_server.py", "umap_art/cli.py",
              "umap_art/demo.py", *("umap_art/examples/kadikoy/" + name for name in
                ("poster.json", "guide.json", "atlas.json", "snapshot.json", "DATA-LICENSES.txt"))}
    with zipfile.ZipFile(wheels[0]) as archive:
        names = set(archive.namelist())
        if not needed <= names:
            raise RuntimeError(f"Wheel is missing files: {sorted(needed - names)}")
        metadata_files = [name for name in names if name.endswith(".dist-info/METADATA")]
        if len(metadata_files) != 1 or b"License-Expression: MIT" not in archive.read(metadata_files[0]):
            raise RuntimeError("Wheel MIT license metadata is missing")
        if not any(name.endswith(".dist-info/licenses/LICENSE") for name in names):
            raise RuntimeError("Wheel does not include the code license")
    with tarfile.open(sources[0], "r:gz") as archive:
        names = {name.split("/", 1)[1] for name in archive.getnames() if "/" in name}
        required = {"pyproject.toml", "README.md", "LICENSE", *("src/" + name for name in needed)}
        if not required <= names:
            raise RuntimeError(f"Source distribution is missing files: {sorted(required - names)}")
    return wheels[0].resolve()


def install_and_verify(directory: Path, environment: Path, *, plain=False, from_sdist=False,
                       result_path: Path | None = None):
    repository = Path(__file__).resolve().parents[1]
    wheel = inspect_distributions(directory)
    environment = environment.resolve()
    if environment.exists():
        raise RuntimeError("Choose a new environment directory for the wheel installation check")
    scratch = repository / ".cache"
    scratch.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="umap-sdist-") as temporary:
        if from_sdist:
            source = next(directory.glob("umap_art-*.tar.gz")).resolve()
            extracted = Path(temporary) / "source"
            extracted.mkdir()
            with tarfile.open(source, "r:gz") as archive:
                archive.extractall(extracted, filter="data")
            projects = [p for p in extracted.iterdir() if (p / "pyproject.toml").is_file()]
            if len(projects) != 1:
                raise RuntimeError("Source distribution must contain exactly one project")
            built = Path(temporary) / "dist"
            subprocess.run(["uv", "build", "--wheel", "--no-sources", "--out-dir", str(built)],
                           cwd=projects[0], check=True)
            wheels = list(built.glob("*.whl"))
            if len(wheels) != 1:
                raise RuntimeError("Source build must produce exactly one wheel")
            wheel = wheels[0]
        python = environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        if plain:
            # Resolve from wheel metadata alone, without preinstalling lockfile dependencies.
            subprocess.run([sys.executable, "-m", "venv", str(environment)], check=True)
            subprocess.run([str(python), "-m", "pip", "install", "--only-binary", ":all:",
                            str(wheel)], cwd=temporary, check=True)
        else:
            requirements = Path(temporary) / "requirements.txt"
            subprocess.run(["uv", "export", "--frozen", "--all-extras", "--no-dev",
                            "--no-emit-project", "--output-file", str(requirements)],
                           cwd=repository, check=True, stdout=subprocess.DEVNULL)
            subprocess.run(["uv", "venv", str(environment), "--python", sys.executable], check=True)
            subprocess.run(["uv", "pip", "install", "--python", str(python), "--only-binary",
                            ":all:", "-r", str(requirements), str(wheel) + "[mcp]"], check=True)
        command = [str(python), "-I", str(Path(__file__).resolve()), "--verify", "--work-dir",
                   str(scratch / (environment.name + "-output")), "--result",
                   str((result_path or scratch / "wheel-smoke-result.json").resolve())]
        if plain:
            command.append("--core-only")
        subprocess.run(command, cwd=temporary, check=True)


NETWORK_GUARD = '''\
import ipaddress
import json
import os
import socket
import sys

def _local(host):
    if host is None or host in ("localhost", b"localhost"):
        return True
    try:
        if isinstance(host, bytes):
            host = host.decode("ascii")
        return ipaddress.ip_address(host.split("%")[0]).is_loopback
    except (ValueError, AttributeError, UnicodeError):
        return False

def _wrap_connect(original):
    def guarded(sock, address, *args, **kwargs):
        if sock.family in (socket.AF_INET, socket.AF_INET6) and not _local(address[0]):
            raise RuntimeError("Wheel smoke: external networking disabled")
        return original(sock, address, *args, **kwargs)
    return guarded

socket.socket.connect = _wrap_connect(socket.socket.connect)
socket.socket.connect_ex = _wrap_connect(socket.socket.connect_ex)
_original_lookup = socket.getaddrinfo
def _lookup(host, *args, **kwargs):
    if not _local(host):
        raise RuntimeError("Wheel smoke: external DNS disabled")
    return _original_lookup(host, *args, **kwargs)
socket.getaddrinfo = _lookup
# Prove the guard runs in every process, without sending a packet.
with socket.socket() as probe:
    try:
        probe.connect(("192.0.2.1", 9))
    except RuntimeError:
        pass
    else:
        raise RuntimeError("External network guard failed")
with open(os.environ["UMAP_SMOKE_GUARD_LOG"], "a", encoding="utf-8") as log:
    log.write(json.dumps({"pid": os.getpid(), "parent_pid": os.getppid(),
                          "argv": sys.argv, "external_probe_blocked": True}) + "\\n")
'''


def guarded_arguments(*args):
    # -I ignores PYTHONPATH. Explicitly install the same guard in the stdio/CLI parent;
    # normal worker subprocesses inherit the guard-only PYTHONPATH/sitecustomize.
    return ["-I", "-c", "import os,runpy; runpy.run_path(os.environ['UMAP_SMOKE_GUARD']); "
            "runpy.run_module('umap_art',run_name='__main__')", *args]


def cli_json(work_dir: Path, *args):
    command = subprocess.run([sys.executable, *guarded_arguments(*map(str, args))],
                             cwd=work_dir, capture_output=True, text=True,
                             encoding="utf-8", timeout=240)
    if command.returncode:
        raise RuntimeError(f"Installed CLI failed: {command.stderr}")
    return json.loads(command.stdout)


def verify_installed(work_dir: Path, *, core_only=False) -> dict:
    from shapely.geometry import LineString, box, mapping

    import umap_art
    from umap_art import MapSpec, render
    from umap_art.geometry import compute_extent
    from umap_art.models import Dataset, Feature
    from umap_art.storage import atomic_json, digest

    installation = Path(umap_art.__file__).resolve()
    if not installation.is_relative_to(Path(sys.prefix).resolve()):
        raise RuntimeError(f"Umap was imported from source instead of the wheel: {installation}")
    package = files("umap_art")
    assert len(package.joinpath("assets/fonts/DejaVuSans.ttf").read_bytes()) > 100_000
    assert "Bitstream" in package.joinpath("assets/fonts/LICENSE_DEJAVU").read_text(encoding="utf-8")
    work_dir = work_dir.resolve() / uuid.uuid4().hex
    work_dir.mkdir(parents=True, exist_ok=True)
    os.environ["UMAP_CACHE_DIR"] = str(work_dir / "cache")
    guard = work_dir / "network-guard"
    guard.mkdir()
    guard_path = guard / "sitecustomize.py"
    guard_path.write_text(NETWORK_GUARD, encoding="utf-8")
    os.environ["UMAP_SMOKE_GUARD"] = str(guard_path)
    os.environ["UMAP_SMOKE_GUARD_LOG"] = str(work_dir / "network-guard.jsonl")
    os.environ["PYTHONPATH"] = str(guard)
    # Localhost remains available for asyncio IPC, but must not proxy external HTTP.
    for name in list(os.environ):
        if name.lower() in {"http_proxy", "https_proxy", "all_proxy"}:
            os.environ.pop(name)
    runpy.run_path(str(guard_path))
    demos = {}
    for preset in ("poster", "guide", "atlas"):
        demo = cli_json(work_dir, "demo", "--preset", preset, "--output",
                        work_dir / "demo" / preset, "--json")
        expected = {"figure_ground", "roads", "green", "water"} if preset == "atlas" else {"general"}
        assert set(demo["scene_hashes"]) == expected
        assert {a["mime_type"] for a in demo["artifacts"]} >= {
            "image/png", "image/svg+xml", "application/pdf"}
        relocated = work_dir / "relocated" / preset
        shutil.copytree(Path(demo["recipe_path"]).parent, relocated)
        assert not (relocated / "assets" / "demo").exists()
        assert not (relocated / "assets" / "examples").exists()
        again = cli_json(work_dir, "render", relocated / "recipe.json", "--output",
                         work_dir / "reproduced" / preset, "--json")
        assert again["scene_hashes"] == demo["scene_hashes"]
        assert again["dataset_id"] == demo["dataset_id"]
        demos[preset] = {"dataset_id": demo["dataset_id"], "scene_hashes": demo["scene_hashes"]}
    assert len({d["dataset_id"] for d in demos.values()}) == 1
    spec = MapSpec(area={"center": [29.025, 40.985]}, page={"size": "A4", "dpi": 72, "layout": "guide"},
                   style={"theme": "neon"}, places=[{
                       "id": "selected", "label": "Çığ / Iİıi", "coordinates": [29.025, 40.985]}],
                   formats=["svg", "png", "pdf"], title="İstanbul — Çığ / Iİıi")
    extent = compute_extent(spec)
    data = Dataset(bbox=extent.bbox, sources=[{"provider": "synthetic", "license": "CC0"}], features=[
        Feature(id="wheel-building", layer="buildings", geometry=mapping(box(29.024, 40.984, 29.025, 40.985))),
        Feature(id="wheel-road", layer="roads", geometry=mapping(LineString([(29.022, 40.983), (29.028, 40.986)])),
                properties={"highway": "primary"}),
    ])
    mcp_workspace = work_dir / "mcp"
    mcp_workspace.mkdir()
    snapshot = mcp_workspace / "snapshot.json"
    atomic_json(snapshot, {"schema_version": "1", "dataset_id": digest(data.model_dump(mode="json")),
                           "dataset": data.model_dump(mode="json")})
    spec.source.snapshot, spec.source.offline = str(snapshot), True
    result = render(spec, output_dir=work_dir / "python")
    assert {artifact.mime_type for artifact in result.artifacts} >= {"image/png", "image/svg+xml", "application/pdf"}
    recipe = work_dir / "recipe.json"
    recipe.write_text(spec.model_dump_json(), encoding="utf-8")
    cli = cli_json(work_dir, "render", recipe, "--output", work_dir / "cli", "--json")
    assert cli["scene_hashes"] == result.scene_hashes
    dependencies = cli_json(work_dir, "doctor", "--json")
    assert dependencies["mcp_installed"] is (not core_only)

    async def stdio():
        from mcp.client import Client
        from mcp.client.stdio import StdioServerParameters

        before_guard = Path(os.environ["UMAP_SMOKE_GUARD_LOG"]).read_text("utf-8").splitlines()
        params = StdioServerParameters(command=sys.executable,
            args=guarded_arguments("mcp", "--workspace", str(mcp_workspace)), env=dict(os.environ))
        async with asyncio.timeout(180):
            async with Client(params, read_timeout_seconds=30) as client:
                async def call(name, arguments=None):
                    response = await client.call_tool(name, arguments or {})
                    assert not response.is_error, response
                    return response.structured_content

                async def completed(job_id):
                    for _ in range(600):
                        job = await call("get_job", {"job_id": job_id})
                        if job["state"] in ("succeeded", "failed", "cancelled", "interrupted"):
                            assert job["state"] == "succeeded", job
                            return job
                        await asyncio.sleep(0.1)
                    raise RuntimeError("Installed MCP job did not finish")

                tools = await client.list_tools()
                assert len(tools.tools) == 10
                assert len((await call("list_styles"))["styles"]) == 6
                created = await call("create_map", {"spec": spec.model_dump(mode="json")})
                first = await completed(created["job_id"])
                assert first["result"]["scene_hashes"] == result.scene_hashes
                edited = await call("edit_map", {"map_id": created["map_id"], "base_revision": 1,
                    "changes": {"title": "Kadıköy — düzenlendi", "style": {"theme": "blueprint"}}})
                changed = await completed(edited["job_id"])
                assert changed["result"]["dataset_id"] == result.dataset_id
                assert changed["result"]["scene_hashes"] != result.scene_hashes
                exported = await call("render_map", {"map_id": created["map_id"],
                    "revision": 2, "formats": ["png", "svg", "pdf"]})
                final = await completed(exported["job_id"])
                artifact = next(a for a in final["artifacts"] if a["mime_type"] == "image/png")
                metadata = await call("get_artifact", {"artifact_id": artifact["artifact_id"]})
                resource = await client.read_resource(metadata["uri"])
                payload = base64.b64decode(resource.contents[0].blob)
                assert hashlib.sha256(payload).hexdigest() == metadata["sha256"]
        log = Path(os.environ["UMAP_SMOKE_GUARD_LOG"]).read_text("utf-8").splitlines()
        guarded = [json.loads(line) for line in log[len(before_guard):]]
        assert len({row["pid"] for row in guarded}) >= 4, "Guard missing in MCP workers"
        return {"guarded_processes": guarded, "revision": 2, "artifact_hash_verified": True}

    mcp_result = None if core_only else asyncio.run(stdio())
    return {"passed": True, "python": sys.version, "installed_package": str(installation),
            "version": importlib.metadata.version("umap-art"), "scene_hashes": result.scene_hashes,
            "dependencies": dependencies, "demos": demos, "mcp": mcp_result,
            "core_only": core_only, "network_guard_log": os.environ["UMAP_SMOKE_GUARD_LOG"],
            "network_guard_processes": [json.loads(line) for line in
                Path(os.environ["UMAP_SMOKE_GUARD_LOG"]).read_text("utf-8").splitlines()],
            "checks": ["font_and_license", "offline_presets", "portable_reproduction",
                       "offline_poster_svg_png_pdf", "cli_equivalence"] +
                      ([] if core_only else ["mcp_stdio_render_edit_export_artifact"])}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--install", type=Path, help="Directory containing built distributions")
    mode.add_argument("--verify", action="store_true", help="Verify the package installed in this interpreter")
    parser.add_argument("--environment", type=Path, default=Path(".cache/wheel-venv"))
    parser.add_argument("--work-dir", type=Path, default=Path(".cache/wheel-output"))
    parser.add_argument("--result", type=Path)
    install_mode = parser.add_mutually_exclusive_group()
    install_mode.add_argument("--plain-install", action="store_true",
                              help="Install only the core wheel using pip and its metadata")
    install_mode.add_argument("--from-sdist", action="store_true",
                              help="Build the sdist outside the checkout before installation")
    parser.add_argument("--core-only", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    result_path = args.result or (
        Path(__file__).resolve().parents[1] / ".cache/wheel-smoke-result.json" if args.install else None
    )

    def record(value):
        if result_path:
            result_path.parent.mkdir(parents=True, exist_ok=True)
            temporary = result_path.with_suffix(".tmp")
            temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
            temporary.replace(result_path)

    # Never leave an earlier successful report behind when installation or verification fails.
    record({"passed": False, "status": "running"})
    try:
        if args.install:
            install_and_verify(args.install, args.environment, plain=args.plain_install,
                               from_sdist=args.from_sdist, result_path=result_path)
        else:
            result = verify_installed(args.work_dir, core_only=args.core_only)
            record(result)
            print(json.dumps(result, ensure_ascii=False, indent=2))
    except Exception as exc:
        record({"passed": False, "status": "failed", "error": str(exc)})
        raise


if __name__ == "__main__":
    main()
