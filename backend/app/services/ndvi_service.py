"""
NDVI pipeline: DOS atmospheric correction, NDVI, classification visualization, map tiles.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Tuple

import ee

from app.services import gee_service

logger = logging.getLogger(__name__)

# Classification breaks (NDVI) — display on map
CLASS_BREAKS = [
    {"max_ndvi": 0.1, "label": "Bare Soil / Water", "color": "#e53935"},
    {"max_ndvi": 0.3, "label": "Stressed Vegetation", "color": "#fb8c00"},
    {"max_ndvi": 0.5, "label": "Moderate Vegetation", "color": "#fdd835"},
    {"max_ndvi": 1.01, "label": "Healthy Vegetation", "color": "#2e7d32"},
]


def dark_object_subtraction(
    image: ee.Image,
    band_names: List[str],
    geometry: ee.Geometry,
    scale_m: float,
) -> ee.Image:
    """
    Dark Object Subtraction: subtract ~2nd percentile reflectance per band (valid pixels).
    """
    sel = image.select(band_names)
    p2 = sel.reduceRegion(
        reducer=ee.Reducer.percentile([2]),
        geometry=geometry,
        scale=scale_m,
        maxPixels=1e13,
        bestEffort=True,
        tileScale=2,
    )
    out = None
    for b in band_names:
        dark = ee.Number(p2.get(b))
        band = image.select(b).subtract(dark).max(0).rename(b)
        out = band if out is None else out.addBands(band)
    return out


def compute_ndvi_from_reflectance(red_nir: ee.Image) -> ee.Image:
    """NDVI = (NIR - Red) / (NIR + Red), clamped to [-1, 1]."""
    red = red_nir.select("red")
    nir = red_nir.select("nir")
    ndvi = nir.subtract(red).divide(nir.add(red)).clamp(-1, 1).rename("ndvi")
    return ndvi


def full_preprocess_pipeline(
    reflectance_median: ee.Image,
    geometry: ee.Geometry,
    scale_m: float,
) -> Tuple[ee.Image, ee.Image]:
    """
    Apply DOS on red/nir, then compute NDVI.
    Returns (reflectance after DOS, NDVI image).
    """
    dos_img = dark_object_subtraction(reflectance_median, ["red", "nir"], geometry, scale_m)
    ndvi = compute_ndvi_from_reflectance(dos_img)
    return dos_img, ndvi


def classify_ndvi_palette(ndvi: ee.Image) -> ee.Image:
    """Single-band classified image 0–3 for visualization (order: high NDVI first)."""
    cls = ee.Image(0)
    cls = cls.where(ndvi.gt(0.5), 3)
    cls = cls.where(ndvi.gt(0.3).And(ndvi.lte(0.5)), 2)
    cls = cls.where(ndvi.gt(0.1).And(ndvi.lte(0.3)), 1)
    # cls 0: NDVI <= 0.1 (bare / water)
    return cls.rename("class")


def ndvi_visualization_params() -> Dict[str, Any]:
    return {
        "min": -0.2,
        "max": 0.9,
        "palette": ["#8c510a", "#d8b365", "#f6e8c3", "#c7eae5", "#5ab4ac", "#01665e"],
    }


def classification_visualization_params() -> Dict[str, Any]:
    return {
        "min": 0,
        "max": 3,
        "palette": ["#e53935", "#fb8c00", "#fdd835", "#2e7d32"],
    }


def build_legend() -> List[Dict[str, Any]]:
    rows = []
    low = -1.0
    for i, c in enumerate(CLASS_BREAKS):
        rows.append(
            {
                "class_id": i,
                "ndvi_min": low,
                "ndvi_max": c["max_ndvi"],
                "label": c["label"],
                "color": c["color"],
            }
        )
        low = c["max_ndvi"]
    return rows


def geometry_bounds(geometry: ee.Geometry) -> List[float]:
    """Return [west, south, east, north] for Leaflet."""
    coords = geometry.bounds().coordinates().getInfo()[0]
    xs = [c[0] for c in coords]
    ys = [c[1] for c in coords]
    return [min(xs), min(ys), max(xs), max(ys)]


def compute_ndvi_pipeline(
    roi_geojson: Dict[str, Any],
    start_date: str,
    end_date: str,
    satellite: str,
    max_cloud_pct: float,
    use_latest: bool = False,
) -> Dict[str, Any]:
    """
    Core GEE pipeline: collection → composite → DOS → NDVI + classification.
    Returns EE objects and scale for downstream ML / exports.
    """
    gee_service.initialize_gee()
    region = gee_service.geojson_to_ee_geometry(roi_geojson)
    scale_m = 10.0 if satellite == "sentinel2" else 30.0

    if satellite == "sentinel2":
        col = gee_service.sentinel2_collection(start_date, end_date, region, max_cloud_pct)
    else:
        col = gee_service.landsat89_collection(start_date, end_date, region, max_cloud_pct)

    size = col.size().getInfo()
    if size == 0 and not use_latest:
        raise ValueError(
            "No imagery found for the selected dates, region, and cloud cover. "
            "Try widening the date range or increasing cloud tolerance."
        )

    if use_latest and size == 0:
        from datetime import datetime, timedelta

        end = datetime.utcnow().date()
        start = end - timedelta(days=60)
        if satellite == "sentinel2":
            col = gee_service.sentinel2_collection(
                str(start), str(end), region, min(max_cloud_pct, 40)
            )
        else:
            col = gee_service.landsat89_collection(
                str(start), str(end), region, min(max_cloud_pct, 40)
            )
        size = col.size().getInfo()
        if size == 0:
            raise ValueError("No recent clear imagery available for this ROI.")

    if use_latest:
        reflectance = gee_service.latest_clear_composite(col, satellite)
    else:
        reflectance, _ = gee_service.composite_median(col, satellite)

    dos_img, ndvi = full_preprocess_pipeline(reflectance, region, scale_m)
    classified = classify_ndvi_palette(ndvi)
    return {
        "region": region,
        "scale_m": scale_m,
        "dos_img": dos_img,
        "ndvi": ndvi,
        "classified": classified,
        "collection_size": size,
    }


def run_ndvi_for_request(
    roi_geojson: Dict[str, Any],
    start_date: str,
    end_date: str,
    satellite: str,
    max_cloud_pct: float,
    use_latest: bool = False,
) -> Dict[str, Any]:
    """
    Execute full GEE NDVI pipeline; returns tile URLs, stats, legend, bounds.
    """
    pipe = compute_ndvi_pipeline(
        roi_geojson, start_date, end_date, satellite, max_cloud_pct, use_latest
    )
    region = pipe["region"]
    scale_m = pipe["scale_m"]
    ndvi = pipe["ndvi"]
    classified = pipe["classified"]

    ndvi_vis = ndvi_visualization_params()
    cls_vis = classification_visualization_params()

    ndvi_map = ndvi.getMapId(ndvi_vis)
    cls_map = classified.getMapId(cls_vis)

    red = ee.Reducer.mean().combine(reducer2=ee.Reducer.minMax(), sharedInputs=True)
    stats = ndvi.reduceRegion(
        reducer=red,
        geometry=region,
        scale=scale_m,
        maxPixels=1e13,
        bestEffort=True,
        tileScale=2,
    ).getInfo()
    std_stats = ndvi.reduceRegion(
        reducer=ee.Reducer.stdDev(),
        geometry=region,
        scale=scale_m,
        maxPixels=1e13,
        bestEffort=True,
        tileScale=2,
    ).getInfo()

    mean_ndvi = stats.get("ndvi_mean")
    min_ndvi = stats.get("ndvi_min")
    max_ndvi = stats.get("ndvi_max")
    std_ndvi = std_stats.get("ndvi")

    hist = classified.reduceRegion(
        reducer=ee.Reducer.frequencyHistogram(),
        geometry=region,
        scale=scale_m,
        maxPixels=1e13,
        bestEffort=True,
        tileScale=2,
    ).getInfo()
    class_hist = hist.get("class") or {}
    count_bare = float(class_hist.get("0", 0) or 0)
    count_stressed = float(class_hist.get("1", 0) or 0)
    count_moderate = float(class_hist.get("2", 0) or 0)
    count_healthy = float(class_hist.get("3", 0) or 0)
    total_count = count_bare + count_stressed + count_moderate + count_healthy

    healthy_pct = (count_healthy / total_count) * 100.0 if total_count else 0.0
    stressed_pct = (count_stressed / total_count) * 100.0 if total_count else 0.0
    moderate_pct = (count_moderate / total_count) * 100.0 if total_count else 0.0
    bare_water_pct = (count_bare / total_count) * 100.0 if total_count else 0.0

    bounds = geometry_bounds(region)

    return {
        "ndvi_map_id": ndvi_map["mapid"],
        "ndvi_token": ndvi_map["token"],
        "ndvi_tile_url": ndvi_map["tile_fetcher"].url_format,
        "classification_map_id": cls_map["mapid"],
        "classification_token": cls_map["token"],
        "classification_tile_url": cls_map["tile_fetcher"].url_format,
        "ndvi_stats": {
            "mean": mean_ndvi,
            "min": min_ndvi,
            "max": max_ndvi,
            "std": std_ndvi,
            "healthy_pct": healthy_pct,
            "stressed_pct": stressed_pct,
            "moderate_pct": moderate_pct,
            "bare_water_pct": bare_water_pct,
            "total_pixels": int(total_count),
        },
        "legend": build_legend(),
        "bounds": bounds,
        "scale_m": scale_m,
        "dos_preview": "DOS applied on red/nir (2nd percentile subtraction)",
    }


def classify_label_from_ndvi(v: float) -> Tuple[str, str]:
    if v <= 0.1:
        return "Bare Soil / Water", CLASS_BREAKS[0]["color"]
    if v <= 0.3:
        return "Stressed Vegetation", CLASS_BREAKS[1]["color"]
    if v <= 0.5:
        return "Moderate Vegetation", CLASS_BREAKS[2]["color"]
    return "Healthy Vegetation", CLASS_BREAKS[3]["color"]


def sample_ndvi_at_point(
    lat: float,
    lon: float,
    roi_geojson: Dict[str, Any],
    start_date: str,
    end_date: str,
    satellite: str,
    max_cloud_pct: float,
) -> Dict[str, Any]:
    """Pixel-scale NDVI sample near click (buffered point)."""
    pipe = compute_ndvi_pipeline(roi_geojson, start_date, end_date, satellite, max_cloud_pct, False)
    ndvi = pipe["ndvi"]
    scale_m = pipe["scale_m"]
    pt = ee.Geometry.Point([lon, lat])
    geom = pt.buffer(scale_m * 0.6)
    val = ndvi.reduceRegion(
        reducer=ee.Reducer.mean(),
        geometry=geom,
        scale=scale_m,
        maxPixels=1e9,
        bestEffort=True,
    ).getInfo()
    raw = val.get("ndvi")
    if raw is None:
        return {"ndvi": None, "vegetation_status": "No data", "class_color": "#888888"}
    label, color = classify_label_from_ndvi(float(raw))
    return {"ndvi": float(raw), "vegetation_status": label, "class_color": color}


def export_geotiff_url(ndvi: ee.Image, region: ee.Geometry, scale: float) -> str:
    """Get download URL for GeoTIFF (may fail for very large requests)."""
    return ndvi.clip(region).getDownloadURL(
        {
            "region": region,
            "scale": scale,
            "crs": "EPSG:4326",
            "format": "GeoTIFF",
            "maxPixels": 1e9,
        }
    )
