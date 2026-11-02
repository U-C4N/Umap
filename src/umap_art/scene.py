"""Immutable, renderer-independent scene in physical PostScript points.

The bottom-left of the page is (0, 0); all coordinates are points (1/72 inch).
No raster DPI enters layout. Geographical paths are clipped to ``frame``.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import asdict, dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from shapely.geometry import shape
from shapely.geometry.polygon import orient

from .errors import UmapError
from .layout import resolve_layout
from .models import Diagnostic, MapSpec, Paint
from .styles import LABELS, THEMES, VIEW_LAYERS, resolve_paint, validate_style

PT_PER_MM = 72 / 25.4
FONT_PATH = Path(__file__).parent / "assets" / "fonts" / "SpaceGrotesk-Regular.ttf"
BOLD_FONT_PATH = FONT_PATH.with_name("SpaceGrotesk-Bold.ttf")


@lru_cache(maxsize=4)
def _glyphs(font_path):
    from matplotlib.ft2font import FT2Font

    return frozenset(FT2Font(str(font_path)).get_charmap())


@dataclass(frozen=True)
class ScenePaint:
    fill: str | None = None
    stroke: str | None = None
    width_pt: float = 0
    opacity: float = 1
    dash_pt: tuple[float, ...] = ()

    @classmethod
    def from_paint(cls, paint: Paint) -> ScenePaint:
        return cls(paint.fill, paint.stroke, paint.width_mm * PT_PER_MM,
                   paint.opacity, tuple(v * PT_PER_MM for v in paint.dash_mm))


@dataclass(frozen=True)
class ScenePath:
    id: str
    vertices: tuple[tuple[float, float], ...]
    codes: tuple[int, ...]
    paint: ScenePaint
    clip: bool = True
    feature_id: str | None = None


@dataclass(frozen=True)
class SceneText:
    id: str
    text: str
    x: float
    y: float
    size_pt: float
    color: str = "#252A30"
    align: str = "left"
    clip: bool = False
    bold: bool = False

    @property
    def font_path(self):
        primary = BOLD_FONT_PATH if self.bold else FONT_PATH
        if all(ord(c) in _glyphs(primary) for c in self.text):
            return primary
        return FONT_PATH.with_name("DejaVuSans-Bold.ttf" if self.bold else "DejaVuSans.ttf")


@dataclass(frozen=True)
class SceneGroup:
    id: str
    paths: tuple[ScenePath, ...]


@dataclass(frozen=True)
class SceneImage:
    path: str  # Content-addressed path relative to the portable recipe.
    box: tuple[float, float, float, float]


@dataclass(frozen=True)
class Scene:
    view: str
    width_pt: float
    height_pt: float
    frame: tuple[float, float, float, float]
    groups: tuple[SceneGroup, ...]
    texts: tuple[SceneText, ...]
    scale_denominator: float
    crs: str
    diagnostics: tuple[Diagnostic, ...] = ()
    image: SceneImage | None = None

    def semantic_hash(self) -> str:
        # Diagnostics are delivery information, not visual scene content.
        data = asdict(self)
        data.pop("diagnostics")
        if not self.image:
            data.pop("image")
        for item in data["texts"]:
            if not item["bold"]:
                item.pop("bold")
        return hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=False,
                                        separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def stable_id(source: str, role: str) -> str:
    label = re.sub(r"[^a-zA-Z0-9_-]", "-", source)[:70]
    digest = hashlib.sha256(f"{source}|{role}".encode()).hexdigest()[:12]
    return f"feature-{label}-{role}-{digest}"


def _rect(identifier, x, y, w, h, paint, *, clip=False):
    return ScenePath(identifier, ((x, y), (x+w, y), (x+w, y+h), (x, y+h), (x, y)),
                     (1, 2, 2, 2, 79), paint, clip)


def _geometry_paths(geometry, transform):
    """Yield compound paths; opposite ring winding preserves polygon holes."""
    if geometry.is_empty:
        return
    if geometry.geom_type == "Polygon":
        geometry = orient(geometry, sign=1.0)
        vertices, codes = [], []
        for ring in [geometry.exterior, *geometry.interiors]:
            coords = [transform(x, y) for x, y, *_ in ring.coords]
            if len(coords) < 4:
                continue
            vertices.extend(coords)
            codes.extend([1] + [2] * (len(coords)-2) + [79])
        if vertices:
            yield tuple(vertices), tuple(codes)
    elif geometry.geom_type in ("LineString", "LinearRing"):
        vertices = tuple(transform(x, y) for x, y, *_ in geometry.coords)
        if len(vertices) > 1:
            yield vertices, (1,) + (2,) * (len(vertices)-1)
    elif geometry.geom_type in ("MultiPolygon", "MultiLineString", "GeometryCollection"):
        for part in geometry.geoms:
            yield from _geometry_paths(part, transform)


def _road_order(feature):
    props = feature.properties
    try:
        level = float(props.get("layer", 0))
        if not math.isfinite(level):
            level = 0
    except (ValueError, TypeError):
        level = 0
    def truth(name):
        return str(props.get(name, "no")).lower() not in ("no", "false", "0", "none", "")
    grade = -1 if truth("tunnel") else (1 if truth("bridge") else 0)
    importance = {"motorway": 9, "trunk": 8, "primary": 7, "secondary": 6,
                  "tertiary": 5, "residential": 4, "unclassified": 3,
                  "service": 2}.get(props.get("highway"), 1)
    return level, grade, importance, feature.id


def _measure(text: SceneText):
    from matplotlib.font_manager import FontProperties
    from matplotlib.textpath import TextToPath

    return TextToPath().get_text_width_height_descent(
        text.text, FontProperties(fname=str(text.font_path), size=text.size_pt), ismath=False)


def _preflight_text(text: SceneText, max_width: float):
    if any(c in text.text for c in "\r\n\t"):
        raise UmapError("TEXT_OVERFLOW", "Page labels must be single-line strings", {"id": text.id})
    cmap = _glyphs(text.font_path)
    missing = sorted({c for c in text.text if ord(c) not in cmap})
    if missing:
        raise UmapError("MISSING_GLYPH", "The bundled font cannot display all label characters",
                        {"id": text.id, "characters": missing})
    width, height, descent = _measure(text)
    if width > max_width:
        raise UmapError("TEXT_OVERFLOW", "Label exceeds the available page width",
                        {"id": text.id, "width_pt": width, "available_pt": max_width})
    return width, height, descent


def _nice_distance(target: float) -> float:
    exponent = 10 ** math.floor(math.log10(target))
    return max(v for v in (1, 2, 5, 10) if v * exponent <= target) * exponent


def _attribution(spec, prepared):
    value = "© OpenStreetMap contributors · openstreetmap.org/copyright"
    has_ocean = any(f.properties.get("subtype") == "ocean" or
                    f.properties.get("ocean") is True for f in prepared.features)
    if spec.source.include_ocean or has_ocean:
        value += " · Overture Maps"
    return value + " · ODbL"


def _circle(identifier, x, y, radius, paint):
    # Four cubic Beziers preserve editable vector circles in every renderer.
    r, c = radius, radius * 0.5522847498307936
    vertices = ((x+r, y), (x+r, y+c), (x+c, y+r), (x, y+r),
                (x-c, y+r), (x-r, y+c), (x-r, y), (x-r, y-c),
                (x-c, y-r), (x, y-r), (x+c, y-r), (x+r, y-c), (x+r, y))
    return ScenePath(identifier, vertices + (vertices[0],), (1,) + (4,)*12 + (79,), paint)


def _contrast_ink(color):
    rgb = [int(color[i:i+2], 16)/255 for i in (1, 3, 5)]
    linear = [c/12.92 if c <= 0.04045 else ((c+0.055)/1.055)**2.4 for c in rgb]
    luminance = sum(c*w for c, w in zip(linear, (0.2126, 0.7152, 0.0722)))
    return "#000000" if luminance > 0.179 else "#FFFFFF"


def place_anchors(prepared, spec):
    from pyproj import Transformer

    project = Transformer.from_crs("EPSG:4326", prepared.crs, always_xy=True)
    xmin, ymin, xmax, ymax = prepared.bounds
    mx, my, mw, mh = (v * PT_PER_MM for v in spec.page.frame_mm)
    anchors = {}
    for place in spec.places:
        px, py = project.transform(*place.coordinates)
        if not (xmin <= px <= xmax and ymin <= py <= ymax):
            raise UmapError("PLACE_OUTSIDE_MAP", "Place lies outside the map frame",
                            {"place_id": place.id, "coordinates": list(place.coordinates)})
        anchors[place.id] = (round(mx+(px-xmin)*mw/(xmax-xmin), 9),
                             round(my+(py-ymin)*mh/(ymax-ymin), 9))
    return anchors


def _marker_positions(anchors, frame, radius):
    """Keep isolated markers fixed; reserve their space before arranging clusters."""
    gap = 2*radius + 1
    clustered = {key for key, xy in anchors.items() if any(
        other != key and math.dist(xy, pos) < gap for other, pos in anchors.items())}
    positions = {key: xy for key, xy in anchors.items() if key not in clustered}
    mx, my, mw, mh = frame
    for key in sorted(clustered):
        ax, ay = anchors[key]
        for ring in range(1, 2*len(clustered)+3):
            count = 8*ring
            for step in range(count):
                angle = 2*math.pi*step/count
                x, y = ax+ring*gap*math.cos(angle), ay+ring*gap*math.sin(angle)
                if (mx+radius <= x <= mx+mw-radius and my+radius <= y <= my+mh-radius
                        and all(math.dist((x, y), xy) >= gap-1e-6 for xy in positions.values())
                        and all(math.dist((x, y), xy) >= radius+2 for xy in anchors.values())):
                    positions[key] = (x, y)
                    break
            if key in positions:
                break
        else:
            raise UmapError("MARKER_LAYOUT_FULL", "Map frame is too small to separate markers",
                            {"place_id": key})
    return positions


def _poster_content(prepared, spec, layout, ink, accent, diagnostics):
    """Fixed bands, editable numbered markers, and an optional place directory."""
    tx, ty, tw, th = (v * PT_PER_MM for v in layout.title_band_mm)
    centered = spec.page.layout == "poster"
    align = "center" if centered else "left"
    title_size = spec.page.title_size_pt or 24.0
    subtitle_size = spec.page.subtitle_size_pt or 9.0
    title = SceneText("title", spec.title, tx+tw/2 if centered else tx,
                      ty+th-2*PT_PER_MM-title_size, title_size, ink, align, bold=True)
    subtitle = SceneText("subtitle", spec.subtitle, title.x, ty+3*PT_PER_MM,
                         subtitle_size, ink, align)
    texts = [title, subtitle]
    for item in texts:
        _, height, descent = _preflight_text(item, tw)
        if item.text and (item.y-descent < ty or item.y+height > ty+th):
            raise UmapError("TEXT_OVERFLOW", "Text exceeds the fixed title band", {"id": item.id})
    if subtitle.text and title.text:
        _, height, _ = _measure(subtitle)
        _, _, descent = _measure(title)
        if title.y-descent <= subtitle.y+height:
            raise UmapError("TEXT_OVERFLOW", "Title and subtitle overlap in the fixed title band")

    radius = 2.5*PT_PER_MM
    markers, leaders, directory = [], [], []
    anchors = place_anchors(prepared, spec)
    mx, my, mw, mh = (v * PT_PER_MM for v in layout.frame_mm)
    positions = _marker_positions(anchors, (mx, my, mw, mh), radius)
    for index, place in enumerate(spec.places):
        x, y = positions[place.id]
        anchor = anchors[place.id]
        if anchor != (x, y):
            leaders.append(ScenePath(stable_id(place.id, "leader"), (anchor, (x, y)),
                                     (1, 2), ScenePaint(stroke=ink, width_pt=0.8)))
            leaders.append(_circle(stable_id(place.id, "anchor"), *anchor, 1.6, ScenePaint(fill=ink)))
            diagnostics.append(Diagnostic(code="PLACE_OVERLAP", severity="info", feature_id=place.id,
                               message="Number moved; the leader points to the original location"))
        if x-radius < mx or x+radius > mx+mw or y-radius < my or y+radius > my+mh:
            diagnostics.append(Diagnostic(code="PLACE_CLIPPED", feature_id=place.id,
                message="The marker touches the map edge and is clipped; coordinates were retained"))
        markers.append(_circle(stable_id(place.id, "place-marker"), x, y, radius,
                               ScenePaint(fill=accent, stroke=ink, width_pt=0.5)))
        texts.append(SceneText(stable_id(place.id, "place-number"), str(index+1),
                               x, y-2.5, 7, _contrast_ink(accent), "center", True, bold=True))
        if not layout.places_band_mm:
            continue
        lx, ly, lw, lh = (v * PT_PER_MM for v in layout.places_band_mm)
        if len(spec.places) <= 3 and lw >= 170*PT_PER_MM:
            # A short walking guide gets a generous, horizontal index.
            cell = lw / len(spec.places)
            left = lx + index*cell
            directory.append(_rect(stable_id(place.id, "index-rule"), left, ly+lh-15,
                                   cell-9, 0.8, ScenePaint(fill=accent)))
            texts.append(SceneText(stable_id(place.id, "index-number"), f"{index+1:02d}", left,
                                   ly+lh-39, 15, accent, bold=True))
            label = SceneText(stable_id(place.id, "place-label"), place.label, left, ly+lh-57, 10, ink)
            label_width = cell-9
        else:
            column, row = divmod(index, (len(spec.places)+1)//2)
            label = SceneText(stable_id(place.id, "place-label"), f"{index+1:02d}  {place.label}",
                              lx+column*(lw/2+3*PT_PER_MM), ly+lh-(5+row*5)*PT_PER_MM, 8, ink)
            label_width = lw/2-3*PT_PER_MM
        _, label_height, label_descent = _preflight_text(label, label_width)
        if label_height > 4*PT_PER_MM or label_descent > PT_PER_MM:
            raise UmapError("TEXT_OVERFLOW", "Place label exceeds its fixed directory row",
                            {"id": label.id})
        texts.append(label)

    m = spec.page.margin_mm*PT_PER_MM
    width = spec.page.dimensions_mm[0]*PT_PER_MM-2*m
    by = m+(spec.page.footer_mm-5)*PT_PER_MM
    scale = prepared.scale_denominator
    distance = _nice_distance(scale*0.035)
    bar_width = distance*1000/scale*PT_PER_MM
    bx = m+width-bar_width
    decorations = [ScenePath("scale-bar", ((bx, by+3), (bx, by), (bx+bar_width, by),
                                           (bx+bar_width, by+3)), (1, 2, 2, 2),
                             ScenePaint(stroke=ink, width_pt=0.6), False)]
    distance_text = f"{distance/1000:g} km" if distance >= 1000 else f"{distance:g} m"
    texts.append(SceneText("scale-label", f"1:{scale:,.0f} · {distance_text}",
                           bx+bar_width, by+5, 7, ink, "right"))
    attribution = SceneText("attribution", _attribution(spec, prepared), m,
                            m+PT_PER_MM, 7, ink)
    _preflight_text(attribution, width)
    texts.append(attribution)
    groups = [SceneGroup("place-leaders", tuple(leaders))] if leaders else []
    return groups + [SceneGroup("places", tuple(markers)),
                     SceneGroup("decorations", tuple(decorations+directory))], texts


def _sheet_identity(spec, view, frame, ink, accent):
    """Print a consistent series line and plate number above the map or title."""
    x, y, width, height = frame
    paths = [_rect("map-keyline", x, y, width, height, ScenePaint(stroke=ink, width_pt=0.5, opacity=0.5))]
    if spec.page.margin_mm < 9:
        return SceneGroup("sheet-identity", tuple(paths)), []
    is_tr = spec.language == "tr"
    series = {"poster": ("KENT POSTERİ", "CITY POSTER"), "guide": ("SEMT REHBERİ", "FIELD GUIDE"),
              "pocket": ("CEP REHBERİ", "POCKET GUIDE"), "classic": ("KENT ATLASI", "CITY ATLAS")}
    page_h = spec.page.dimensions_mm[1]*PT_PER_MM
    baseline = page_h - spec.page.margin_mm*PT_PER_MM + 5
    mark = series[spec.page.layout][0 if is_tr else 1]
    count = len(spec.views)
    number = spec.views.index(view)+1 if view in spec.views else 1
    if spec.page.layout == "pocket":
        count = 2
    folio = f"{number:02} / {count:02}"
    paths.append(_rect("edition-bar", x, baseline, 11, 4, ScenePaint(fill=accent)))
    return SceneGroup("sheet-identity", tuple(paths)), [
        SceneText("edition", f"U-MAP   /   {mark}", x+16, baseline, 7, ink, bold=True),
        SceneText("sheet-number", folio, x+width, baseline, 7, ink, "right", bold=True)]


def compile_scene(prepared: Any, spec: MapSpec, view: str) -> Scene:
    """Compile prepared metric geometry into a fully laid out page."""
    if view not in VIEW_LAYERS:
        raise UmapError("INVALID_VIEW", f"Unknown view: {view}")
    if not FONT_PATH.is_file():
        raise UmapError("FONT_UNAVAILABLE", "The bundled Space Grotesk font is missing")
    validate_style(spec.style)
    w, h = (v * PT_PER_MM for v in spec.page.dimensions_mm)
    layout = resolve_layout(spec.page)
    x, y, fw, fh = (v * PT_PER_MM for v in layout.frame_mm)
    xmin, ymin, xmax, ymax = prepared.bounds
    if xmax <= xmin or ymax <= ymin:
        raise UmapError("INVALID_EXTENT", "Projected bounds must have positive dimensions")
    sx, sy = fw / (xmax-xmin), fh / (ymax-ymin)
    if not math.isclose(sx, sy, rel_tol=1e-7):
        raise UmapError("FRAME_ASPECT_MISMATCH", "Prepared bounds do not match the physical map frame")

    def transform(px, py):
        return (round(x + (px-xmin)*sx, 9), round(y + (py-ymin)*sy, 9))

    theme, labels = THEMES[spec.style.theme], LABELS[spec.language]
    background = spec.style.background or theme["background"]
    groups = [SceneGroup("page", (_rect("page-background", 0, 0, w, h,
                                       ScenePaint(fill=background)),)),
              SceneGroup("map-background", (_rect("map-background-fill", x, y, fw, fh,
                                                 ScenePaint(fill=background)),))]
    diagnostics = list(prepared.diagnostics)
    present = {}
    for layer in spec.style.order:
        features = [f for f in prepared.features if f.layer == layer]
        features.sort(key=_road_order if layer == "roads" else lambda f: f.id)
        paths = []
        for feature in features:
            paint = resolve_paint(feature, spec.style, view)
            if not paint.visible or paint.opacity == 0 or (paint.fill is None and paint.stroke is None):
                continue
            if paint.stroke and 0 < paint.width_mm < 0.05:
                diagnostics.append(Diagnostic(code="THIN_STROKE", feature_id=feature.id,
                    message=f"Stroke width {paint.width_mm:g} mm may be difficult to print"))
            geometry = shape(feature.geometry)
            for index, (vertices, codes) in enumerate(_geometry_paths(geometry, transform)):
                paths.append(ScenePath(stable_id(feature.id, f"{layer}-{index}"), vertices,
                                       codes, ScenePaint.from_paint(paint), True, feature.id))
                present.setdefault(layer, ScenePaint.from_paint(paint))
        if paths:
            groups.append(SceneGroup(f"layer-{layer}", tuple(paths)))

    m = spec.page.margin_mm * PT_PER_MM
    ink = spec.style.ink or theme["ink"]
    if spec.page.layout == "field_cards":
        attribution = SceneText("attribution", _attribution(spec, prepared), m, m, 6.5, ink)
        _preflight_text(attribution, fw)
        return Scene(view, w, h, (x, y, fw, fh), tuple(groups), (attribution,),
                     float(prepared.scale_denominator), prepared.crs, tuple(diagnostics))
    sheet_group, edition = _sheet_identity(spec, view, (x, y, fw, fh), ink,
                                          spec.style.accent or theme["accent"])
    groups.append(sheet_group)
    if spec.page.layout != "classic":
        decorations, texts = _poster_content(prepared, spec, layout, ink,
            spec.style.accent or theme["accent"], diagnostics)
        groups.extend(decorations)
        texts.extend(edition)
        return Scene(view, w, h, (x, y, fw, fh), tuple(groups), tuple(texts),
                     float(prepared.scale_denominator), prepared.crs, tuple(diagnostics))
    title_size = spec.page.title_size_pt or min(
        18.0, (spec.page.header_mm * PT_PER_MM - 4*PT_PER_MM - 9) / 1.6)
    title = SceneText("title", spec.title, m, h-m-title_size, title_size, ink, bold=True)
    # The view belongs in a consistent position whether or not a subtitle exists.
    subtitle_text = " · ".join(t for t in (spec.subtitle, labels[view]) if t)
    subtitle = SceneText("subtitle", subtitle_text, m,
                         y+fh+4*PT_PER_MM, spec.page.subtitle_size_pt or 9, ink)
    texts = [title, subtitle, *edition]
    _preflight_text(title, fw)
    _preflight_text(subtitle, fw)
    if title.y - title.size_pt * 0.25 <= subtitle.y + subtitle.size_pt:
        raise UmapError("TEXT_OVERFLOW", "Header is too short for the title and subtitle")

    # Footer has independent legend, scale, and attribution rows, in physical units.
    legend_y = y - 5*PT_PER_MM
    legend_x = x
    decoration = []
    legend_max = fw - 75*PT_PER_MM
    for layer in spec.style.order:
        if layer not in present:
            continue
        paint = present[layer]
        swatch_paint = ScenePaint(fill=paint.fill or paint.stroke, stroke=None)
        swatch_height = 0.65 if layer == "roads" else 2
        decoration.append(_rect(f"legend-swatch-{layer}", legend_x, legend_y,
                                3*PT_PER_MM, swatch_height*PT_PER_MM, swatch_paint))
        label = SceneText(f"legend-label-{layer}", labels[layer],
                          legend_x+4.5*PT_PER_MM, legend_y, 7, ink)
        width, _, _ = _preflight_text(label, legend_max)
        texts.append(label)
        legend_x += 4.5*PT_PER_MM + width + 4*PT_PER_MM
    if legend_x-x > legend_max and present:
        raise UmapError("TEXT_OVERFLOW", "Legend does not fit the page footer")

    scale = float(prepared.scale_denominator)
    distance = _nice_distance(scale * 0.035)
    bar_width = distance * 1000/scale * PT_PER_MM
    bx, by = x+fw-bar_width, legend_y
    vertices = ((bx, by+3), (bx, by), (bx+bar_width, by), (bx+bar_width, by+3))
    decoration.append(ScenePath("scale-bar", vertices, (1, 2, 2, 2),
                                ScenePaint(stroke=ink, width_pt=0.6), False))
    distance_text = f"{distance/1000:g} km" if distance >= 1000 else f"{distance:g} m"
    scale_text = SceneText("scale-label", f"1:{scale:,.0f} · {distance_text}",
                           bx+bar_width, by+5, 7, ink, "right")
    texts.append(scale_text)
    attribution = _attribution(spec, prepared)
    texts.append(SceneText("attribution", attribution, m, m+PT_PER_MM, 7, ink))
    for text in texts[2:]:
        width, height, descent = _preflight_text(text, fw)
        left = text.x - (width/2 if text.align == "center" else width if text.align == "right" else 0)
        if left < m-0.01 or left+width > w-m+0.01 or text.y-descent < 0 or text.y+height > h:
            raise UmapError("TEXT_OVERFLOW", "Page label falls outside the printable page",
                            {"id": text.id})
    groups.append(SceneGroup("decorations", tuple(decoration)))
    return Scene(view, w, h, (x, y, fw, fh), tuple(groups), tuple(texts),
                 scale, prepared.crs, tuple(diagnostics))
