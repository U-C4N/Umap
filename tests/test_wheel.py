"""Packaging contracts also run against installed distributions in wheel_smoke.py."""
from __future__ import annotations

import json
import subprocess
import sys
from importlib.resources import files


def test_bundled_font_has_redistribution_notice():
    assets = files("umap_art").joinpath("assets/fonts")
    assert len(assets.joinpath("DejaVuSans.ttf").read_bytes()) > 100_000
    notice = assets.joinpath("LICENSE_DEJAVU").read_text(encoding="utf-8")
    assert "Bitstream" in notice and "Permission" in notice


def test_basic_python_import_does_not_load_optional_mcp():
    command = subprocess.run([sys.executable, "-c", "import json,sys,umap_art; print(json.dumps({"
                              "'mcp_loaded': any(m == 'mcp' or m.startswith('mcp.') for m in sys.modules),"
                              "'public': sorted(umap_art.__all__)}))"],
                             capture_output=True, text=True, encoding="utf-8", timeout=15)
    assert command.returncode == 0, command.stderr
    value = json.loads(command.stdout)
    assert not value["mcp_loaded"]
    assert value["public"] == ["MapSpec", "RenderResult", "render"]
