"""Install a built wheel with binary dependencies, then verify it outside editable source.

CI: uv run python scripts/wheel_smoke.py --install dist --environment .cache/wheel-venv
Existing wheel environment: <python> -I scripts/wheel_smoke.py --verify --work-dir <scratch>
"""
from __future__ import annotations

import argparse
import asyncio
import importlib.metadata
import json
import os
import subprocess
import sys
import tarfile
import zipfile
from importlib.resources import files
from pathlib import Path


def inspect_distributions(directory: Path) -> Path:
    wheels = sorted(directory.glob("umap_art-*.whl"))
    sources = sorted(directory.glob("umap_art-*.tar.gz"))
    if len(wheels) != 1 or len(sources) != 1:
        raise RuntimeError("Build exactly one Umap wheel and source distribution before this check")
    needed = {"umap_art/assets/fonts/DejaVuSans.ttf", "umap_art/assets/fonts/LICENSE_DEJAVU",
              "umap_art/sources/overture.py", "umap_art/mcp_server.py", "umap_art/cli.py"}
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


def install_and_verify(directory: Path, environment: Path):
    repository = Path(__file__).resolve().parents[1]
    wheel = inspect_distributions(directory)
    environment = environment.resolve()
    if environment.exists():
        raise RuntimeError("Choose a new environment directory for the wheel installation check")
    scratch = repository / ".cache"
    scratch.mkdir(exist_ok=True)
    requirements = scratch / "wheel-runtime-requirements.txt"
    subprocess.run(["uv", "export", "--frozen", "--all-extras", "--no-dev", "--no-emit-project",
                    "--output-file", str(requirements)], cwd=repository, check=True,
                   stdout=subprocess.DEVNULL)
    subprocess.run(["uv", "venv", str(environment), "--python", sys.executable], check=True)
    python = environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    # --only-binary enforces that users need no native compiler on each CI platform.
    subprocess.run(["uv", "pip", "install", "--python", str(python), "--only-binary", ":all:",
                    "-r", str(requirements), str(wheel) + "[mcp]"], check=True)
    subprocess.run([str(python), "-I", str(Path(__file__).resolve()), "--verify", "--work-dir",
                    str(scratch / "wheel-output"), "--result", str(scratch / "wheel-smoke-result.json")],
                   cwd=scratch, check=True)


def verify_installed(work_dir: Path) -> dict:
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
    work_dir = work_dir.resolve()
    work_dir.mkdir(parents=True, exist_ok=True)
    os.environ["UMAP_CACHE_DIR"] = str(work_dir / "cache")
    spec = MapSpec(area={"center": [29.025, 40.985]}, page={"size": "A4", "dpi": 72},
                   formats=["svg", "png", "pdf"], title="İstanbul — Çığ / Iİıi")
    extent = compute_extent(spec)
    data = Dataset(bbox=extent.bbox, sources=[{"provider": "synthetic", "license": "CC0"}], features=[
        Feature(id="wheel-building", layer="buildings", geometry=mapping(box(29.024, 40.984, 29.025, 40.985))),
        Feature(id="wheel-road", layer="roads", geometry=mapping(LineString([(29.022, 40.983), (29.028, 40.986)])),
                properties={"highway": "primary"}),
    ])
    snapshot = work_dir / "snapshot.json"
    atomic_json(snapshot, {"schema_version": "1", "dataset_id": digest(data.model_dump(mode="json")),
                           "dataset": data.model_dump(mode="json")})
    spec.source.snapshot, spec.source.offline = str(snapshot), True
    result = render(spec, output_dir=work_dir / "python")
    assert {artifact.mime_type for artifact in result.artifacts} >= {"image/png", "image/svg+xml", "application/pdf"}
    recipe = work_dir / "recipe.json"
    recipe.write_text(spec.model_dump_json(), encoding="utf-8")
    command = subprocess.run([sys.executable, "-I", "-m", "umap_art", "render", str(recipe),
                              "--output", str(work_dir / "cli"), "--json"], cwd=work_dir,
                             capture_output=True, text=True, encoding="utf-8", timeout=90)
    assert command.returncode == 0, command.stderr
    assert json.loads(command.stdout)["scene_hashes"] == result.scene_hashes
    doctor = subprocess.run([sys.executable, "-I", "-m", "umap_art", "doctor", "--json"],
                            capture_output=True, text=True, encoding="utf-8", timeout=45)
    assert doctor.returncode == 0, doctor.stderr
    dependencies = json.loads(doctor.stdout)
    assert dependencies["mcp_installed"]

    async def stdio():
        from mcp.client import Client
        from mcp.client.stdio import StdioServerParameters

        params = StdioServerParameters(command=sys.executable, args=["-I", "-m", "umap_art", "mcp",
                                       "--workspace", str(work_dir / "mcp")], env=dict(os.environ))
        async with asyncio.timeout(30):
            async with Client(params, read_timeout_seconds=20) as client:
                tools = await client.list_tools()
                assert len(tools.tools) == 10
                response = await client.call_tool("list_styles")
                assert not response.is_error
                assert len(response.structured_content["styles"]) == 2

    asyncio.run(stdio())
    return {"passed": True, "python": sys.version, "installed_package": str(installation),
            "version": importlib.metadata.version("umap-art"), "scene_hashes": result.scene_hashes,
            "dependencies": dependencies, "checks": ["font_and_license", "offline_svg_png_pdf", "cli_equivalence", "mcp_stdio"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--install", type=Path, help="Directory containing built distributions")
    mode.add_argument("--verify", action="store_true", help="Verify the package installed in this interpreter")
    parser.add_argument("--environment", type=Path, default=Path(".cache/wheel-venv"))
    parser.add_argument("--work-dir", type=Path, default=Path(".cache/wheel-output"))
    parser.add_argument("--result", type=Path)
    args = parser.parse_args()
    if args.install:
        install_and_verify(args.install, args.environment)
    else:
        result = verify_installed(args.work_dir)
        text = json.dumps(result, ensure_ascii=False, indent=2)
        if args.result:
            args.result.parent.mkdir(parents=True, exist_ok=True)
            args.result.write_text(text, encoding="utf-8")
        print(text)


if __name__ == "__main__":
    main()
