"""Build the real-data release showcase and verify offline revision/portability.

Uses only the bundled Kadikoy snapshot and the public render pipeline. PNG contact
sheets are presentation assets, not new map layouts. The evidence records actual
checks; it does not claim an Inkscape GUI edit or an independent geographic survey.
"""

from __future__ import annotations

import argparse
import json
import os
import socket
import xml.etree.ElementTree as ET
import zipfile
from importlib.resources import as_file, files
from pathlib import Path, PureWindowsPath
from unittest.mock import patch

from PIL import Image, ImageDraw, ImageFont

from umap_art import MapSpec, render
from umap_art.scene import FONT_PATH, stable_id
from umap_art.storage import atomic_json, digest, file_hash
from umap_art.styles import THEMES

SVG = "{http://www.w3.org/2000/svg}"
LAYER_NAMES = ("buildings", "roads", "green", "water")


def svg_contract(path: Path) -> dict:
    """Read geometry separately from paint so a revision cannot hide map drift."""
    root = ET.parse(path).getroot()
    identifiers = [e.attrib["id"] for e in root.iter() if "id" in e.attrib]
    elements = {e.attrib["id"]: e for e in root.iter() if "id" in e.attrib}
    if len(identifiers) != len(elements):
        raise ValueError(f"Duplicate SVG identifiers: {path}")
    if list(root.iter(f"{SVG}image")):
        raise ValueError(f"Unexpected raster image in editable SVG: {path}")
    if not list(root.iter(f"{SVG}text")):
        raise ValueError(f"SVG has no editable text: {path}")

    def geometry(group):
        if group is None:
            return {}
        return {e.attrib["id"]: [p.attrib.get("d") for p in e.iter(f"{SVG}path")]
                for e in group if "id" in e.attrib}

    layers = {name: geometry(elements.get(name)) for name in LAYER_NAMES}
    text = {key: "".join(e.itertext()).strip() for key, e in elements.items()
            if any(True for _ in e.iter(f"{SVG}text"))}
    return {"page": {key: root.attrib.get(key) for key in ("width", "height", "viewBox")},
            "geometry_hash": digest(layers),
            "feature_paths": sum(len(layer) for layer in layers.values()),
            "markers": geometry(elements.get("places")), "text": text}


def revision_checks(before: dict, after: dict, before_manifest: dict, after_manifest: dict) -> dict:
    checks = {
        "same_dataset": before_manifest["dataset_id"] == after_manifest["dataset_id"],
        "same_extent": before_manifest["bounds"] == after_manifest["bounds"],
        "same_scale": before_manifest["scale_denominator"] == after_manifest["scale_denominator"],
        "same_page": before["page"] == after["page"],
        "same_map_geometry": before["geometry_hash"] == after["geometry_hash"],
        "same_marker_ids_and_positions": before["markers"] == after["markers"],
        "title_changed": before["text"].get("title") != after["text"].get("title"),
        "theme_changed": before_manifest["style"]["theme"] != after_manifest["style"]["theme"],
    }
    before_places = before_manifest["places"]
    after_places = after_manifest["places"]
    checks["place_order_changed"] = [p["id"] for p in before_places] != [
        p["id"] for p in after_places]
    checks["numbers_follow_new_order"] = all(
        after["text"].get(stable_id(place["id"], "place-number")) == str(i + 1)
        for i, place in enumerate(after_places)
    )
    if not all(checks.values()):
        raise ValueError(f"Revision check failed: {checks}")
    return checks


def extract_project(archive: Path, destination: Path) -> None:
    """Extract a generated project only when every entry stays within its folder."""
    destination = destination.resolve()
    destination.mkdir(parents=True, exist_ok=False)
    with zipfile.ZipFile(archive) as bundle:
        for name in bundle.namelist():
            if PureWindowsPath(name).is_absolute() or not (
                destination / name
            ).resolve().is_relative_to(destination):
                raise ValueError(f"Unsafe project archive entry: {name}")
        bundle.extractall(destination)


