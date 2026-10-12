import pytest


@pytest.fixture(autouse=True)
def isolated_cache(tmp_path, monkeypatch):
    monkeypatch.setenv("UMAP_CACHE_DIR", str(tmp_path / "cache"))


def pytest_addoption(parser):
    parser.addoption(
        "--live", action="store_true", default=False, help="Allow requests to real public services"
    )


def pytest_collection_modifyitems(config, items):
    if not config.getoption("--live"):
        skip = pytest.mark.skip(reason="Live service requests require --live")
        for item in items:
            if "live" in item.keywords:
                item.add_marker(skip)
