# AGENTS.md

## Cursor Cloud specific instructions

### Overview

**Umap** (`umap-osm`) is a Python CLI tool and library for generating styled maps from OpenStreetMap data. It is a single-package Python project (not a monorepo, no web services, no databases).

### Running the application

- **CLI:** `umap Istanbul` or `umap --coords "48.8566,2.3522"` (see `umap --help`)
- **Python API:** `import umap; result = umap.plot("Istanbul")`
- When running headless (no display), set `matplotlib.use('Agg')` before importing umap's plot module, or use the CLI which handles this automatically.

### Build / Test / Lint

- **Install (dev):** `pip install -e ".[dev]"` (installs pytest, build, twine)
- **Build:** `python3 -m build`
- **Test:** `python3 -m pytest` — note: the repo currently has **no test files**, so pytest collects nothing.
- **Lint:** No linter is configured in the project.

### Non-obvious notes

- The `umap` CLI and scripts are installed to `~/.local/bin`. This path must be on `$PATH` (already added to `~/.bashrc` during setup).
- Map generation requires **internet access** to fetch data from the OpenStreetMap Overpass API and Nominatim geocoder. First runs for a location will be slower; subsequent runs use a local pickle cache.
- Warnings like `"Error fetching waterway data: No matching features"` are normal and non-fatal — they occur when the queried area has no waterways.
- The cache directory is `~/.umap_cache/` by default.
