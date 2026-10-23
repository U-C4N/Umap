"""Terminal adapter for the shared map service."""

from __future__ import annotations

import argparse
import importlib.metadata
import importlib.util
import json
import sys
from pathlib import Path

from pydantic import ValidationError

from .errors import UmapError
from .models import MapSpec, validate_spec


def _emit(value, as_json=True):
    print(json.dumps(value, ensure_ascii=False, indent=2))


def parser():
    from .demo import PRESETS
    from .styles import THEMES

    root = argparse.ArgumentParser(prog="umap-art", description="Keyless, editable map artwork")
    root.add_argument("--version", action="version", version=importlib.metadata.version("umap-art"))
    commands = root.add_subparsers(dest="command", required=True)
    for name in ("render", "refresh"):
        p = commands.add_parser(
            name,
            help="Render a saved recipe" if name == "render" else "Explicitly refresh map data",
        )
        p.add_argument("recipe", type=Path)
        p.add_argument("--output", type=Path, default=Path("outputs"))
        p.add_argument("--json", action="store_true")
    p = commands.add_parser("demo", help="Render a bundled Kadıköy example completely offline")
    p.add_argument("--preset", choices=PRESETS, default="poster")
    p.add_argument("--theme", choices=THEMES, help="Override the preset's theme")
    p.add_argument("--output", type=Path, default=Path("outputs"))
    p.add_argument("--json", action="store_true")
    p = commands.add_parser("locations", help="Find place candidates")
    p.add_argument("query")
    p.add_argument("--country-code")
    p.add_argument("--json", action="store_true")
    p = commands.add_parser("styles", help="List themes, layouts and editable fields")
    p.add_argument("--json", action="store_true")
    p = commands.add_parser("inspect", help="Inspect a recipe or output manifest")
    p.add_argument("path", type=Path)
    p.add_argument("--json", action="store_true")
    p = commands.add_parser("doctor", help="Check installed runtime dependencies")
    p.add_argument("--json", action="store_true")
    p = commands.add_parser("mcp", help="Start the optional local MCP server")
    p.add_argument("--workspace", type=Path, required=True)
    p.add_argument("--photon-url")
    p.add_argument("--overpass-url")
    p.add_argument("--overture-catalog-url")
    p = commands.add_parser("schema", help="Print the recipe JSON Schema")
    p.add_argument("--json", action="store_true")
    return root


def main(argv=None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    args = parser().parse_args(argv)
    try:
        if args.command in ("render", "refresh", "demo"):
            if args.command == "demo":
                from .demo import render_demo

                print("Rendering bundled Kadıköy data offline…", file=sys.stderr)
                result = render_demo(args.preset, theme=args.theme, output_dir=args.output)
            else:
                from .service import render

                print("Preparing map and outputs…", file=sys.stderr)
                result = render(args.recipe, output_dir=args.output, refresh=args.command == "refresh")
            if args.json:
                _emit(result.model_dump(mode="json"))
            elif args.command == "demo":
                print("Demo complete. Open a PNG preview or edit the SVG artwork:")
                labels = {"image/png": "Preview", "image/svg+xml": "SVG", "application/pdf": "PDF"}
                for artifact in result.artifacts:
                    if artifact.mime_type in labels:
                        print(f"{labels[artifact.mime_type]}: {Path(artifact.path).resolve()}")
                print(f"Recipe: {Path(result.recipe_path).resolve()}")
                print(f"Project: {Path(result.recipe_path).resolve().parent}")
            else:
                for a in result.artifacts:
                    print(a.path)
            for d in result.diagnostics:
                print(f"{d.severity}: {d.code}: {d.message}", file=sys.stderr)
        elif args.command == "locations":
            from .sources import find_locations

            _emit(find_locations(args.query, country_code=args.country_code))
        elif args.command == "styles":
            from .styles import list_styles

            _emit(list_styles())
        elif args.command == "inspect":
            value = json.loads(args.path.read_text(encoding="utf-8"))
            if "area" in value:
                spec = validate_spec(value)
                _emit({"kind": "recipe", "spec": spec.model_dump(mode="json")})
            else:
                _emit(value)
        elif args.command == "schema":
            _emit(MapSpec.model_json_schema())
        elif args.command == "doctor":
            imports = {
                "pydantic": "pydantic",
                "httpx": "httpx",
                "shapely": "shapely",
                "pyproj": "pyproj",
                "matplotlib": "matplotlib",
                "osmium": "osmium",
                "pyarrow": "pyarrow",
            }
            checks = {}
            for distribution, module in imports.items():
                try:
                    __import__(module)
                    checks[distribution] = {
                        "ok": True,
                        "version": importlib.metadata.version(distribution),
                    }
                except Exception as exc:
                    checks[distribution] = {"ok": False, "error": str(exc)}
            _emit(
                {
                    "python": sys.version,
                    "dependencies": checks,
                    "mcp_installed": importlib.util.find_spec("mcp") is not None,
                }
            )
            return 0 if all(c["ok"] for c in checks.values()) else 1
        elif args.command == "mcp":
            if importlib.util.find_spec("mcp") is None:
                raise UmapError(
                    "MCP_NOT_INSTALLED", "Install the MCP extra: pip install 'umap-art[mcp]'"
                )
            from .mcp_server import run_server

            urls = {
                k: getattr(args, k)
                for k in ("photon_url", "overpass_url", "overture_catalog_url")
                if getattr(args, k)
            }
            run_server(args.workspace, provider_urls=urls or None)
        return 0
    except UmapError as exc:
        print(json.dumps({"error": exc.to_dict()}, ensure_ascii=False), file=sys.stderr)
        return 2
    except (ValidationError, ValueError, OSError) as exc:
        print(
            json.dumps(
                {"error": {"code": "INVALID_INPUT", "message": str(exc)}}, ensure_ascii=False
            ),
            file=sys.stderr,
        )
        return 2
    except KeyboardInterrupt:
        print("Cancelled", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
