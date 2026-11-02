"""Local place lists and portable, content-addressed reference photographs."""
from __future__ import annotations

import csv
import hashlib
import io
import uuid
from pathlib import Path

from PIL import Image
from pydantic import ValidationError

from .errors import UmapError
from .models import Place

_HEADERS = {"ad": "name", "label": "name", "enlem": "latitude", "boylam": "longitude",
            "not": "note", "yön": "bearing", "fotoğraf": "reference_photo"}


def read_places_csv(path: str | Path) -> list[Place]:
    """Read UTF-8 CSV in file order. Photo paths are relative to the CSV file."""
    path = Path(path)
    places, ids = [], set()
    line = 1
    try:
        with path.open(encoding="utf-8-sig", newline="") as stream:
            reader = csv.reader(stream, strict=True)
            header = [h.strip().lower() for h in next(reader, [])]
            header = [_HEADERS.get(h, h) for h in header]
            required = {"name", "latitude", "longitude"}
            optional = {"id", "note", "bearing", "reference_photo"}
            if (not required.issubset(header) or set(header) - required - optional
                    or len(header) != len(set(header))):
                raise ValueError("Expected unique name, latitude and longitude columns; "
                                 "optional columns are id, note, bearing and reference_photo")
            for row in reader:
                line = reader.line_num
                if not row:
                    continue
                if len(row) != len(header):
                    raise ValueError("Column count differs from the header")
                fields = dict(zip(header, (value.strip() for value in row)))
                name = fields["name"]
                coords = (float(fields["longitude"]), float(fields["latitude"]))
                identity = fields.get("id") or hashlib.sha256(
                    f"{name}|{coords}".encode()).hexdigest()[:16]
                if identity in ids:
                    raise ValueError("Duplicate place ID; assign distinct IDs for identical places")
                if len(places) >= 12:
                    raise ValueError("A guide supports at most twelve places")
                photo = fields.get("reference_photo")
                places.append(Place(id=identity, label=name, coordinates=coords,
                              note=fields.get("note", ""), bearing=fields.get("bearing") or None,
                              reference_photo=str((path.parent / photo).resolve()) if photo else None))
                ids.add(identity)
    except (ValueError, csv.Error, OSError) as exc:
        if isinstance(exc, csv.Error):
            line = reader.line_num
        reason = exc.errors()[0]["msg"] if isinstance(exc, ValidationError) else str(exc)
        raise UmapError("INVALID_PLACES_CSV", f"CSV row {line}: {reason}", {"row": line}) from exc
    return places


def store_photo(source: Path, directory: Path) -> Path:
    """Validate and pin the exact input bytes before rendering or queuing a revision."""
    try:
        if not source.is_file() or source.stat().st_size > 20 * 1024**2:
            raise ValueError("Expected a local image of at most 20 MiB")
        data = source.read_bytes()
        with Image.open(io.BytesIO(data), formats=("JPEG", "PNG")) as photo:
            if photo.width * photo.height > 40_000_000:
                raise ValueError("Reference photograph exceeds 40 megapixels")
            extension = "jpg" if photo.format == "JPEG" else "png"
            photo.load()
    except (OSError, ValueError, Image.DecompressionBombError) as exc:
        raise UmapError("INVALID_REFERENCE_PHOTO", f"Cannot read reference photo {source.name}: {exc}") from exc
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / f"{hashlib.sha256(data).hexdigest()}.{extension}"
    if not target.exists():
        temporary = directory / f".{uuid.uuid4().hex}.tmp"
        try:
            temporary.write_bytes(data)
            temporary.replace(target)
        finally:
            temporary.unlink(missing_ok=True)
    return target
