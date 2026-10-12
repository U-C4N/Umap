"""Isolated render worker. Parent pipe EOF prevents orphaned workers."""
from __future__ import annotations

import json
import os
import sys
import threading
from pathlib import Path


def _watch_owner():
    while sys.stdin.buffer.read(1):
        pass
    # The owner is gone (or cancelled this job). Never keep rendering unattended.
    os._exit(143)


def main():
    request = json.loads(sys.stdin.buffer.readline())
    # Load native array/rendering libraries before a thread blocks in Windows
    # stdin: some native startup paths inspect CRT stdio and share its locks.
    from . import renderer  # noqa: F401
    from .errors import UmapError
    from .models import MapSpec
    from .service import render
    threading.Thread(target=_watch_owner, name="umap-owner-watchdog", daemon=True).start()
    try:
        result = render(MapSpec.model_validate(request["spec"]), output_dir=request["output_dir"],
                        refresh=request.get("refresh", False))
        message = {"result": result.model_dump(mode="json")}
    except Exception as exc:
        message = {"error": exc.to_dict() if isinstance(exc, UmapError) else
                   {"code": "RENDER_FAILED", "message": str(exc)}}
    destination = Path(request["result_file"])
    temporary = destination.with_suffix(".tmp")
    temporary.write_text(json.dumps(message, ensure_ascii=False), encoding="utf-8")
    temporary.replace(destination)
    # Bypass interpreter shutdown while the daemon is blocked in buffered stdin.
    os._exit(0)


if __name__ == "__main__":
    main()
