"""Compose print pages from a shared, physically scaled map scene."""
from __future__ import annotations

import math
from dataclasses import replace

from pyproj import Geod, Transformer

from .errors import UmapError
from .scene import (
    PT_PER_MM,
    SceneGroup,
    SceneImage,
    ScenePaint,
    ScenePath,
    SceneText,
    _circle,
    _measure,
    _preflight_text,
    _rect,
    place_anchors,
)
from .styles import THEMES


def _lines(text, width, size, *, bold=False):
    lines = []
    for paragraph in text.splitlines():
        line = ""
        for word in paragraph.split():
            candidate = f"{line} {word}".strip()
            if line and _measure(SceneText("note", candidate, 0, 0, size, bold=bold))[0] > width:
                lines.append(line)
                line = word
            else:
                line = candidate
        lines.append(line)
    return lines


def _pocket_back(front, spec, ink, accent):
    mm = PT_PER_MM
    margin = spec.page.margin_mm*mm
    width = front.width_pt-2*margin
    top = front.height_pt-margin
    heading = "Duraklar ve notlar" if spec.language == "tr" else "Places and notes"
    texts = [SceneText("section", heading, margin+10, top-9, 9, ink, bold=True),
             SceneText("title", spec.title, margin, top-34, 20, ink, bold=True)]
    rules = [_rect("back-accent", margin, top-9, 3, 9, ScenePaint(fill=accent))]
    y = top-51
    for n, place in enumerate(spec.places, 1):
        rules.append(ScenePath(f"rule-{n}", ((margin, y), (margin+width, y)), (1, 2),
                               ScenePaint(stroke=ink, width_pt=0.4, opacity=0.45), False))
        y -= 12
        texts.append(SceneText(f"number-{n}", f"{n:02}", margin, y, 9, ink))
        for i, line in enumerate(_lines(place.label, width-10*mm, 11, bold=True)):
            texts.append(SceneText(f"place-{n}-{i}", line, margin+10*mm, y, 11, ink, bold=True))
            y -= 13
        for i, line in enumerate(_lines(place.note, width-10*mm, 8)):
            texts.append(SceneText(f"note-{n}-{i}", line, margin+10*mm, y, 8, ink))
            y -= 10
        y -= 2
    if y < margin+6:
        raise UmapError("TEXT_OVERFLOW", "Shorten place names or notes to fit the A5 reverse")
    if y-margin >= 30*mm:
        y -= 11
        texts.append(SceneText("notes-heading", "Saha notlarım" if spec.language == "tr"
                               else "Field notes", margin, y, 9, ink))
        for i in range(int((y-margin-12)/(9*mm))):
            y -= 9*mm
            rules.append(ScenePath(f"writing-line-{i}", ((margin, y), (margin+width, y)), (1, 2),
                                   ScenePaint(stroke=ink, width_pt=0.35, opacity=0.28), False))
    texts.append(SceneText("folio", "02 / 02", margin+width, margin, 8, ink, "right"))
    for t in texts:
        _preflight_text(t, width if t.align == "right" else margin+width-t.x)
    return replace(front, view="pocket-back", groups=(front.groups[0], SceneGroup("rules", tuple(rules))),
                   texts=tuple(texts), diagnostics=())


def _camera_arrow(origin, angle, frame, ink, accent):
    # Keep the tip visible at a frame edge by shifting the arrow inward.
    x, y = origin
    dx, dy = math.cos(angle), math.sin(angle)
    mx, my, mw, mh = frame
    reach = 11*PT_PER_MM
    tx = min(max(x+reach*dx, mx+reach), mx+mw-reach)
    ty = min(max(y+reach*dy, my+reach), my+mh-reach)
    tail = (tx-reach*dx, ty-reach*dy)
    a = (tx-8*dx-4*dy, ty-8*dy+4*dx)
    b = (tx-8*dx+4*dy, ty-8*dy-4*dx)
    silhouette = (tail, (tx, ty), a, b, (tx, ty))
    return SceneGroup("camera", (
        ScenePath("camera-leader", (origin, tail), (1, 2), ScenePaint(stroke=ink, width_pt=0.8)),
        ScenePath("camera-halo", silhouette, (1, 2, 2, 2, 2),
                  ScenePaint(fill="#FFFFFF", stroke="#FFFFFF", width_pt=5)),
        ScenePath("camera-bearing", silhouette, (1, 2, 2, 2, 2),
                  ScenePaint(fill=accent, stroke=accent, width_pt=2.8)),
        _circle("camera-position", x, y, 4.5, ScenePaint(fill=ink, stroke="#FFFFFF", width_pt=1.8))))


