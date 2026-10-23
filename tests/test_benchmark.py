"""A release performance gate must fail on measured regressions."""
import importlib.util
import json
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    "benchmark", Path(__file__).resolve().parents[1] / "scripts/benchmark.py"
)
benchmark = importlib.util.module_from_spec(spec)
spec.loader.exec_module(benchmark)


@pytest.mark.parametrize("elapsed,memory,target,passed", [
    (30, 2048, 30, True), (30.01, 2048, 30, False),
    (1, 2049, 5, False), (100, 2048, None, True), (1, 2049, None, False),
])
def test_performance_gate_checks_time_and_memory(elapsed, memory, target, passed):
    record = {"elapsed_seconds": elapsed, "peak_rss_bytes": memory,
              "targets": {"elapsed_seconds": target, "peak_rss_bytes": 2048}}
    assert benchmark.meets_targets([record]) is passed


def test_empty_benchmark_is_not_a_pass():
    assert not benchmark.meets_targets([])


@pytest.mark.parametrize("check,exit_code", [(True, 1), (False, 0)])
def test_failed_threshold_keeps_report_and_changes_check_exit(tmp_path, monkeypatch, check, exit_code):
    from umap_art import MapSpec

    monkeypatch.setattr(benchmark, "synthetic_snapshot", lambda _: (
        MapSpec(area={"center": [29.025, 40.985]}), {"fixture_version": "test"}))

    def failed_measure(name, spec, output_dir, time_target=None):
        return {"phase": name, "elapsed_seconds": 40, "peak_rss_bytes": 3 * 1024**3,
                "targets": {"elapsed_seconds": time_target, "peak_rss_bytes": 2 * 1024**3},
                "scene_hashes": {"general": name}}

    monkeypatch.setattr(benchmark, "measure", failed_measure)
    argv = ["--output", str(tmp_path)] + (["--check"] if check else [])
    assert benchmark.main(argv) == exit_code
    latest = json.loads((tmp_path / "latest.json").read_text("utf-8"))
    report = json.loads(Path(latest["report"]).read_text("utf-8"))
    assert report["meets_targets"] is False
    assert len(report["phases"]) == 6