def sheet(destination: Path, cards: list[tuple[str, Path]], *, title: str,
          subtitle: str, columns: int = 3, tile_width: int = 360) -> None:
    """Compose un-cropped real outputs, preserving each page's proportions."""
    gap, margin, header, footer = 28, 36, 125, 90
    image_height = round(tile_width * 297 / 210)
    card_height = image_height + 48
    rows = (len(cards) + columns - 1) // columns
    width = 2 * margin + columns * tile_width + (columns - 1) * gap
    height = header + rows * card_height + (rows - 1) * gap + footer
    canvas = Image.new("RGB", (width, height), "#ECEEE9")
    draw = ImageDraw.Draw(canvas)
    headline = ImageFont.truetype(str(FONT_PATH), 31)
    body = ImageFont.truetype(str(FONT_PATH), 15)
    caption = ImageFont.truetype(str(FONT_PATH), 18)
    draw.text((margin, 22), "UMAP ART / 0.2", font=body, fill="#52665B")
    draw.text((margin, 47), title, font=headline, fill="#173D32")
    draw.text((margin, 91), subtitle, font=body, fill="#52665B")
    for index, (label, path) in enumerate(cards):
        x = margin + (index % columns) * (tile_width + gap)
        y = header + (index // columns) * (card_height + gap)
        draw.text((x, y), label, font=caption, fill="#173D32")
        draw.rectangle((x - 1, y + 32, x + tile_width + 1, y + 33 + image_height),
                       fill="#FFFFFF", outline="#D0D7CE", width=1)
        with Image.open(path) as image:
            preview = image.convert("RGB")
            preview.thumbnail((tile_width, image_height), Image.Resampling.LANCZOS)
        canvas.paste(preview, (x + (tile_width - preview.width) // 2,
                              y + 33 + (image_height - preview.height) // 2))
    draw.text((margin, height - 63),
              "Kadıköy · 1:5000 · Saved data acquired 12 October 2026", font=body, fill="#52665B")
    draw.text((margin, height - 37),
              "Map data © OpenStreetMap contributors and Overture Maps · ODbL", font=body,
              fill="#52665B")
    canvas.save(destination)


def build_showcase(output: Path, *, dpi: int = 300) -> dict:
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    resource = files("umap_art").joinpath("examples/kadikoy")
    calls = []
    records = {}
    results = {}

    def no_network(*args, **kwargs):
        calls.append("blocked")
        raise RuntimeError("Release showcase networking is disabled")

    with (
        as_file(resource.joinpath("snapshot.json")) as snapshot,
        patch.dict(os.environ, {"UMAP_CACHE_DIR": str(output / "cache")}),
        patch.object(socket.socket, "connect", side_effect=no_network),
        patch.object(socket.socket, "connect_ex", side_effect=no_network),
        patch.object(socket, "create_connection", side_effect=no_network),
        patch.object(socket, "getaddrinfo", side_effect=no_network),
    ):
        def preset(name):
            spec = MapSpec.model_validate_json(resource.joinpath(f"{name}.json").read_text("utf-8"))
            spec.source.snapshot = str(snapshot)
            spec.page.dpi = dpi
            return spec

        def run(name, spec):
            result = render(spec, output_dir=output / name)
            if result.diagnostics:
                raise ValueError(f"Unreviewed showcase diagnostics in {name}: {result.diagnostics}")
            results[name] = result
            manifest = json.loads(Path(result.manifest_path).read_text("utf-8"))
            records[name] = {
                "recipe": str(Path(result.recipe_path).relative_to(output)).replace("\\", "/"),
                "manifest": str(Path(result.manifest_path).relative_to(output)).replace("\\", "/"),
                "dataset_id": result.dataset_id, "scene_hashes": result.scene_hashes,
                "bounds": manifest["bounds"], "scale_denominator": manifest["scale_denominator"],
                "layout": manifest["page"]["layout"],
                "artifacts": [{"path": str(Path(a.path).relative_to(output)).replace("\\", "/"),
                               "sha256": a.sha256, "view": a.view} for a in result.artifacts],
            }
            return result

        for theme in THEMES:
            spec = preset("poster")
            spec.style.theme = theme
            run(f"themes/{theme}", spec)
        run("guide", preset("guide"))
        run("atlas", preset("atlas"))
        edited = preset("poster")
        edited.title = "Benim Kadıköy’üm"
        edited.page.title_size_pt = 22
        edited.style.theme = "neon"
        edited.places = list(reversed(edited.places))
        before = results["themes/vintage"]
        after = run("revision/after", edited)
        before_manifest = json.loads(Path(before.manifest_path).read_text("utf-8"))
        after_manifest = json.loads(Path(after.manifest_path).read_text("utf-8"))
        checks = revision_checks(
            svg_contract(Path(before.recipe_path).parent / "general.svg"),
            svg_contract(Path(after.recipe_path).parent / "general.svg"),
            before_manifest, after_manifest,
        )
        archive = next(Path(a.path) for a in after.artifacts if a.mime_type == "application/zip")
        extract_project(archive, output / "portable/input")
        reproduced = run("portable/rerender", output / "portable/input/recipe.json")
        checks["portable_scene_equal"] = reproduced.scene_hashes == after.scene_hashes
        original_hashes = {f"{a.view}/{a.mime_type}": a.sha256 for a in after.artifacts if a.view}
        reproduced_hashes = {f"{a.view}/{a.mime_type}": a.sha256 for a in reproduced.artifacts if a.view}
        checks["portable_artifacts_equal_on_this_runtime"] = original_hashes == reproduced_hashes
        checks["all_outputs_share_dataset"] = len({r.dataset_id for r in results.values()}) == 1
        checks["zero_network_attempts"] = not calls
        if not all(checks.values()):
            raise ValueError(f"Showcase check failed: {checks}")

    def png(name, view="general"):
        return Path(results[name].recipe_path).parent / f"{view}.png"

    sheet(output / "theme-gallery.png", [(theme, png(f"themes/{theme}")) for theme in THEMES],
          title="One place. Six expressions.", subtitle="The same scale, map geometry and selected points.")
    atlas_cards = [(label, png("atlas", view)) for label, view in (
        ("01 / Figure-ground", "figure_ground"), ("02 / Roads", "roads"),
        ("03 / Green spaces", "green"), ("04 / Water", "water"))]
    sheet(output / "atlas-sheet.png", atlas_cards, title="Read the neighborhood.",
          subtitle="Four aligned analytical pages from the same saved dataset.", columns=2)
    sheet(output / "release-showcase.png", [
        ("01 / READ · Spatial atlas", output / "atlas-sheet.png"),
        ("02 / SHARE · Field guide", png("guide")),
        ("03 / KEEP · Personal poster", png("themes/vintage")),
    ], title="One neighborhood. Three ways to work.",
          subtitle="A4 · Editable vectors · Offline revisions · One portable project per output")
    sheet(output / "revision-comparison.png", [
        ("BEFORE / Vintage", png("themes/vintage")), ("AFTER / Neon + title + point order", png("revision/after"))
    ], title="Change the design. Keep the geography.",
          subtitle="Network blocked. Same dataset, geographic paths and marker positions.",
          columns=2, tile_width=500)
    images = {path.name: file_hash(path) for path in output.glob("*.png")}
    evidence = {"schema_version": "1", "dataset_id": after.dataset_id, "dpi": dpi,
                "checks": checks, "outputs": records, "images": images,
                "limits": ["Atlas and poster use different map frames; dataset identity is shared.",
                           "Byte equality is checked only within this runtime, not across platforms.",
                           "SVG structure is inspected; an Inkscape GUI edit is not performed.",
                           "Selected points are examples, not verified venues or a route."]}
    atomic_json(output / "index.json", evidence)
    return evidence


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("outputs/release-showcase"),
                        help="New directory; existing evidence is never overwritten")
    parser.add_argument("--dpi", type=int, default=300, choices=range(72, 601), metavar="72..600")
    args = parser.parse_args()
    evidence = build_showcase(args.output, dpi=args.dpi)
    print(json.dumps({"index": str(args.output.resolve() / "index.json"),
                      "checks": evidence["checks"], "dataset_id": evidence["dataset_id"]}))


if __name__ == "__main__":
    main()
