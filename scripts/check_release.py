"""Reject a release tag that does not identify the code's exact package version."""

from __future__ import annotations

import ast
import os
import tomllib
from pathlib import Path


def check_release(root: Path, tag: str) -> str:
    project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    version = project["version"]
    if project["name"] != "umap-art":
        raise ValueError("The PyPI publisher is configured only for umap-art")
    if tag != f"v{version}":
        raise ValueError(f"Release tag {tag!r} must be v{version}")
    tree = ast.parse((root / "src/umap_art/__init__.py").read_text(encoding="utf-8"))
    public_version = next(
        (
            ast.literal_eval(node.value)
            for node in tree.body
            if isinstance(node, ast.Assign)
            and any(
                isinstance(target, ast.Name) and target.id == "__version__"
                for target in node.targets
            )
        ),
        None,
    )
    if public_version != version:
        raise ValueError("The public __version__ must match pyproject.toml before releasing")
    return version


def main() -> int:
    try:
        version = check_release(
            Path(__file__).resolve().parents[1], os.environ.get("RELEASE_TAG", "")
        )
    except (ValueError, KeyError, OSError) as exc:
        print(f"Release validation failed: {exc}")
        return 1
    print(f"Validated umap-art {version}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
