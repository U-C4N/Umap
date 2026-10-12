"""Small, declarative styling language shared by every presentation interface.

Filters are JSON objects with one operator: ``{"eq": ["highway", "primary"]}``,
``{"in": ["highway", ["primary", "secondary"]]}``, ``{"has": "building"}``,
or ``{"all": [filter, ...]}`` / ``{"any": [filter, ...]}``. An empty filter
matches every feature. No expressions, imports, or Python evaluation are allowed.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from .errors import UmapError
from .models import Feature, Paint, StyleSpec

THEMES = {
    "architectural": {
        "background": "#FAFAF7", "ink": "#252A30",
        "buildings": {"fill": "#454A4F", "stroke": "#454A4F", "width_mm": 0.06},
        "roads": {"stroke": "#777C80", "width_mm": 0.24},
        "green": {"fill": "#CCD5C6", "stroke": None, "width_mm": 0},
        "water": {"fill": "#D4E3E8", "stroke": None, "width_mm": 0},
    },
    "city_poster": {
        "background": "#F7ECDC", "ink": "#253A43",
        "buildings": {"fill": "#CE765C", "stroke": "#BA654F", "width_mm": 0.06},
        "roads": {"stroke": "#FBF6EC", "width_mm": 0.35},
        "green": {"fill": "#87A886", "stroke": None, "width_mm": 0},
        "water": {"fill": "#75AABB", "stroke": None, "width_mm": 0},
    },
}

VIEW_LAYERS = {
    "general": ("water", "green", "buildings", "roads"),
    "figure_ground": ("buildings",), "roads": ("roads",),
    "green": ("green",), "water": ("water",),
}

LABELS = {
    "tr": {"buildings": "Yapılar", "roads": "Yollar", "green": "Yeşil alanlar",
           "water": "Su", "general": "Kent haritası", "figure_ground": "Dolu–boş",
           "scale": "Ölçek"},
    "en": {"buildings": "Buildings", "roads": "Roads", "green": "Green spaces",
           "water": "Water", "general": "City map", "figure_ground": "Figure–ground",
           "scale": "Scale"},
}


def list_styles() -> list[dict[str, Any]]:
    """Return independently editable copies of the two built-in themes."""
    return [
        {"name": name, "schema_version": "1", "defaults": deepcopy(theme),
         "views": list(VIEW_LAYERS),
         "editable_fields": list(Paint.model_fields),
         "filter_operators": ["all", "any", "eq", "in", "has"]}
        for name, theme in THEMES.items()
    ]


def validate_filter(condition: dict[str, Any]) -> None:
    """Validate the complete tree before matching, including unreachable branches."""
    count = 0

    def visit(node, depth):
        nonlocal count
        count += 1
        if count > 256 or depth > 16:
            raise UmapError("INVALID_FILTER", "Style filter exceeds its size/depth limit")
        if not isinstance(node, dict) or len(node) > 1:
            raise UmapError("INVALID_FILTER", "Each filter must contain exactly one operator")
        if not node:
            return
        op, arg = next(iter(node.items()))
        if op in ("all", "any"):
            if not isinstance(arg, list) or not arg:
                raise UmapError("INVALID_FILTER", f"{op} requires a nonempty list of filters")
            for child in arg:
                visit(child, depth + 1)
        elif op == "has":
            if not isinstance(arg, str) or not arg:
                raise UmapError("INVALID_FILTER", "has requires a property name")
        elif op in ("eq", "in"):
            if not isinstance(arg, list) or len(arg) != 2 or not isinstance(arg[0], str):
                raise UmapError("INVALID_FILTER", f"{op} requires [property, value]")
            values = arg[1] if op == "in" else [arg[1]]
            if not isinstance(values, list) or not values or len(values) > 128:
                raise UmapError("INVALID_FILTER", "in requires 1–128 literal values")
            if any(not isinstance(v, (str, bool, int, float, type(None))) for v in values):
                raise UmapError("INVALID_FILTER", "Filter values must be JSON scalars")
        else:
            raise UmapError("INVALID_FILTER", f"Unsupported filter operator: {op}")

    visit(condition, 0)


def matches(condition: dict[str, Any], properties: dict[str, Any]) -> bool:
    """Match an already validated condition against feature attributes."""
    if not condition:
        return True
    op, arg = next(iter(condition.items()))
    if op == "all":
        return all(matches(child, properties) for child in arg)
    if op == "any":
        return any(matches(child, properties) for child in arg)
    if op == "has":
        return arg in properties
    if op == "eq":
        return arg[0] in properties and properties[arg[0]] == arg[1]
    if op == "in":
        return arg[0] in properties and properties[arg[0]] in arg[1]
    raise UmapError("INVALID_FILTER", f"Unsupported filter operator: {op}")


def validate_style(style: StyleSpec) -> None:
    for rule in style.rules:
        validate_filter(rule.when)


def resolve_paint(feature: Feature, style: StyleSpec, view: str) -> Paint:
    if view not in VIEW_LAYERS:
        raise UmapError("INVALID_VIEW", f"Unknown view: {view}")
    values = deepcopy(THEMES[style.theme][feature.layer])
    if feature.layer == "roads":
        highway = feature.properties.get("highway", "")
        weight = {"motorway": 2.2, "trunk": 2.0, "primary": 1.8,
                  "secondary": 1.5, "tertiary": 1.25, "footway": 0.55,
                  "path": 0.55, "cycleway": 0.65, "steps": 0.5}.get(highway, 1.0)
        values["width_mm"] *= weight
        if str(feature.properties.get("tunnel", "no")).lower() not in ("no", "false", "0", "none"):
            values.update(dash_mm=[0.8, 0.5], opacity=0.65)
    if view == "figure_ground":
        values.update(fill="#252A30", stroke=None, width_mm=0)
    if view == "roads" and style.theme == "city_poster":
        values["stroke"] = THEMES[style.theme]["ink"]
    overrides = dict(style.layers.get(feature.layer, {}))
    for rule in style.rules:
        if rule.layer == feature.layer and matches(rule.when, feature.properties):
            overrides.update(rule.paint)
    values.update(overrides)
    if feature.layer == "water" and feature.geometry.get("type") in ("LineString", "MultiLineString"):
        # Area water uses fill, river/stream centerlines need a visible stroke.
        # Explicit stroke=None still hides it, and fill overrides recolor both forms.
        if "stroke" not in overrides:
            values["stroke"] = values.get("fill")
        if "width_mm" not in overrides:
            values["width_mm"] = 0.2
        values["fill"] = None
    values["visible"] = values.get("visible", True) and feature.layer in VIEW_LAYERS[view]
    return Paint.model_validate(values)
