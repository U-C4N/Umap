"""Release metadata gates must fail before an OIDC publishing job can run."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

MODULE_SPEC = importlib.util.spec_from_file_location(
    "check_release", Path(__file__).resolve().parents[1] / "scripts/check_release.py"
)
release = importlib.util.module_from_spec(MODULE_SPEC)
MODULE_SPEC.loader.exec_module(release)


@pytest.fixture
def project(tmp_path):
    (tmp_path / "pyproject.toml").write_text('[project]\nname="umap-art"\nversion="0.1.0"\n')
    package = tmp_path / "src/umap_art"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text('__version__ = "0.1.0"\n')
    return tmp_path


def test_matching_release_is_accepted(project):
    assert release.check_release(project, "v0.1.0") == "0.1.0"


@pytest.mark.parametrize("tag", ["", "main", "0.1.0", "v0.2.0", "v0.1.0\n"])
def test_unrelated_or_malformed_tag_is_rejected(project, tag):
    with pytest.raises(ValueError, match="Release tag"):
        release.check_release(project, tag)


def test_public_version_cannot_drift(project):
    (project / "src/umap_art/__init__.py").write_text('__version__ = "0.0.1"\n')
    with pytest.raises(ValueError, match="__version__"):
        release.check_release(project, "v0.1.0")


def test_renamed_package_requires_new_publisher_configuration(project):
    (project / "pyproject.toml").write_text('[project]\nname="another-package"\nversion="0.1.0"\n')
    with pytest.raises(ValueError, match="publisher"):
        release.check_release(project, "v0.1.0")


def test_checkout_and_lockfile_versions_match():
    import tomllib

    from umap_art import __version__

    root = Path(__file__).resolve().parents[1]
    assert release.check_release(root, f"v{__version__}") == __version__
    locked = tomllib.loads((root / "uv.lock").read_text("utf-8"))
    assert next(p for p in locked["package"] if p["name"] == "umap-art")["version"] == __version__
