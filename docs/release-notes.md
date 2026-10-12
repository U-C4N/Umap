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
