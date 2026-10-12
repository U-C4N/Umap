# Architecture and data ownership

Python, CLI and MCP call the same application service. The core recipe has no
MCP-specific IDs, job queue, or database requirement.

| Layer | Responsibility |
|---|---|
| `models` | Versioned validated public recipes/results |
| `sources` | Photon search, complete OSM XML assembly, bounded Overture ocean reads |
| `geometry` | UTM selection, scale/extent, validation, clipping, ocean union |
| `styles` / `scene` | Declarative styling, deterministic IDs, layout in page points |
| `renderer` | Matplotlib backends; no network or geographic decisions |
| `service` / `storage` | Snapshots, separate caches, atomic outputs, manifests |
| `workspace` / `worker` | Immutable revisions, SQLite jobs, owned subprocess lifecycle |
| `cli` / `mcp_server` | Thin presentation adapters |

## Online acquisition

Photon results are normalized to longitude/latitude. Ambiguous places are never
silently resolved. Overpass retrieves nodes, ways and relations; Pyosmium assembles
areas, preserving inner rings. Missing references and provider error remarks are
fatal; an empty valid response is separate.

The Overture adapter reads the STAC metadata index, selects intersecting water
assets, inspects Parquet row-group bbox statistics and reads only selected groups
and columns. A bounded HTTP range reader records requested bytes and raw hashes.
The geometric intersection test includes features enclosing the entire bbox.
Only ocean polygons enter the water layer; inland water remains from OSM.
Unavailable indexes/statistics cause an explicit error, never a global scan.

Acquisition is bounded by elapsed time, decoded HTTP bytes, file/row-group counts
and decoded Parquet size. Public-provider locks and caches are local to the cache
directory. They do not claim to enforce an aggregate quota across every user's
computer. There is no automatic endpoint rotation or paid fallback.

## Persistence and reproducibility

The source cache keeps raw content-addressed responses. A normalized snapshot
contains features, source times and provenance; its SHA-256 is verified on loading.
Saved output directories own a snapshot copy, so deleting a disposable cache cannot
erase a project. A changed provider profile or expanded extent requires explicit
refresh. Acquisition-query caches expire after one day for new requests; saved
recipes remain pinned indefinitely.

Projected geometry has a separate cache keyed by dataset, extent, repair policy and
geometry implementation/dependency versions. Render caches include semantic scene,
format/DPI/text mode, font hash and renderer implementation/dependency versions.
Style changes reuse geometry; exact repeats can reuse verified output files.

Source dates and transport success are not real-world completeness guarantees.
`coverage` remains `not_assessed`. Normalized feature geometry and a manifest make
the project reproducible even if the original public service changes.

## Physical output

The scene stores coordinates in PostScript points. Geographic dimensions are
metres; public page widths are mm, typography is pt. Layout is resolved before
selecting PNG/SVG/PDF and does not depend on DPI. SVG semantic groups and feature
IDs survive palette edits. PDF embeds the packaged font. Optional SVG outline text
trades text editing for font-independent appearance.

Data licensing stays separate from MIT software licensing. Source attribution and
data licenses travel with each output, and the font license travels with the font.
