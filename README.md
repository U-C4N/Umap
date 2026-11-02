# Umap Art

**Editable city maps for posters, neighborhood guides, architectural studies and repeat photography.**

Create maps for spatial studies, presentations and personal neighborhood guides
from open data. Start with a bundled real-world example, then choose a theme,
add your own places, and export **PNG, editable SVG and vector PDF** at a
real-world scale — through Python, the CLI or a local MCP server.

[![Python 3.12–3.14](https://img.shields.io/badge/Python-3.12%E2%80%933.14-3776AB?logo=python&logoColor=white)](pyproject.toml)
[![Source version 0.3.0](https://img.shields.io/badge/source-v0.3.0-2563EB)](docs/release-notes.md)
[![License: MIT](https://img.shields.io/badge/code-MIT-16A34A)](LICENSE)

[Quick start](#quick-start) · [Python](#create-a-poster-in-python) ·
[MCP](#connect-your-mcp-client) · [Documentation](#documentation) ·
[Türkçe başlangıç](docs/hizli-baslangic.md)

## What changed from v0.2.0 to v0.3.0?

| Task | v0.2.0 | v0.3.0 |
|---|---|---|
| Add selected places | Enter each place in the map recipe | Import up to 12 places from a CSV in row order. Invalid coordinates identify the row to fix. |
| Read nearby markers | Overlapping numbers share space and produce a warning | Numbers move apart automatically. A dot and a leader line identify each original coordinate. |
| Carry a neighborhood guide | A3 or A4, with the map and directory on one side | **A5 pocket guide** with the map on the front and numbered places and notes on the reverse, in one two-page PDF. |
| Return to a camera position | A numbered point identifies the location | **Aynı Kadraj** gives each station its own A5 card with a position, direction arrow, true bearing, reference photo and field note. |
| Read the exported artwork | DPI-based PNGs and single-weight page typography | All five layouts share clearer titles and page identifiers. Default PNG exports have at least 3,840 pixels on the long side. SVG and PDF preserve physical scale. |

[![Five v0.3.0 layouts rendered from Kadıköy data](docs/release-showcase.png)](docs/release-showcase.png)

*The poster, neighborhood guide and atlas are A4. The pocket guide and camera
card are A5. All five use the same October 2026 map data at 1:5000. The building
in the example camera card is an AI-generated illustration.*

Install the v0.3.0 package with `python -m pip install "umap-art==0.3.0"`, then try:

```sh
umap-art demo --preset pocket
umap-art demo --preset field-cards
```

Open **`pocket-guide.pdf`**. Print at actual size on A5 (148 × 210 mm), double-sided,
flipping on the long edge. PNG and editable SVG exports are named by side.

**Make your own field cards.** Put your reference JPEG or PNG next to a UTF-8
file named `stations.csv`. These example coordinates fit the bundled Kadıköy map.
Replace the filename and bearing with those from your own shot.

```csv
name,latitude,longitude,bearing,reference_photo,note
Sokak köşesi,40.9850,29.0250,75,corner.jpg,Kapı eşiğini kadrajın solunda tut.
```

```sh
umap-art demo --preset field-cards --places-csv stations.csv
```

Open **`field-cards.pdf`**. Each page uses one CSV row. Bearings are degrees
clockwise from true north. The project ZIP includes the reference images for
offline reprints. For a pocket guide, only `name,latitude,longitude` are required.
`--places-csv` also works with `render` and `refresh` on your own map recipe.
See the [Turkish walkthrough](docs/hizli-baslangic.md#v030-ile-cep-rehberi-ve-aynı-kadraj).

## What you can make

| Make | Start with | What you get |
|---|---|---|
| A personal city poster | `umap-art demo` | A4 portrait, vintage colours, a centred title and numbered places |
| A neighborhood guide | `umap-art demo --preset guide` | A4 portrait, blueprint colours and an ordered place directory |
| A pocket guide | `umap-art demo --preset pocket` | A5 map front and a notes directory on the back |
| Camera station cards | `umap-art demo --preset field-cards` | A5 cards with mapped direction, coordinates and a reference image |
| An architectural study | `umap-art demo --preset atlas` | Four aligned A4 pages for buildings, roads, green spaces and water |
| A general city map | [Kadıköy map](examples/kadikoy.json) | A3 landscape with a legend, scale bar and all four map layers |

- **Edit the artwork.** SVG retains semantic groups, individual paths, stable IDs
  and editable text. PDF embeds the bundled font.
- **Keep the scale.** Page geometry uses millimetres and points. Set a scale such
  as 1:5000, or fit a bounding box to the page.
- **Make it yours.** Choose from six themes, override layer colours, adjust title sizes
  and add up to twelve numbered places.
- **Revise offline.** Saved recipes pin a verified dataset. Changing colours,
  text or selected places reuses that data.
- **Take the project with you.** Every default export includes the recipe,
  snapshot, source manifest, font/license and a portable ZIP.

The bundled demo needs no map download. Acquiring your own area uses public
services without an account or API key. Their
availability and data coverage can vary. Umap runs locally and does not call a
model API; an MCP client supplies its own assistant.

## Quick start

Use Python **3.12–3.14** to install the v0.3.0 release.

```sh
python -m pip install "umap-art==0.3.0"
umap-art doctor
umap-art demo
```

If your shell cannot find `umap-art`, use `python -m umap_art` with the same Python
environment. The distribution name is `umap-art`; the import is `umap_art`.
For a source installation, see [Development and verification](#development-and-verification).

The demo works from the installed package, without cloning example files or
contacting map services. Its default is an A4 portrait poster in the vintage theme
at 1:5000. Installation itself may download Python dependencies.
The command prints the preview, SVG, PDF and recipe paths, and creates a new
project directory under `outputs`. Open a PNG to inspect the map or an SVG to
continue in your vector editor.

Make a guide, an architectural atlas or a different poster theme from the same
saved data, without editing JSON:

```sh
umap-art demo --preset guide --output outputs
umap-art demo --preset atlas --output outputs
umap-art demo --theme neon --output outputs
umap-art styles
```

Use `--preset poster`, `guide`, `atlas`, `pocket` or `field-cards`. Supply
`--places-csv` to use your own stations. Use `--theme` to override a preset's theme.
Each run keeps earlier outputs and delivers its own recipe, snapshot and ZIP.
The atlas produces four separate pages.
The presets share a dataset and physical scale. Their visible frames vary by layout.

For your own area, use the Python example below or adapt a [repository recipe](examples)
and run `umap-art render <recipe.json> --output outputs`. Those additional recipes
are not copied into your working directory by package installation. First
acquisition depends on public services; delivered snapshots support later offline edits.

## Choose your look

All five layouts use Space Grotesk and a single white background across the
page and map. An explicit `style.background` sets both to the same colour.

| Theme | Palette and treatment |
|---|---|
| `architectural` | Restrained greys and soft land/water colours |
| `city_poster` | Terracotta buildings, warm grey streets and blue water |
| `minimal` | Black, white and greys |
| `blueprint` | Blue outlines and navy roads on white |
| `vintage` | Sepia buildings and muted greens on white |
| `neon` | Teal roads, violet buildings and pink markers on white |

Use `page.layout="poster"` for a centred title below the map, or `"guide"` for a
title above it. Both provide a two-column directory for up to twelve places and
use the `general` view. The default `classic` layout also supports the four
analytical views.

The place band has a fixed size, even when empty: adding or removing a point does
not move the map frame. Neon uses vector fills and strokes, keeping the SVG and
PDF editable. See the [poster guide](docs/posters.md) for layout details.

## Create a poster in Python

```python
from umap_art import MapSpec, render

spec = MapSpec(
    area={"center": [29.025, 40.985], "scale_denominator": 5000},
    page={"size": "A4", "orientation": "portrait", "layout": "poster", "dpi": 300},
    style={"theme": "vintage", "accent": "#913E2B"},
    title="Kadıköy",
    subtitle="Seçtiğim noktalar · İstanbul",
    places=[
        {"id": "meeting", "label": "Buluşma noktası", "coordinates": [29.025, 40.985]},
    ],
)

result = render(spec, output_dir="outputs")
print(result.recipe_path)
```

Coordinates are always **longitude, latitude**. Place IDs must be unique;
numbering follows list order. Labels are your own content, and rendering does
not search for or invent locations.

To find coordinates by name:

```sh
umap-art locations "Kadıköy, İstanbul"
```

Choose the intended candidate and use its coordinates. Python and CLI recipes also
accept `area.place`; ambiguous results return candidates for you to choose from.

| To change… | Set… |
|---|---|
| Overall palette | `style.theme` |
| One layer's colour or line width | `style.layers` |
| Features matching a property, such as primary roads | `style.rules` |
| Text and marker colours | `style.ink`, `style.accent` |
| Title and subtitle size | `page.title_size_pt`, `page.subtitle_size_pt` |
| Place names, positions or order | `places` |

See the [recipe/API reference](docs/api.md) for field limits, filters and errors.
Version 0.3 reads earlier v1 recipes. Pocket guides, field cards and
`page.png_resolution` require Umap 0.3 or newer.

## Edit without downloading again

Continue from the Python example above, using its `result`:

```python
from pathlib import Path
from umap_art import MapSpec, render

recipe = Path(result.recipe_path)
edited = MapSpec.model_validate_json(recipe.read_text(encoding="utf-8"))
edited.source.snapshot = str(recipe.parent / edited.source.snapshot)
edited.style.theme = "blueprint"
edited.style.accent = "#FFE09A"
edited.places[0].label = "Burada buluşalım"

revised = render(edited, output_dir="outputs")
print(revised.recipe_path)
```

Saved recipes set `source.offline=true`. The CLI resolves a saved recipe's relative
snapshot path automatically; constructing a model from JSON yourself requires
resolving it as shown above.

Use `umap-art refresh` with your recipe when you explicitly want fresh data.
Changing providers or expanding the map beyond its pinned snapshot also requires
a refresh. Each render writes a new output directory and preserves earlier outputs.

### What travels with an export

A default single-view export contains:

```text
general.png          Raster image at the requested DPI
general.svg          Editable vector artwork
general.pdf          Vector PDF with embedded font
recipe.json          Design settings and selected places
snapshot.json        Hash-verified geographic data
manifest.json        Sources, versions, diagnostics and artifact hashes
assets/              Bundled font and its license
DATA-LICENSES.txt     Source attribution and license notices
project.zip          Portable copy of the project
```

Keep the whole output directory or `project.zip` to reproduce a design. Analytical
exports use their view names, such as `figure_ground.svg`, instead of `general`.
For SVG text editing, install the delivered Space Grotesk faces and DejaVu Sans fallback;
`page.text_mode="outline"` converts text to paths when font independence matters.

## Connect your MCP client

Install the optional MCP adapter, then start a local workspace:

```sh
python -m pip install "umap-art[mcp]==0.3.0"
umap-art mcp --workspace ./map-workspace
```

Register the command in your client's server configuration, with an absolute
workspace path and an executable the client can find. Example for Windows:

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

Example request to your connected assistant:

> Create an A4 portrait poster of Kadıköy in the vintage theme. Use the title
> “Benim Kadıköy’üm” and mark the three coordinates I provide. Then change only
> the theme to blueprint and export SVG and PDF.

The server exposes **ten tools** for location search, styles, map creation,
inspection, edits, refresh, rendering, job status/cancellation and artifacts.
Long operations return a `job_id`; poll `get_job` for the result. Edits use
`base_revision`, and restoring an earlier version creates a new revision.

Colour, text and place edits use pinned data. For a larger page needing more
coverage, `refresh_map_data` accepts the intended `changes` and commits them only
after a successful refresh without a revision conflict.
See the [MCP contract](docs/mcp.md) for tool arguments, previews and artifact access.

## Data, scale and boundaries

| Data | Provider | How Umap uses it |
|---|---|---|
| Place search | [Photon](https://github.com/komoot/photon#demo-server) | Cached, user-initiated searches with explicit candidate selection |
| Buildings, roads, green and inland water | [OpenStreetMap / Overpass](https://dev.overpass-api.de/overpass-doc/en/preface/commons.html) | Bounded queries assembled with Pyosmium |
| Ocean polygons | [Overture](https://docs.overturemaps.org/schema/reference/base/water/) | Anonymous STAC/GeoParquet reads for the selected area |

- A3/A4/A5 pages, portrait or landscape, fixed centre/scale or bbox fitting, up to
  **25 km²**. Choosing a place name does not select its entire administrative area.
- PNG at 72–600 DPI, editable SVG and RGB vector PDF. CMYK/PDF-X, routing, GPX,
  3D, a web editor and remote MCP are outside this release.
- Out-of-frame points and overflowing text produce explicit errors. Crowded
  numbers get leader lines. Isolated markers clipped at the frame edge produce a warning.
- Source dates can differ, and successful downloads do not establish geographic
  completeness. OSM building data is not a cadastral survey.

Umap owns its source adapters, geometry pipeline, declarative styles and scene
model. Shapely, pyproj and Matplotlib provide infrastructure; Prettymaps, OSMnx,
QGIS and GDAL are not runtime dependencies. Python calls within one process are
serialized; MCP uses isolated render workers. See the [architecture](docs/architecture.md).

## Development and verification

To install the source checkout, including the optional MCP adapter:

```sh
git clone https://github.com/U-C4N/Umap.git
cd Umap
python -m pip install ".[mcp]"
umap-art demo
```

Use `python -m pip install .` if you only need the core package. The checkout also
contains the additional [example recipes](examples) and the showcase scripts.
For development checks, install [uv](https://docs.astral.sh/uv/), then run from
the repository:

```sh
uv sync --frozen --all-extras --dev
uv run pytest -m "not live"
uv run ruff check src tests scripts
uv run python scripts/benchmark.py
uv run python scripts/poster_gallery.py
uv run python scripts/release_showcase.py --output outputs/release-showcase
```

The benchmark and default gallery generator use synthetic snapshots. The release
showcase uses the bundled real Kadıköy snapshot, creates the six themes, a guide,
four analytical pages and a before/after comparison, and verifies an extracted
ZIP can reproduce the edited result. All three disable network connections.
Choose a new showcase output directory on every run to preserve its evidence.
Its `index.json` records dataset, geometry, marker, scene and artifact checks;
this does not replace manual SVG editing acceptance. To test public providers:

```sh
uv run pytest --live -m live
```

For v0.3.0, 331 offline tests passed locally on Windows with Python 3.14.
The candidate was also installed from its wheel and used to produce a 4K field card.
The release evidence records the nine-environment CI run, distribution hashes and
the disposition of the Inkscape edit/reopen check, three-user pilot and physical
reference-machine performance checks. [v0.3.0 release evidence](https://github.com/U-C4N/Umap/releases/download/v0.3.0/release-evidence.json).

For bug reports, include the output of `umap-art --version`, the error code and a
minimal recipe. [Open an issue](https://github.com/U-C4N/Umap/issues).

## Documentation

| I want to… | Read |
|---|---|
| Get started in Turkish | [Türkçe hızlı başlangıç](docs/hizli-baslangic.md) |
| Design a poster or guide | [Poster workflow and gallery](docs/posters.md) |
| Understand recipe fields and errors | [Python/API reference](docs/api.md) |
| Connect an assistant | [Local MCP workflow](docs/mcp.md) |
| Understand the implementation | [Architecture and data ownership](docs/architecture.md) |
| Check what changed and what was verified | [Release notes](docs/release-notes.md) · [Validation](docs/validation.md) |
| Publish a release | [GitHub/PyPI publishing guide](docs/publishing.md) |

## License and attribution

Umap's application code is [MIT licensed](LICENSE). Geographic data retains its
source licenses: OpenStreetMap and Overture Base water use ODbL. Bundled fonts
include [Space Grotesk](src/umap_art/assets/fonts/LICENSE_SPACE_GROTESK) and
the [DejaVu Sans fallback](src/umap_art/assets/fonts/LICENSE_DEJAVU).
Preserve the source attribution when sharing artwork; source and font notices
travel with each default export.

[OpenStreetMap attribution](https://www.openstreetmap.org/copyright) ·
[Overture attribution](https://docs.overturemaps.org/attribution/)