def _field_cards(base, prepared, spec, ink, accent):
    x, map_bottom, width, map_height = base.frame
    top, right = base.height_pt-x, x+width
    map_top = map_bottom+map_height
    anchors = place_anchors(prepared, spec)
    project = Transformer.from_crs("EPSG:4326", prepared.crs, always_xy=True)
    geod = Geod(ellps="WGS84")
    turkish = spec.language == "tr"
    heading = "AYNI KADRAJ" if turkish else "REPEAT PHOTOGRAPHY"
    panel_bottom = map_bottom-41
    split = x+width*0.62
    gutter = 12
    photo_top, photo_bottom = panel_bottom-24, x+16
    photo_width = split-x-gutter/2
    note_x = split+gutter/2
    note_width = right-note_x
    frame_paint = ScenePaint(stroke=ink, width_pt=0.6, opacity=0.35)
    geometry = [
        _rect("masthead-accent", x, top-10, 3, 10, ScenePaint(fill=accent)),
        _rect("map-outline", x, map_bottom, width, map_height, frame_paint),
        _rect("station-rule", x, panel_bottom, width, 0.5, ScenePaint(fill=ink, opacity=0.35)),
        _rect("footer-rule", x, x+9, width, 0.55, ScenePaint(fill=ink, opacity=0.4)),
    ]
    for n, place in enumerate(spec.places, 1):
        lon, lat = place.coordinates
        fx, fy = project.transform(*geod.fwd(lon, lat, place.bearing, 10)[:2])
        cx, cy = project.transform(lon, lat)
        arrow = _camera_arrow(anchors[place.id], math.atan2(fy-cy, fx-cx), base.frame, ink, accent)
        station = SceneText("station", place.label, x, top-40, spec.page.title_size_pt or 22, ink, bold=True)
        _, height, descent = _preflight_text(station, width)
        if station.y-descent <= map_top+17 or station.y+height-descent > top-14:
            raise UmapError("TEXT_OVERFLOW", "Station name does not fit the field card header")
        scale = f"1 : {base.scale_denominator:,.0f}".replace(",", " ")
        cardinal = (("K", "KD", "D", "GD", "G", "GB", "B", "KB") if turkish
                    else ("N", "NE", "E", "SE", "S", "SW", "W", "NW"))
        direction = cardinal[int((place.bearing+22.5)//45) % 8]
        position = SceneText("position", f"{lat:.5f},  {lon:.5f}", x, panel_bottom+9, 12, ink)
        bearing = SceneText("bearing", f"{place.bearing:g}°   {direction}", split+10, panel_bottom+8,
                            14, ink, bold=True)
        _preflight_text(position, split-position.x-6)
        _preflight_text(bearing, right-bearing.x-4)
        texts = [*base.texts, station, position, bearing,
                 SceneText("series", f"U-MAP   /   {heading}", x+10, top-9, 9, ink, bold=True),
                 SceneText("folio", f"{n:02} / {len(spec.places):02}", right, top-9,
                           8, ink, "right"),
                 SceneText("map-section", "01   ÇEKİM NOKTASI" if turkish else "01   CAMERA STATION",
                           x, map_top+7, 8, ink, bold=True),
                 SceneText("scale", scale, right, map_top+7, 8, ink, "right"),
                 SceneText("position-key", "KONUM" if turkish else "POSITION", x, map_bottom-12,
                           7.5, ink),
                 SceneText("bearing-key", "YÖN  /  GERÇEK KUZEY" if turkish else "BEARING  /  TRUE NORTH",
                           split+10, map_bottom-12, 7.5, ink),
                 SceneText("reference-key", "02   REFERANS KADRAJ" if turkish else "02   REFERENCE FRAME",
                           x, photo_top+7, 8, ink, bold=True),
                 SceneText("note-key", "SAHA NOTU" if turkish else "FIELD NOTE", note_x,
                           photo_top+7, 8, ink, bold=True)]
        lines = _lines(place.note, note_width, 10)
        decorations = list(geometry)
        y = photo_top-12
        for i, line in enumerate(lines):
            item = SceneText(f"note-{i}", line, note_x, y, 10, ink)
            _preflight_text(item, note_width)
            texts.append(item)
            y -= 14
        if y < photo_bottom+22:
            raise UmapError("TEXT_OVERFLOW", "Shorten the field note to fit the card", {"place_id": place.id})
        texts.append(SceneText("date-key", "ÇEKİM TARİHİ" if turkish else "VISIT DATE",
                               note_x, photo_bottom+16, 7.5, ink, bold=True))
        decorations.append(_rect("date-line", note_x, photo_bottom+1, note_width, 0.5, frame_paint))
        for t in texts:
            _preflight_text(t, width)
        yield replace(base, view=f"field-card-{n:02}", groups=(*base.groups, SceneGroup("card", tuple(decorations)), arrow),
                      texts=tuple(texts), image=SceneImage(place.reference_photo,
                      (x+1, photo_bottom+1, photo_width-2, photo_top-photo_bottom-2)))


def print_pages(base, prepared, spec):
    theme = THEMES[spec.style.theme]
    ink, accent = spec.style.ink or theme["ink"], spec.style.accent or theme["accent"]
    if spec.page.layout == "field_cards":
        return list(_field_cards(base, prepared, spec, ink, accent))
    return [replace(base, view="pocket-front"), _pocket_back(base, spec, ink, accent)]
