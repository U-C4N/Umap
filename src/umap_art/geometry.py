"""Projection and physical extent preparation, independent of rendering and I/O."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from pyproj import CRS, Geod, Proj, Transformer
from shapely import make_valid, transform
from shapely.geometry import box, mapping, shape
from shapely.ops import unary_union

from .errors import UmapError
from .models import Dataset, Diagnostic, Feature, MapSpec


@dataclass(frozen=True)
class Extent:
    crs: str
    bounds: tuple[float, float, float, float]
    bbox: tuple[float, float, float, float]
    scale_denominator: float
    projection_distortion: float


@dataclass(frozen=True)
class PreparedGeometry:
    features: list[Feature]
    crs: str
    bounds: tuple[float, float, float, float]
    scale_denominator: float
    diagnostics: list[Diagnostic]
    projection_distortion: float


def compute_extent(spec: MapSpec) -> Extent:
    area = spec.area
    if area.place is not None:
        raise UmapError("UNRESOLVED_LOCATION", "Resolve the place before computing the extent")
    if area.bbox:
        w, s, e, n = area.bbox
        lon, lat = (w + e) / 2, (s + n) / 2
    else:
        lon, lat = area.center
    zone = min(60, max(1, int((lon + 180) // 6) + 1))
    crs = f"EPSG:{(32600 if lat >= 0 else 32700) + zone}"
    forward = Transformer.from_crs("EPSG:4326", crs, always_xy=True)
    inverse = Transformer.from_crs(crs, "EPSG:4326", always_xy=True)
    _, _, frame_w, frame_h = spec.page.frame_mm
    if frame_w <= 0 or frame_h <= 0:
        raise UmapError("INVALID_PAGE", "Margins and information bands leave no map frame")
    if area.bbox:
        xmin, ymin, xmax, ymax = forward.transform_bounds(*area.bbox, densify_pts=21)
        scale = max((xmax - xmin) / (frame_w / 1000), (ymax - ymin) / (frame_h / 1000))
        cx, cy = (xmin + xmax) / 2, (ymin + ymax) / 2
    else:
        cx, cy = forward.transform(lon, lat)
        scale = area.scale_denominator
    width, height = frame_w * scale / 1000, frame_h * scale / 1000
    bounds = (cx - width / 2, cy - height / 2, cx + width / 2, cy + height / 2)
    bbox = inverse.transform_bounds(*bounds, densify_pts=21)
    w, s, e, n = bbox
    if w >= e or w < -180 or e > 180 or s < -80 or n > 84:
        raise UmapError("UNSUPPORTED_EXTENT", "Extent crosses antimeridian or UTM coverage")
    geographic_area, _ = Geod(ellps="WGS84").polygon_area_perimeter([w, e, e, w], [s, s, n, n])
    area_km2 = abs(geographic_area) / 1e6
    if area_km2 > spec.limits.max_area_km2:
        raise UmapError(
            "AREA_LIMIT",
            "Choose a smaller map extent",
            {"area_km2": area_km2, "limit_km2": spec.limits.max_area_km2},
        )
    proj = Proj(CRS.from_user_input(crs))
    distortion = 0.0
    for x, y in [(lon, lat), (w, s), (w, n), (e, s), (e, n)]:
        factors = proj.get_factors(x, y)
        distortion = max(
            distortion, abs(factors.meridional_scale - 1), abs(factors.parallel_scale - 1)
        )
    if distortion > 0.001:
        raise UmapError(
            "PROJECTION_DISTORTION",
            "Projection scale distortion exceeds 0.1%",
            {"distortion": distortion, "crs": crs},
        )
    return Extent(crs, bounds, bbox, scale, distortion)


def prepare_geometry(dataset: Dataset, spec: MapSpec, extent: Extent) -> PreparedGeometry:
    transformer = Transformer.from_crs("EPSG:4326", extent.crs, always_xy=True)
    clip = box(*extent.bounds)
    features: list[Feature] = []
    ocean: list[tuple[Feature, object]] = []
    diagnostics = list(dataset.diagnostics)
    for feature in sorted(dataset.features, key=lambda f: (f.layer, f.id)):
        try:
            geom = shape(feature.geometry)
            if geom.is_empty:
                continue
            linear = geom.geom_type in ("LineString", "LinearRing", "MultiLineString")
            if not geom.is_valid:
                if spec.geometry_policy == "strict":
                    raise UmapError(
                        "INVALID_GEOMETRY",
                        "Invalid source geometry; use geometry_policy='repair' to request repair",
                        {"feature_id": feature.id},
                    )
                old_type = geom.geom_type
                geom = make_valid(geom)
                diagnostics.append(
                    Diagnostic(
                        code="GEOMETRY_REPAIRED",
                        message=f"{old_type} repaired to {geom.geom_type}",
                        feature_id=feature.id,
                    )
                )
            projected = transform(geom, transformer.transform, interleaved=False)
            if not projected.intersects(clip):
                continue
            if not projected.is_valid:
                raise UmapError(
                    "INVALID_GEOMETRY",
                    "Projection produced invalid geometry",
                    {"feature_id": feature.id},
                )
            projected = projected.intersection(clip)
            if projected.geom_type == "GeometryCollection":
                wanted = (
                    ("LineString", "MultiLineString") if linear else ("Polygon", "MultiPolygon")
                )
                parts = [p for p in projected.geoms if p.geom_type in wanted]
                if len(parts) != len(projected.geoms):
                    diagnostics.append(
                        Diagnostic(
                            code="GEOMETRY_COMPONENT_REMOVED",
                            message="Repair/clip produced lower dimensional components; these were removed",
                            feature_id=feature.id,
                        )
                    )
                projected = unary_union(parts)
            if projected.is_empty:
                continue
            if (
                feature.properties.get("subtype") == "ocean"
                or feature.properties.get("ocean") is True
            ):
                ocean.append((feature, projected))
            else:
                features.append(feature.model_copy(update={"geometry": mapping(projected)}))
        except UmapError:
            raise
        except Exception as exc:
            raise UmapError(
                "INVALID_GEOMETRY",
                "Unable to prepare source geometry",
                {"feature_id": feature.id, "reason": str(exc)},
            ) from exc
    if ocean:
        merged = unary_union([g for _, g in ocean])
        ids = sorted(f.id for f, _ in ocean)
        identity = hashlib.sha256("\n".join(ids).encode()).hexdigest()[:20]
        features.append(
            Feature(
                id=f"ocean-{identity}",
                layer="water",
                geometry=mapping(merged),
                properties={"subtype": "ocean", "source_ids": ids},
            )
        )
    if not features:
        diagnostics.append(
            Diagnostic(
                code="EMPTY_DATA", message="The completed source query contains no visible features"
            )
        )
    return PreparedGeometry(
        features,
        extent.crs,
        extent.bounds,
        extent.scale_denominator,
        diagnostics,
        extent.projection_distortion,
    )
