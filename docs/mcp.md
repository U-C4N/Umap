# Local MCP workflow

Install `.[mcp]` and launch `umap-art mcp --workspace <absolute-directory>` from
the installed Python environment. The official SDK v2 runs the stdio transport.
This server has no LLM provider dependency and needs no model API key.

| Tool | Contract |
|---|---|
| `find_map_location` | Query and optional country code → up to five persisted candidates |
| `list_styles` | Themes, paint fields and supported views |
| `create_map` | Validated recipe plus optional candidate ID/request ID → map/revision/job IDs |
| `inspect_map` | Current recipe, history, pinned data, jobs, artifacts and diagnostics |
| `edit_map` | `map_id`, `base_revision`, targeted `changes` or `restore_revision` |
| `refresh_map_data` | Fetch new data and commit only if the base revision still matches |
| `render_map` | Render a chosen revision; optional formats or small preview |
| `get_job` | State, error, results and artifact identities |
| `cancel_job` | Cancel queued/running work without removing older outputs |
| `get_artifact` | Metadata, local path and optional native PNG preview |

## Typical interaction

1. Find a location and choose the correct context. A raw `area.place` is not accepted
   by `create_map`; select a returned `candidate_id` or provide coordinates/bbox.
2. Create the map. Poll `get_job` until a terminal state.
3. Inspect it and note `revision`.
4. Edit `{"style":{"layers":{"roads":{"stroke":"#B34A44"}}}}`, passing that
   `base_revision`. The response includes a structural before/after diff and a
   preview job.
5. Restore an earlier revision using `restore_revision`, or export the current
   revision with `render_map`.

Updates commit a new revision immediately; preview is not an extra user-approval
gate. A failed preview leaves the revision and previous outputs inspectable. Source
data refresh is a separate operation. Conflicts return `REVISION_CONFLICT` instead
of silently overwriting another edit. Optional `request_id` values deduplicate
repeated mutation requests; reusing an ID with different arguments is an error.

## Jobs and files

There is one active worker and at most four queued jobs per workspace. State:
`queued → running → succeeded/failed/cancelled/interrupted`, with `cancelling`
while cancellation is requested. Runtime is bounded to 300 seconds. Each job owns
an isolated process. Parent-pipe EOF, cancellation and shutdown terminate owned
work; a reopened workspace marks unfinished jobs interrupted. One server process
owns a workspace at a time.

All model-supplied snapshot paths and output artifacts must remain within the
workspace after symlink/junction resolution. Provider endpoints are trusted startup
configuration (`--photon-url`, `--overpass-url`, `--overture-catalog-url`), not arbitrary
tool-selected URLs. Writes publish complete artifacts atomically; normal operations
never overwrite user files.

`get_artifact(include_preview=true)` returns a PNG preview at most 1024 pixels on
its long edge and below 1 MiB. Full files up to 16 MiB can be read at
`umap://artifacts/{artifact_id}`. Larger files remain available at their registered
local path with size/hash metadata; a resource read returns `ARTIFACT_TOO_LARGE`.
Larger files can also be read at `umap://artifact-chunks/{artifact_id}/{offset}`
with a byte offset starting at zero, advancing by the returned byte count until
the advertised size is reached. Each response is at most 1 MiB; concatenate the
decoded bytes and verify the artifact SHA-256. Metadata includes the URI template.
Clients differ in how they display local files. Saved maps and final artifacts
are not automatically deleted.

Remote HTTP, authentication, multiple tenants and standard MCP Tasks extension
support are outside this local server. The job IDs above belong to the application.
