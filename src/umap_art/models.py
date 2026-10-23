"""Versioned public recipe and result models; all coordinates are longitude, latitude."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Layer = Literal["buildings", "roads", "green", "water"]
View = Literal["general", "figure_ground", "roads", "green", "water"]


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class AreaSpec(Model):
    center: tuple[float, float] | None = None
    place: str | None = Field(default=None, min_length=1, max_length=300)
    bbox: tuple[float, float, float, float] | None = None
    scale_denominator: float = Field(default=5000, ge=100, le=1_000_000)

    @model_validator(mode="after")
    def validate_area(self):
        if sum(x is not None for x in (self.center, self.place, self.bbox)) != 1:
            raise ValueError("Specify exactly one of center, place, or bbox")
        if self.center and not (-180 <= self.center[0] <= 180 and -80 <= self.center[1] <= 84):
            raise ValueError("Center must be longitude/latitude within UTM coverage")
        if self.bbox:
            w, s, e, n = self.bbox
            if not (-180 <= w < e <= 180 and -80 <= s < n <= 84):
                raise ValueError(
                    "bbox must be west,south,east,north; antimeridian/poles unsupported"
                )
        return self


class PageSpec(Model):
    size: Literal["A3", "A4"] = "A3"
    orientation: Literal["landscape", "portrait"] = "landscape"
    dpi: int = Field(default=300, ge=72, le=600)
    margin_mm: float = Field(default=10, ge=5, le=30)
    header_mm: float = Field(default=20, ge=15, le=40)
    footer_mm: float = Field(default=16, ge=12, le=35)
    text_mode: Literal["editable", "outline"] = "editable"
    layout: Literal["classic", "poster", "guide"] = "classic"
    title_size_pt: float | None = Field(default=None, ge=8, le=48)
    subtitle_size_pt: float | None = Field(default=None, ge=7, le=24)

    @property
    def dimensions_mm(self) -> tuple[float, float]:
        w, h = (297.0, 420.0) if self.size == "A3" else (210.0, 297.0)
        return (h, w) if self.orientation == "landscape" else (w, h)

    @property
    def frame_mm(self) -> tuple[float, float, float, float]:
        from .layout import resolve_layout

        return resolve_layout(self).frame_mm


class Paint(Model):
    fill: str | None = None
    stroke: str | None = None
    width_mm: float = Field(default=0.2, ge=0, le=10)
    opacity: float = Field(default=1, ge=0, le=1)
    dash_mm: list[float] = Field(default_factory=list)
    visible: bool = True

    @field_validator("fill", "stroke")
    @classmethod
    def colors(cls, value):
        if value is not None:
            import re

            if not re.fullmatch(r"#[0-9a-fA-F]{6}", value):
                raise ValueError("Colors must use #RRGGBB")
        return value

    @field_validator("dash_mm")
    @classmethod
    def dashes(cls, value):
        if any(not math.isfinite(v) or v <= 0 for v in value) or len(value) > 8:
            raise ValueError("Dash lengths must be positive finite mm, at most eight")
        return value


class StyleRule(Model):
    layer: Layer
    when: dict[str, Any] = Field(default_factory=dict)
    paint: dict[str, Any]


class StyleSpec(Model):
    schema_version: Literal["1"] = "1"
    theme: Literal["architectural", "city_poster", "minimal", "blueprint", "vintage", "neon"] = "architectural"
    background: str | None = None
    ink: str | None = None
    accent: str | None = None
    layers: dict[Layer, dict[str, Any]] = Field(default_factory=dict)
    order: list[Layer] = Field(default_factory=lambda: ["water", "green", "buildings", "roads"])
    rules: list[StyleRule] = Field(default_factory=list, max_length=100)

    @model_validator(mode="after")
    def validate_style(self):
        if set(self.order) != {"water", "green", "buildings", "roads"} or len(self.order) != 4:
            raise ValueError("order must contain every layer exactly once")
        for color in (self.background, self.ink, self.accent):
            if color is not None:
                Paint(fill=color)
        for p in list(self.layers.values()) + [r.paint for r in self.rules]:
            Paint.model_validate(p)
        return self


class SourceSpec(Model):
    photon_url: str = "https://photon.komoot.io"
    overpass_url: str = "https://overpass-api.de/api/interpreter"
    overture_catalog_url: str = "https://stac.overturemaps.org/catalog.json"
    snapshot: str | None = None
    offline: bool = False
    include_ocean: bool = True


class Limits(Model):
    max_area_km2: float = Field(default=25, gt=0, le=25)
    acquisition_seconds: float = Field(default=180, gt=0, le=300)
    max_response_bytes: int = Field(default=150 * 1024**2, ge=1024, le=150 * 1024**2)
    max_features: int = Field(default=200_000, ge=1, le=1_000_000)


class Place(Model):
    """User-selected locations, kept in the recipe rather than the source dataset."""

    id: str = Field(min_length=1, max_length=80)
    label: str = Field(min_length=1, max_length=180)
    coordinates: tuple[float, float]

    @model_validator(mode="after")
    def validate_place(self):
        if not self.id.strip() or not self.label.strip():
            raise ValueError("Place id and label must not be blank")
        lon, lat = self.coordinates
        if not (-180 <= lon <= 180 and -80 <= lat <= 84):
            raise ValueError("Place coordinates must be longitude/latitude within UTM coverage")
        return self


class MapSpec(Model):
    schema_version: Literal["1"] = "1"
    area: AreaSpec
    page: PageSpec = Field(default_factory=PageSpec)
    style: StyleSpec = Field(default_factory=StyleSpec)
    source: SourceSpec = Field(default_factory=SourceSpec)
    limits: Limits = Field(default_factory=Limits)
    views: list[View] = Field(default_factory=lambda: ["general"], min_length=1, max_length=5)
    formats: list[Literal["png", "svg", "pdf"]] = Field(
        default_factory=lambda: ["png", "svg", "pdf"], min_length=1
    )
    title: str = Field(default="Umap", max_length=180)
    subtitle: str = Field(default="", max_length=240)
    language: Literal["tr", "en"] = "tr"
    geometry_policy: Literal["strict", "repair"] = "strict"
    bundle: bool = True
    places: list[Place] = Field(default_factory=list, max_length=12)

    @model_validator(mode="after")
    def unique_outputs(self):
        if len(set(self.views)) != len(self.views) or len(set(self.formats)) != len(self.formats):
            raise ValueError("views and formats must not contain duplicates")
        if len({place.id for place in self.places}) != len(self.places):
            raise ValueError("Place ids must be unique")
        if self.page.layout != "classic" and self.views != ["general"]:
            raise ValueError("Poster and guide layouts require views=['general']")
        if self.places and self.page.layout == "classic":
            raise ValueError("Places require a poster or guide layout")
        return self


class Diagnostic(Model):
    code: str
    message: str
    severity: Literal["info", "warning", "error"] = "warning"
    feature_id: str | None = None


class Feature(Model):
    id: str
    layer: Layer
    geometry: dict[str, Any]
    properties: dict[str, Any] = Field(default_factory=dict)


class Dataset(Model):
    schema_version: Literal["1"] = "1"
    features: list[Feature] = Field(default_factory=list)
    sources: list[dict[str, Any]] = Field(default_factory=list)
    diagnostics: list[Diagnostic] = Field(default_factory=list)
    bbox: tuple[float, float, float, float]
    coverage: Literal["not_assessed"] = "not_assessed"


class Artifact(Model):
    path: str
    mime_type: str
    sha256: str
    size_bytes: int
    view: str | None = None


class RenderResult(Model):
    schema_version: Literal["1"] = "1"
    artifacts: list[Artifact]
    manifest_path: str
    recipe_path: str
    snapshot_path: str
    dataset_id: str
    scene_hashes: dict[str, str]
    diagnostics: list[Diagnostic] = Field(default_factory=list)


def validate_spec(spec: MapSpec | dict | str | Path) -> MapSpec:
    if isinstance(spec, MapSpec):
        return MapSpec.model_validate(spec.model_dump())
    if isinstance(spec, dict):
        return MapSpec.model_validate(spec)
    return MapSpec.model_validate_json(Path(spec).read_text(encoding="utf-8"))
