# Validation and release status

Recorded on 12 October 2026. The implementation and local installable packages are
available; this is not a claim that the human pilot or all release gates have run.

## Local automated verification

The Windows x64 / Python 3.14.6 test suite passed. The normal suite intentionally
skips its one opt-in live-provider test. Ruff reported no errors.

Coverage includes malformed XML, incomplete references, empty source responses,
429/retries/timeouts, Photon coordinate conversion, ocean containment and schema
errors; courtyard holes, invalid geometry and water-line clipping; page sizes,
editable SVG IDs/text, Turkish glyphs, PDF font embedding and physical scale;
snapshot integrity, offline rendering and Python/CLI/MCP scene equivalence;
revision conflicts, idempotence, queue capacity, cancellation, timeout, worker
crash, restart recovery, parent death and workspace/junction containment.

The 100 m fixture at 1:5000 measures 20 mm in the scene and delivered SVG/PDF path
coordinates. Raster batching is compared with unbatched drawing with a maximum
one-level RGB difference at antialiased edges. Other platforms are compared by
geometry and page contracts, not promised byte identity.

A wheel and source distribution were built locally. The wheel was installed into
a fresh environment with `--only-binary :all:` and imported from `site-packages`
under Python's isolated mode. Font/license packaging, all three offline outputs,
CLI scene equivalence and a real SDK v2 stdio MCP connection passed. No native
compiler or desktop GIS was used.

Reproduce the checks:

```sh
uv sync --frozen --all-extras
uv run ruff check src tests scripts
uv run pytest --basetemp .cache/pytest-check
uv build
uv run python scripts/wheel_smoke.py --install dist --environment .cache/fresh-wheel-check
```

The wheel check requires an environment directory that does not already exist.

## Live keyless acquisition

All five windows successfully used public Overpass and Overture data. Photon was
also exercised in the opt-in source probe. No credentials or API keys were used.

| Window | Normalized features | First production elapsed |
|---|---:|---:|
| Kadıköy, İstanbul | 3,862 | 77.94 s |
| Ankara | 611 | 33.74 s |
| Amsterdam | 1,695 | 124.42 s |
| Venice | 2,175 | 48.24 s |
| Barcelona | 1,253 | 29.18 s |

Kadıköy used A3 landscape, 1:5000, 300 DPI PNG plus SVG and PDF. The remaining four
used smaller A4 landscape windows, 1:3000, 72 DPI PNG plus SVG; their timings are
not directly comparable. Overture release `2026-09-23.1` supplied the ocean layer.
The four inland/city-center windows had zero intersecting ocean features; their
OSM inland-water layers remained available. Source timestamps are recorded per
output, separately from access time.

The five map layouts were visually inspected for page, legend, scale and source
overlap. This is not an independent geographic completeness survey. The same
Kadıköy snapshot subsequently produced the poster and four aligned architectural
pages offline. Live source availability and waiting times can change.

Local evidence is retained under `outputs/live/`, `outputs/cities/report.json`,
`outputs/delivery/index.json` and `.cache/wheel-smoke-result.json`. These generated
datasets and machine-specific paths are intentionally excluded from Git. Run
`uv run python scripts/probe_cities.py` to record another four-city probe.

## Performance

`scripts/benchmark.py` creates a fixed synthetic 10,000-building / 2,000-road
snapshot and disables networking. Measured on Windows 11, Python 3.14.6, **24
physical cores / 32 logical cores and about 32 GiB RAM**:

| Phase | Elapsed | Sampled peak RSS |
|---|---:|---:|
| Cold A3 300 DPI PNG + SVG + PDF + ZIP | 8.26 s | 368 MiB |
| Warm geometry, fresh 72 DPI preview | 1.60 s | 251 MiB |
| Identical cached preview | 1.17 s | 204 MiB |
| Changed road color, new preview | 1.53 s | 208 MiB |

These satisfy the numeric development targets on this machine. The planned
4-core/16-GiB reference-machine gate remains unmeasured. Process startup and fixture
generation are excluded; native renderer imports are included in the cold phase.
RSS is sampled every 20 ms and can miss instantaneous peaks. Reports contain the
fixture hash, machine details, dependency versions and separate phase outputs.

Run `uv run python scripts/benchmark.py`; `.cache/benchmark/latest.json` points to
the latest report. No public service requests are needed.

## Remaining release gates

- The repository's CI workflow defines Python 3.12, 3.13 and 3.14 on Windows x64,
  Linux x64 and macOS ARM64. Remote matrix results have not been obtained here.
- Inkscape's actual GUI editing workflow still needs a manual acceptance pass;
  SVG group, individual path, ID and editable text structure is tested in code.
- The three-architect/designer usability pilot has not been conducted. Record
  time to first useful output, manual corrections and intent to reuse the tool.
- Benchmark the documented 4-core/16-GiB reference machine before advertising
  its performance targets as supported guarantees.
- Recheck the `umap-art` distribution name at publication time, run the full
  matrix and prepare the release tag. The local build has not been uploaded to
  PyPI or published as a GitHub release.
