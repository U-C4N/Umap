# Recipes and Python API

The stable API is `MapSpec`, `RenderResult`, and `render(spec, output_dir=..., places_csv=...)`.
The renderer also accepts a recipe file path. Relative snapshot and photo paths are then
resolved against that file. When constructing a model from JSON text yourself,
resolve its snapshot against the original recipe directory before calling render.
Unknown fields and schema versions are rejected.

Version 0.2 reads existing v1 recipes with the same classic layout defaults.
The added poster fields still use `schema_version="1"`; recipes containing these
fields require Umap 0.2 or newer. Forward compatibility with 0.1 is not promised.

## Recipe fields

| Field | Default / contract |
|---|---|
| `schema_version` | `"1"` |
| `area` | Exactly one of `center`, `place`, `bbox` |
| `area.scale_denominator` | 5000; used for center/place. Bbox mode computes scale |
| `page` | A3 landscape, 300 DPI, 10 mm margins, 20 mm header, 16 mm footer |
| `page.text_mode` | `editable` or `outline` |
| `page.png_resolution` | `auto` (default) gives the standard 300-DPI setting at least 3840 pixels on the long edge, preserving larger pages. Other explicit DPI values use print dimensions. `4k` fixes the long edge at exactly 3840 pixels. `print` uses the requested DPI on every size. |
| `page.layout` | `classic` (default), `poster`, `guide`, `pocket`, `field_cards`. All place layouts use `views=["general"]`. The last two require `size="A5"` and `orientation="portrait"`. |
| `page.title_size_pt` | Optional 8–48 pt; legacy default in classic, 24 pt in poster/guide |
| `page.subtitle_size_pt` | Optional 7–24 pt; default 9 pt |
| `style.schema_version` | `"1"`; also supported for standalone style documents |
| `style.theme` | `architectural`, `city_poster`, `minimal`, `blueprint`, `vintage`, `neon` |
| `style.ink`, `style.accent` | Optional `#RRGGBB` overrides for text/decorations and place markers |
| `style.layers` | Per-layer partial paint overrides |
| `style.order` | Every layer exactly once; default water, green, buildings, roads |
| `style.rules` | Ordered validated filters with partial paint overrides |
| `views` | `["general"]`; also `figure_ground`, `roads`, `green`, `water` |
| `formats` | `["png", "svg", "pdf"]` |
| `title`, `subtitle` | `Umap`, empty string |
| `places` | Up to 12 objects with unique `id`, `label` and `coordinates: [longitude, latitude]` in a place layout. Optional `note`, `bearing` and `reference_photo`. |
| `language` | `tr` or `en`; affects map labels, does not translate user text |
| `geometry_policy` | `strict`; `repair` explicitly requests topology repair with diagnostics |
| `source.snapshot` | Path to a hash-verified normalized dataset snapshot |
| `source.offline` | False for fresh requests; true in saved recipes |
| `source.include_ocean` | True; false explicitly omits the Overture ocean source |
| `source.*_url` | Configurable Photon, Overpass, Overture catalog endpoints |
| `limits` | 25 km², 180 s acquisition, 150 MiB response budget, 200,000 features |
| `bundle` | True; include a portable ZIP |

Use `umap-art schema` for the complete generated JSON Schema. Supported coordinates
are within UTM coverage (80°S to 84°N); antimeridian extents are rejected. Maximum
sampled local projection distortion is 0.1%. This is a map scale check, not a claim
about the accuracy of OSM objects.

The installed package includes JSON Schema Draft 2020-12 files under
`umap_art/schemas/v1/`: `map-spec.schema.json`, `style-spec.schema.json`,
`render-result.schema.json`, and `dataset.schema.json`. Read them without relying
on the installation directory:

```python
from importlib.resources import files

schema_text = files("umap_art").joinpath("schemas", "v1", "style-spec.schema.json").read_text(
    encoding="utf-8"
)
```

These files describe document structure and primitive field constraints. Python
validation additionally checks relationships between fields, such as mutually
exclusive area inputs, layer order, and style filter rules. Maintainers regenerate
the packaged files with `python scripts/export_schemas.py` after model changes;
`--output DIRECTORY` exports a separate copy. Schemas contain no hosted `$id`.

## Style a particular road class

```json
{
  "schema_version": "1",
  "theme": "architectural",
  "layers": {"buildings": {"fill": "#343A40"}},
  "rules": [
    {
      "layer": "roads",
      "when": {"in": ["highway", ["primary", "secondary"]]},
      "paint": {"stroke": "#B34A44", "width_mm": 0.5}
    }
  ]
}
```

This object is the `style` field. Paint fields are `fill`, `stroke`, `width_mm`,
`opacity`, `dash_mm` and `visible`. Colors use `#RRGGBB`; null fill/stroke disables
that paint. Later matching rules override earlier paint properties. Operators:
`eq`, `in`, `has`, `all`, `any`; an empty condition matches every feature. Filters
have depth/size limits and never execute expressions. Default road widths also
reflect highway class; an explicit width override is a physical page measurement.

