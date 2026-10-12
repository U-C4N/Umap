# Umap Art

Editable, physically scaled map artwork from free, keyless online data — in Python,
from a terminal, or through a local MCP server.

Umap owns its source adapters, geometry pipeline, declarative styles and scene model.
It uses Shapely, pyproj and Matplotlib as infrastructure. Prettymaps, OSMnx, QGIS and
GDAL are not runtime dependencies.

## Install

Python 3.12–3.14 is supported by the CI matrix. The development environment was
tested on Windows x64/Python 3.14. Public services can be slow or unavailable;
there is no API key, account, or paid-service fallback.

After the first successful PyPI release, install the published package with:

```sh
python -m pip install umap-art
# Include the optional MCP adapter:
python -m pip install "umap-art[mcp]"
umap-art doctor
```

Until that release is published, install from this checkout:

```sh
python -m pip install .
# Include the optional MCP adapter:
python -m pip install '.[mcp]'
umap-art doctor
```

For development, install [uv](https://docs.astral.sh/uv/) and run `uv sync --all-extras`.
The distribution is `umap-art`; the Python import is `umap_art`.
Maintainers can publish from a GitHub release using
[the PyPI publishing guide](https://github.com/U-C4N/Umap/blob/main/docs/publishing.md).

## Make a map

From the repository checkout, these example recipes are ready to run:

```sh
umap-art render examples/kadikoy.json --output outputs
umap-art render examples/architecture-atlas.json --output outputs
```

The first command produces an A3 Kadıköy map as PNG, editable SVG and vector PDF.
The second produces four separate, aligned pages: buildings, roads, green and water.
The recipe files are in the repository's
[examples directory](https://github.com/U-C4N/Umap/tree/main/examples); they are not
installed as working-directory files by pip. The Python example below works with
either installation method.
Each run creates its own directory with a recipe, verified dataset snapshot, source
manifest, bundled font/license and portable `project.zip`.

```python
from umap_art import MapSpec, render

spec = MapSpec(
    area={"center": [29.025, 40.985], "scale_denominator": 5000},
    title="Kadıköy",
    subtitle="İstanbul",
    style={"theme": "city_poster"},
    page={"size": "A3", "orientation": "landscape", "dpi": 300},
)
result = render(spec, output_dir="outputs")
print(result.recipe_path)
```

Coordinates are always **longitude, latitude**. To choose a place by name, run
`umap-art locations "Kadıköy, İstanbul"` and use the selected candidate's coordinates.
`area.place` is also accepted; an ambiguous search returns candidates instead of
silently choosing the first result.

## Edit without downloading again

```python
from pathlib import Path
from umap_art import MapSpec, render

# `result` is the RenderResult returned by the previous example.
recipe = Path(result.recipe_path)
spec = MapSpec.model_validate_json(recipe.read_text(encoding="utf-8"))
spec.source.snapshot = str(recipe.parent / spec.source.snapshot)
spec.style.layers["roads"] = {"stroke": "#B34A44", "width_mm": 0.4}
changed = render(spec, output_dir="outputs")
```

Saved recipes default to `offline: true`. Run `umap-art render` with the saved
recipe path to resolve its relative snapshot automatically. `umap-art refresh`
explicitly acquires fresh data into a new output directory. Changing source
selection or enlarging a map beyond a pinned snapshot requires a refresh.

## Connect MCP

```sh
umap-art mcp --workspace ./map-workspace
```

Register that command in your MCP client, using an absolute workspace path and an
executable available to the client. Example server entry for a Windows installation:

```json
{
  "mcpServers": {
    "umap": {
      "command": "umap-art",
      "args": ["mcp", "--workspace", "C:/maps/umap-workspace"]
    }
  }
}
```

The server provides ten tools for location search, themes, creation, inspection,
targeted edits, data refresh, rendering, job inspection/cancellation and artifacts.
Long jobs return `job_id`; the client polls `get_job`. Use `base_revision` for edits.
Undo creates a new revision from an old one. The server does not call a model API.
See [MCP behavior](https://github.com/U-C4N/Umap/blob/main/docs/mcp.md) for the full
contract and output limits.

## Data and licensing

| Purpose | Provider | Behavior |
|---|---|---|
| Place search | [Photon](https://github.com/komoot/photon#demo-server) | Cached, user-initiated searches; no silent ambiguous selection |
| Buildings, roads, green, inland water | [Overpass / OpenStreetMap](https://dev.overpass-api.de/overpass-doc/en/preface/commons.html) | Bounded raw OSM queries, assembled with Pyosmium |
| Ocean polygons | [Overture](https://docs.overturemaps.org/schema/reference/base/water/) | Anonymous STAC/GeoParquet range reads for selected files and row groups |

The data remains subject to source licenses and attribution. OpenStreetMap and
Overture Base water are ODbL data; the application code is MIT; DejaVu Sans has its
own bundled license. Ocean and Overpass data can have different dates. An OSM
building map is not a completeness guarantee or a cadastral survey.

## Scope and verification

- A3/A4, fixed center/scale or bbox fitting, up to 25 km².
- Two themes, four analytical views plus a combined general map.
- Editable SVG text by default; install the delivered font in the target editor,
  or use `page.text_mode="outline"` for path text.
- RGB PDF with embedded font. CMYK/PDF-X, remote MCP, routing, 3D and a web editor
  are outside this release.
- Python calls within one process are serialized; MCP isolates render workers.
- Derived caches can be rebuilt. Keep a saved output directory or `project.zip`
  when reproducibility matters.

```sh
uv run pytest
uv run ruff check src tests scripts
uv run python scripts/benchmark.py
# Explicitly contact public services:
uv run pytest --live -m live
```

[Türkçe hızlı başlangıç](https://github.com/U-C4N/Umap/blob/main/docs/hizli-baslangic.md)
· [Recipe/API reference](https://github.com/U-C4N/Umap/blob/main/docs/api.md)
· [Architecture](https://github.com/U-C4N/Umap/blob/main/docs/architecture.md)
· [Validation and release status](https://github.com/U-C4N/Umap/blob/main/docs/validation.md)
· [Publish from GitHub](https://github.com/U-C4N/Umap/blob/main/docs/publishing.md)
