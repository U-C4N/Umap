# 0.2.0 — personal map posters

**Bir semt. Üç anlatım. Düzenlemeye devam edebileceğin tek proje.**

- `umap-art demo` creates a real Kadıköy poster and editable project after
  installation, without a repository checkout or network connection.
- `--preset guide` uses the same three example markers in a numbered guide;
  `--preset atlas` creates four separate architectural analysis pages. All use
  A4 portrait, 1:5000, 300 DPI, PNG/SVG/PDF and a portable project ZIP.
- Six themes, `--output`, machine-readable `--json`, and the equivalent
  `python -m umap_art demo` entry point. Each invocation preserves earlier output.
- Bundled, hash-verified source data includes acquisition dates and attribution.
  Example markers are illustrative, not verified venue recommendations.
- Four additional themes: minimal, blueprint, vintage and vector-only neon.
- Poster and guide layouts with fixed physical bands, adjustable title/subtitle
  sizes, text colour and marker accent colour.
- Up to twelve user-selected places, numbered in recipe order with editable SVG
  paths/text and a two-column directory. Stable IDs survive reordering.
- Explicit errors for out-of-frame points, text overflow and missing glyphs;
  diagnostics for overlapping or clipped markers. No automatic location search.
- Offline place/design edits reuse the source snapshot and projected geometry.
  Recipes, manifests and portable ZIPs carry the user selections.
- MCP place-list replacement, preview and undo; optional editable changes on
  `refresh_map_data`, committed only after successful acquisition without conflicts.
- Two runnable poster recipes, an offline gallery generator, six-theme gallery,
  output-level acceptance tests and installed-wheel poster verification.
- Reproducible real-data gallery, offline revision and moved-ZIP demonstrations.
- Fresh core installations, real installed MCP lifecycle tests with networking
  blocked in the server and workers, and source-distribution round-trip checks.
- `scripts/benchmark.py --check` writes its report and exits unsuccessfully if
  any measured performance target fails.
- Release evidence ties human acceptance to one successful main-branch CI run
  and its exact wheel/sdist hashes. Publishing transfers those tested files
  instead of rebuilding them, and rejects missing or expired artifacts.

Existing v1 recipes keep their classic default appearance. The additive fields
retain schema version `1`, but new recipes require Umap 0.2 or newer. Snapshot
format and the public `MapSpec` / `RenderResult` / `render` entry points are unchanged.
Poster/guide layouts require the general view. Analytical views use classic.

See [posters](posters.md), [API](api.md), [MCP](mcp.md),
[release acceptance](release-acceptance.md) and [validation](validation.md).
Local verification is not a claim that remote CI,
manual Inkscape acceptance, the user pilot or public release publication has run.

# 0.1.0 — local release candidate

Umap creates editable, physically scaled city maps using keyless Photon,
OpenStreetMap/Overpass and Overture sources.

- Shared Python API, terminal commands and optional local MCP server.
- Architectural and city-poster themes, a general map and four aligned analytical
  pages, A3/A4 layouts, PNG, editable SVG and embedded-font vector PDF.
- Declarative style filters, stable feature IDs, UTM projection, courtyard holes,
  bridges/tunnels, explicit invalid-geometry repair and bounded data acquisition.
- Hash-verified snapshots, offline revisions, independent source/geometry/output
  caches, source manifests, font notices and portable reproduction archives.
- Ten MCP tools, persisted revisions, conflict/idempotence checks, one worker and
  four queued jobs, cancellation, restart recovery and bounded artifact resources.
- MIT code, packaged DejaVu Sans, English API documentation, Turkish quickstart,
  versioned schemas, binary-install checks and a nine-configuration CI matrix.

See [validation](validation.md) for measured results and outstanding publication
gates. Public data coverage and service availability are outside Umap's control.
The first release is RGB and local; remote MCP, a web editor, CMYK/PDF-X, routing,
3D and free-layout multi-map boards are deferred.