## Add selected places

```python
from umap_art import MapSpec, render

spec = MapSpec(
    area={"center": [29.025, 40.985], "scale_denominator": 5000},
    page={"size": "A4", "orientation": "portrait", "layout": "poster"},
    style={"theme": "vintage", "accent": "#913E2B"},
    title="Kadıköy",
    subtitle="Seçtiğim noktalar",
    places=[{"id": "meeting", "label": "Buluşma noktası", "coordinates": [29.025, 40.985]}],
)
result = render(spec, output_dir="outputs")
```

Place IDs are nonblank strings of 1–80 characters, labels are nonblank strings of
1–180 characters. Labels must fit one line in the printed column. Coordinates use
the same UTM coverage as the map. Numbering follows list order; IDs stay stable
when places are reordered. These user locations belong to the recipe and manifest,
not to the geographic snapshot. They are not queried, translated or geocoded by
the renderer. Existing `locations` / `find_map_location` results can supply coordinates.

Both poster layouts reserve a 36 mm directory band, two columns of six rows,
including when the list is empty. This band is additional to `header_mm` and
`footer_mm`. Header height controls the title band; in `poster` that band sits
below the map, in `guide` it sits above. Changing font size never resizes the bands;
overflow fails with `TEXT_OVERFLOW`. Place labels use 8 pt, marker numbers 7 pt,
and markers have a physical diameter of 5 mm. Colliding markers move apart with
leader lines to their original coordinates. Isolated edge markers can be clipped.
See the [poster gallery](posters.md).

### Pocket guides and camera stations (v0.3.0)

`places_csv` replaces the recipe list at render time. CSV uses UTF-8, a comma
delimiter and a header. Required columns are `name,latitude,longitude`. Optional
columns are `id,note,bearing,reference_photo`. Turkish headers are supported
(`ad,enlem,boylam,not,yön,fotoğraf`). Generated IDs use the name and coordinates.
Use explicit IDs for identical entries. Photo paths in CSV are relative to the CSV.

`pocket` creates the two sides of an A5 guide. `field_cards` requires at least
one station and, for each, a bearing in [0, 360) clockwise from true north and a
local JPEG or PNG reference photo (up to 20 MiB and 40 megapixels). Use a short
note and place name. Text that cannot fit the page reports `TEXT_OVERFLOW`.
When PDF is requested, pages are combined in `pocket-guide.pdf` or `field-cards.pdf`.
PNG and SVG create one file per side or station. The saved recipe and ZIP retain
the selected places and local copies of photographs.

## Outputs and errors

`RenderResult.schema_version` is `"1"`, matching the versioned standalone style,
recipe and dataset documents. Omitting it uses v1; unsupported versions are rejected.
`RenderResult` returns artifact paths/MIME types/hashes, manifest and recipe paths,
snapshot path, dataset ID, scene hashes and diagnostics. Outputs are published
atomically in a unique directory. A failure before publication removes staging
files. PNG dimensions round the page dimensions at the chosen DPI; PDF/SVG keep
physical units. SVG/PDF byte equality across operating systems is not promised.

`UmapError` has `code`, `message`, `details` and `to_dict()`. Typical errors:

| Code | Action |
|---|---|
| `AMBIGUOUS_LOCATION` | Inspect `details.candidates`, select coordinates |
| `AREA_LIMIT` / `PROJECTION_DISTORTION` | Choose a smaller or supported extent |
| `SNAPSHOT_EXTENT` / `SNAPSHOT_SOURCES` | Explicitly refresh data for the changed request |
| `SNAPSHOT_INTEGRITY` | Restore the original snapshot; do not edit its geometry in place |
| `INVALID_GEOMETRY` | Inspect the feature; explicitly request repair if appropriate |
| `INVALID_FILTER` | Correct the declarative style rule |
| `PLACE_OUTSIDE_MAP` | Move/remove the selected place, or explicitly acquire a map covering it |
| `TEXT_OVERFLOW` / `MISSING_GLYPH` | Shorten the text, adjust supported text sizes/bands, or use supported characters |
| `PLACE_OVERLAP` / `PLACE_CLIPPED` | A number was separated automatically or an isolated marker touches the frame |
| `INVALID_PLACES_CSV` / `INVALID_REFERENCE_PHOTO` | Correct the indicated CSV row or supply a readable local JPEG/PNG |
| `source_unavailable` / `source_timeout` | Retry later, or render an existing saved snapshot |
| `source_incomplete` / `source_schema` | Inspect provider diagnostics; no partial final map is published |

CLI returns 0 on success, 2 for application/input errors, 130 for interruption.
Progress and errors use stderr; `--json` writes machine-readable results to stdout.
