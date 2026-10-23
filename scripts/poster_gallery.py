"""Render an offline, reproducible theme gallery and both poster layouts.

Defaults to clearly labelled synthetic map data. Pass --snapshot to use an
existing Kadikoy snapshot covering A4 portrait at 1:5000. No data is downloaded.
"""
from __future__ import annotations

import argparse
import json
import os
import socket
from pathlib import Path
from unittest.mock import patch

from PIL import Image, ImageDraw, ImageFont
from pyproj import Transformer
from shapely import transform
from shapely.geometry import LineString, Polygon, box, mapping

from umap_art import MapSpec, render
from umap_art.geometry import compute_extent
from umap_art.models import Dataset, Feature
from umap_art.scene import FONT_PATH
from umap_art.storage import atomic_json, digest
from umap_art.styles import THEMES


def synthetic_dataset(spec):
    extent = compute_extent(spec)
    west, south, east, north = extent.bounds
    inverse = Transformer.from_crs(extent.crs, "EPSG:4326", always_xy=True)
    width, height = east-west, north-south

    def geometry(value):
        return mapping(transform(value, inverse.transform, interleaved=False))

    features = [Feature(id="sample-water", layer="water", geometry=geometry(Polygon([
        (west, south), (west+width*0.25, south), (west+width*0.18, south+height*0.3),
        (west+width*0.30, north), (west, north)])))]
    for row in range(24):
        for col in range(14):
            x, y = west+width*(0.35+col*0.045), south+height*(0.03+row*0.04)
            features.append(Feature(id=f"sample-building-{row}-{col}", layer="buildings",
                geometry=geometry(box(x, y, x+width*0.03, y+height*0.025))))
    for row in range(25):
        y = south+height*(0.02+row*0.04)
        features.append(Feature(id=f"sample-road-h-{row}", layer="roads",
            properties={"highway": "primary" if row % 5 == 0 else "residential"},
            geometry=geometry(LineString([(west+width*0.32, y), (east, y)]))))
    for col in range(15):
        x = west+width*(0.342+col*0.045)
        features.append(Feature(id=f"sample-road-v-{col}", layer="roads",
            properties={"highway": "secondary"},
            geometry=geometry(LineString([(x, south), (x, north)]))))
    features.append(Feature(id="sample-park", layer="green", geometry=geometry(box(
        west+width*0.26, south+height*0.36, west+width*0.32, south+height*0.7))))
    return Dataset(bbox=extent.bbox, features=features, sources=[{
        "provider": "synthetic", "license": "CC0-1.0", "fixture_version": "poster-1",
        "description": "Generated example geometry, not a real geographic survey"}])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("outputs/poster-gallery"))
    parser.add_argument("--gallery", type=Path)
    parser.add_argument("--snapshot", type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    spec = MapSpec(area={"center": [29.025, 40.985]},
        page={"size": "A4", "orientation": "portrait", "layout": "poster", "dpi": 100},
        title="Kadıköy" if args.snapshot else "Bir şehir, altı yorum",
        subtitle="Seçtiğim noktalar" if args.snapshot else "Sentetik örnek · Synthetic sample",
        source={"offline": True, "include_ocean": bool(args.snapshot)},
        places=[{"id": "meeting", "label": "Buluşma noktası", "coordinates": [29.027, 40.987]},
                {"id": "break", "label": "Mola noktası", "coordinates": [29.03, 40.984]},
                {"id": "view", "label": "Manzara noktası", "coordinates": [29.026, 40.982]}])
    if args.snapshot:
        spec.source.snapshot = str(args.snapshot.resolve())
    else:
        dataset = synthetic_dataset(spec)
        snapshot = args.output / "input-snapshot.json"
        atomic_json(snapshot, {"schema_version": "1", "dataset_id": digest(dataset.model_dump(mode="json")),
                               "dataset": dataset.model_dump(mode="json")})
        spec.source.snapshot = str(snapshot.resolve())
    gallery = Image.new("RGB", (3*340, 2*502), "#E6E6E6")
    draw = ImageDraw.Draw(gallery)
    font = ImageFont.truetype(str(FONT_PATH), 17)
    records = []
    with (patch.dict(os.environ, {"UMAP_CACHE_DIR": str(args.output.resolve() / "cache")}),
          patch.object(socket.socket, "connect", side_effect=RuntimeError("Gallery networking disabled"))):
        for index, theme in enumerate(THEMES):
            spec.style.theme = theme
            result = render(spec, output_dir=args.output / theme)
            png = next(a for a in result.artifacts if a.mime_type == "image/png")
            with Image.open(png.path) as preview:
                tile = preview.convert("RGB")
                tile.thumbnail((320, 453), Image.Resampling.LANCZOS)
            x, y = (index % 3)*340+10, (index // 3)*502+34
            gallery.paste(tile, (x, y))
            draw.text((x, y-26), theme, font=font, fill="#222222")
            records.append({"theme": theme, "recipe": result.recipe_path, "manifest": result.manifest_path})
        spec.page.layout, spec.style.theme = "guide", "blueprint"
        guide = render(spec, output_dir=args.output / "guide")
    destination = args.gallery or args.output / "theme-gallery.png"
    destination.parent.mkdir(parents=True, exist_ok=True)
    gallery.save(destination)
    atomic_json(args.output / "index.json", {"gallery": str(destination.resolve()),
        "themes": records, "guide": guide.recipe_path, "network": "disabled"})
    print(json.dumps({"gallery": str(destination.resolve()), "guide": guide.recipe_path}))


if __name__ == "__main__":
    main()
