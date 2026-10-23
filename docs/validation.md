# Validation and release status

## v0.2.0 release implementation — 23 October 2026

The offline demo, portable real-data examples, gallery and release promotion
checks are implemented. On 23 October 2026 the release owner explicitly waived
three manual gates for v0.2.0: the Inkscape edit/save/reopen acceptance, the
three-user pilot and the physical 4-core/16-GB reference-device acceptance.
All three are recorded as `waived`, not `passed`. Inkscape was opened, but the
actual SVG editing, saving and reopening sequence was not completed. The user
pilot and physical reference-device test were not performed.

The full platform matrix, installed-package checks and exact CI artifact/hash
verification remain required. The published release's exact final CI run,
artifact ID and package hashes are recorded in its
[`release-evidence.json` asset](https://github.com/U-C4N/Umap/releases/tag/v0.2.0);
an earlier candidate's checks do not establish a new candidate's result.
The [acceptance protocol](release-acceptance.md) preserves
the original manual procedure for future use. The release evidence records the
owner's waiver and actual automated results against the canonical
Ubuntu/Python 3.14 CI wheel. Development-machine timings do not establish a
reference-device performance guarantee.

The final release-policy and documentation update passed **323 local tests**
(one live-provider test deselected) on Windows/Python 3.14.6; Ruff passed.
The report is `.cache/publish-v020-tests.xml`. Both evidence schemas retain
negative tests for commit, CI provenance, artifact identity and package hashes.

On Windows x64 / Python 3.14.6, **243 tests passed** (one live-provider test
deselected), and Ruff passed. A clean wheel installation with locked MCP
dependencies passed. A separate plain-pip core installation passed with MCP
absent. The final sdist was extracted into the OS temporary directory, built
there and installed into a fresh environment; all three demos, relocated
projects and the complete MCP lifecycle passed with external networking blocked.
Local reports are `.cache/release-implementation-tests.xml`,
`.cache/wheel-demo-locked.json`, `.cache/wheel-demo-core-online.json` and
`.cache/release-sdist-final.json`. These are development verification records;
CI provides the canonical packages to which release evidence is bound. This
earlier local record is not a claim that the final candidate's CI has completed.

Automated coverage now includes all three installed demo presets, six themes,
four atlas views, package-data integrity, JSON/stderr separation, output errors,
relocation and offline reproduction. The installed MCP smoke check exercises
create, wait, edit, export and resource reading through real stdio. Its network
guard propagates into the server and worker processes and records their PIDs.
The core smoke install uses only wheel metadata, without development or MCP
dependencies. Ubuntu CI also builds the sdist outside the checkout and installs
the resulting wheel in a fresh environment.

The reproducible showcase in `scripts/release_showcase.py` passed all 14 checks
with no network attempts. It produces the six-theme gallery, the poster/guide/
four-view atlas comparison, an offline revision and a moved-ZIP reproduction.
Poster and guide share a frame; the classic atlas has a larger map area.
Source data dates and example-marker limitations accompany the images.

**Latest development performance record — 23 October 2026:** three additional
benchmark `--check` runs produced **two passes and one failure**. In the failing
run, the warm preview took **5.574 s** and the poster edit took **5.547 s**, both
above their **5 s** targets. These results supersede any impression that the
earlier passing run below establishes consistent performance. They were measured
using candidate `0b585a7`; the map runtime and bundled data are unchanged by the
subsequent release-documentation changes. The reports remain observations of
that candidate, not proof of the final package's performance or a physical
4-core/16-GB acceptance. The failed run is retained as a failure; the owner's
waiver does not turn it into a pass.

**Earlier development baseline:** the Windows/Python 3.14 run passed `--check`:
cold export **13.56 s**, warm preview **3.82 s**, cached preview **2.82 s**,
style edit **3.45 s**, first poster frame **2.79 s**, poster edit **2.64 s**.
The largest sampled RSS was **370 MiB**. This machine has 24 physical cores and
about 32 GiB RAM; this run is not a reference-device acceptance.
The report is under `.cache/release-implementation-benchmark/`.

The nine-job platform matrix and release provenance/hash rejection tests are
part of the candidate checks. Release promotion requires the successful run's
exact artifact ID and verifies package hashes again after the final transfer.
Missing release evidence, an unrecorded waiver, a PR run, a different commit or
an expired artifact stops promotion. The three manual gates use the explicit
owner-authorized waiver for this version; they are not reported as successful tests.

```sh
uv sync --frozen --all-extras --dev
uv run ruff check src tests scripts
uv run pytest -m "not live" --junitxml .cache/release-implementation-tests.xml
uv build --no-sources --out-dir dist/release-check
uv run python scripts/wheel_smoke.py --install dist/release-check --environment .cache/release-wheel
uv run python scripts/wheel_smoke.py --install dist/release-check --environment .cache/release-core --plain-install --result .cache/release-core.json
uv run python scripts/wheel_smoke.py --install dist/release-check --environment .cache/release-sdist --from-sdist --result .cache/release-sdist.json
uv run python scripts/release_showcase.py --help
uv run python scripts/benchmark.py --check --output .cache/release-benchmark
```

Use fresh environment directories for each install. Installation may access
package indexes; the rendering and revision checks themselves run offline.
The full [publishing procedure](publishing.md) describes the canonical artifact,
evidence records and post-publication verification. Local test success alone
does not establish that the final candidate passed CI or was published.

### Poster implementation baseline — 13 October 2026

The following is the historical implementation record. Its open-gate statements
describe 13 October and are superseded for v0.2.0 by the 23 October decision above.

On Windows 11 x64 / Python 3.14.6, **133 tests passed**, with the opt-in live test
excluded. Ruff passed. The final place-row preflight was additionally checked by
all 58 poster acceptance tests. The checks cover all four new themes across both
layouts and A3/A4 orientations, editable SVG, physical PDF/PNG dimensions, font
embedding, outline text, twelve places, invalid coordinates/IDs, text overflow,
clipped/overlapping markers, offline geometry reuse and portable ZIP reproduction.

Python, CLI and real MCP calls produced equal poster scene hashes. Revision tests
cover whole-list replacement/removal, undo, explicit refresh with changes, request
deduplication, cancellation and failed refresh preserving earlier outputs. The
existing refresh publication-conflict test also remains in the suite.

Four classic PNGs (both original themes, A3 landscape and A4 portrait) were compared
with outputs from the pre-change `76a4373` source using the same dependencies.
All four were pixel-identical. Local evidence is in
`.cache/classic-regression/results.json`; test results are in
`.cache/test-results-v020.xml`. Generated evidence is excluded from Git.

The six-theme [gallery](posters.md) and a blueprint guide were rendered and visually
inspected using the previously saved Kadıköy snapshot. No public data requests were
made. Title, place numbers/list, physical scale and attribution were checked.
The gallery's source geometry was acquired on 12 October; this is not a new survey.
`scripts/poster_gallery.py` also generates a fully offline synthetic gallery.

### Performance on this development machine

The unchanged 10,000-building / 2,000-road fixture was measured with network
connections disabled. Hardware: 24 physical / 32 logical cores, about 32 GiB RAM.

| Phase | Elapsed | Sampled peak RSS |
|---|---:|---:|
| Cold A3 300 DPI PNG + SVG + PDF + ZIP | 21.29 s | 368 MiB |
| Warm geometry, fresh 72 DPI preview | 4.53 s | 258 MiB |
| Identical cached preview | 3.11 s | 205 MiB |
| Changed road colour preview | 4.10 s | 209 MiB |
| New poster frame with twelve places | 6.35 s | 204 MiB |
| Poster accent and place-order edit | 3.89 s | 209 MiB |

The existing 30-second cold-export, five-second warm-preview and 2-GiB sampled RSS
development targets passed. The first new poster frame includes geometry
preparation and is reported separately without a warm-preview time target.
These are observations, not guarantees for the unmeasured 4-core/16-GiB machine.
The final benchmark report is referenced by `.cache/benchmark-v020-final/latest.json`.

### Reproduce the release checks

```sh
uv sync --frozen --all-extras --dev
uv run ruff check src tests scripts
uv run pytest -m "not live" --basetemp .cache/pytest-v020
uv run python scripts/benchmark.py --output .cache/benchmark-v020
uv run python scripts/poster_gallery.py
uv build --no-sources --out-dir dist/v0.2.0
uv run python scripts/wheel_smoke.py --install dist/v0.2.0 --environment .cache/wheel-v020-check
```

Choose a new environment path for each wheel installation check. It verifies
binary-only dependency installation, bundled fonts, offline neon guide output in
all three formats, CLI equivalence and the real MCP stdio connection. The release
gate also checks package/public/lockfile versions; MCP reads the public version.

The 0.2.0 wheel and source distribution were built locally. The wheel was installed
with binary-only dependencies into a new `.cache/wheel-v020-verified` environment,
then verified under Python isolated mode from `site-packages`. All checks above
passed, including the real SDK stdio connection. The result is recorded in
`.cache/wheel-smoke-result.json`. Initial offline installation lacked cached binary
packages; the successful installation used PyPI access, while map rendering used
only its synthetic pinned snapshot. Archive inspection confirmed source packages
exclude `.cache`, `.venv` and generated `outputs`, and include the new examples
and gallery. The final MCP/schema/release checks also passed (16 tests).

### Historical open gates — 13 October 2026

- The nine-configuration GitHub Actions matrix remains configured. This checkout's
  changes have not been submitted to or verified by remote CI in this session.
- Manual Inkscape GUI editing acceptance is pending: no Inkscape executable was
  available through PATH or the standard Windows installation location. Editable
  text, vector marker paths and IDs are verified in the output tests.
- The three-user pilot and 4-core/16-GiB reference-machine benchmark remain pending.
- No v0.2.0 tag, GitHub release or PyPI upload was created during implementation.

## v0.1.0 reference record

Recorded on 12 October 2026. The implementation and local installable packages are
available; this is not a claim that the human pilot or all release gates have run.
The historical gates below are not additional v0.2.0 publication requirements;
the current scope and actual results are recorded at the top of this document.

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

## Historical open gates — v0.1.0

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
