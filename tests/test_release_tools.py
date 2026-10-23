"""Failures in a repeated packaging check must not retain old passing evidence."""
import json
import subprocess
import sys
from pathlib import Path


def test_failed_wheel_check_replaces_previous_success(tmp_path):
    result = tmp_path / "result.json"
    result.write_text('{"passed": true}', encoding="utf-8")
    script = Path(__file__).resolve().parents[1] / "scripts/wheel_smoke.py"
    failed = subprocess.run([sys.executable, str(script), "--install", str(tmp_path / "missing"),
                             "--result", str(result)], capture_output=True, timeout=20)
    assert failed.returncode != 0
    recorded = json.loads(result.read_text("utf-8"))
    assert recorded["passed"] is False
    assert recorded["status"] == "failed"
