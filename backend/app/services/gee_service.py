"""
Google Earth Engine: initialization, collections, geometry helpers, cloud filtering.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Tuple

import ee
from ee import oauth as ee_oauth
from google.oauth2 import service_account

from app.config import get_settings

logger = logging.getLogger(__name__)
_initialized = False


def _project_id_from_service_account_json(key_path: str) -> Optional[str]:
    """Read project_id from a Google service account JSON key file."""
    try:
        p = Path(key_path)
        if not p.is_file():
            return None
        with p.open(encoding="utf-8") as f:
            data = json.load(f)
        return data.get("project_id")
    except (OSError, json.JSONDecodeError, TypeError):
        return None


def _resolve_service_account_key_path(settings) -> Optional[str]:
    """Prefer GEE_SERVICE_ACCOUNT_JSON; else standard GOOGLE_APPLICATION_CREDENTIALS."""
    for raw in (settings.gee_service_account_json, os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")):
        if not raw:
            continue
        p = Path(raw)
        if p.is_file():
            return str(p.resolve())
    return None


def _earth_engine_access_help(service_account_key_path: Optional[str], project: Optional[str]) -> str:
    """Human-readable fix for common EE registration errors."""
    api_link = ""
    if project:
        api_link = (
            f"\n• Enable Earth Engine API (open, then Enable):\n"
            f"  https://console.cloud.google.com/apis/library/earthengine.googleapis.com?project={project}\n"
        )
    if service_account_key_path:
        return (
            "Earth Engine blocked this service account. Complete these in Google Cloud (the app cannot bypass Google):\n"
            f"{api_link}"
            "• Register **client_email** from your JSON for Earth Engine:\n"
            "  https://developers.google.com/earth-engine/guides/service_account\n"
            "• Set **GEE_PROJECT** = **project_id** from the same JSON in backend/.env; restart the API.\n"
            "• Key file: GEE_SERVICE_ACCOUNT_JSON or GOOGLE_APPLICATION_CREDENTIALS must exist on disk."
        )
    return (
        "Earth Engine is not enabled for this user/project.\n"
        "1) Request access: https://earthengine.google.com/signup/\n"
        "2) Register a Cloud project: https://developers.google.com/earth-engine/guides/access\n"
        "3) Set GEE_PROJECT in backend/.env to that Cloud project ID.\n"
        "4) Run: earthengine authenticate && earthengine set_project YOUR_PROJECT_ID"
    )


def _is_access_configuration_error(message: str) -> bool:
    m = message.lower()
    needles = (
        "not signed up",
        "not registered",
        "permission denied",
        "permission_denied",
        "has not been registered",
        "earth engine api has not been used",
        "has not been used in project",
        "api has not been enabled",
        "access not configured",
    )
    return any(n in m for n in needles)


def initialize_gee() -> None:
    """Initialize Earth Engine once (service account key file or user OAuth)."""
    global _initialized
    if _initialized:
        return
    settings = get_settings()
    key_path = _resolve_service_account_key_path(settings)
    project: Optional[str] = settings.gee_project

    try:
        if key_path:
            if not project:
                project = _project_id_from_service_account_json(key_path)
            if not project:
                raise RuntimeError(
                    "Set GEE_PROJECT in backend/.env to your Google Cloud project ID, "
                    "or ensure the service account JSON file contains a project_id field."
                )
            credentials = service_account.Credentials.from_service_account_file(
                key_path,
                scopes=ee_oauth.SCOPES,
            )
            ee.Initialize(credentials, project=project)
        elif project:
            ee.Initialize(project=project)
        else:
            ee.Initialize()
        _initialized = True
        logger.info("Earth Engine initialized (project=%s, service_account=%s).", project, bool(key_path))
    except Exception as e:
        logger.warning("GEE init failed (set GEE_PROJECT or run earthengine authenticate): %s", e)
        if _is_access_configuration_error(str(e)):
            raise RuntimeError(_earth_engine_access_help(key_path, project)) from e
        raise


def geojson_to_ee_geometry(geojson: dict | str) -> ee.Geometry:
    if isinstance(geojson, str):
        geojson = json.loads(geojson)

    if not geojson:
        raise ValueError("GeoJSON is empty")

    if geojson.get("type") == "Feature":
        geojson = geojson.get("geometry")

    if "coordinates" not in geojson:
        raise ValueError("Invalid GeoJSON: missing coordinates")

    coords = geojson["coordinates"]

    return ee.Geometry.Polygon(coords)


def _normalize_filter_dates(start: str, end: str) -> Tuple[str, str]:
    """Return a safe [start, end_exclusive) range for ee.FilterDate/filterDate.

    Earth Engine date filters use an exclusive end date. If caller passes the same
    start/end day, expand by one day so a one-day query remains valid.
    """
    try:
        s = datetime.strptime(start, "%Y-%m-%d").date()
        e = datetime.strptime(end, "%Y-%m-%d").date()
    except ValueError as exc:
        raise ValueError("Dates must be in YYYY-MM-DD format.") from exc

    if e < s:
        raise ValueError("end_date must be on or after start_date.")

    # GEE filterDate end is exclusive; convert same-day requests into one-day windows.
    if e == s:
        e = e + timedelta(days=1)

    return s.isoformat(), e.isoformat()


def sentinel2_collection(start: str, end: str, region: ee.Geometry, max_cloud: float) -> ee.ImageCollection:
    """Harmonized Sentinel-2 L2A surface reflectance."""
    start, end = _normalize_filter_dates(start, end)
    col = (
        ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
        .filterBounds(region)
        .filterDate(start, end)
        .filter(ee.Filter.lte("CLOUDY_PIXEL_PERCENTAGE", max_cloud))
    )
    return col


def landsat89_collection(start: str, end: str, region: ee.Geometry, max_cloud: float) -> ee.ImageCollection:
    """Landsat 8/9 Collection 2 Level-2 surface reflectance."""
    start, end = _normalize_filter_dates(start, end)
    l8 = ee.ImageCollection("LANDSAT/LC08/C02/T1_L2").filterBounds(region).filterDate(start, end)
    l9 = ee.ImageCollection("LANDSAT/LC09/C02/T1_L2").filterBounds(region).filterDate(start, end)
    col = l8.merge(l9).filter(ee.Filter.lte("CLOUD_COVER", max_cloud))
    return col


def mask_s2_clouds(image: ee.Image) -> ee.Image:
    """Cloud mask using QA60 (opaque + cirrus bits)."""
    qa = image.select("QA60")
    cloud_bit_mask = 1 << 10
    cirrus_bit_mask = 1 << 11
    mask = qa.bitwiseAnd(cloud_bit_mask).eq(0).And(qa.bitwiseAnd(cirrus_bit_mask).eq(0))
    return image.updateMask(mask)


def mask_l8_clouds(image: ee.Image) -> ee.Image:
    """Landsat QA_PIXEL: cloud, cloud shadow, snow."""
    qa = image.select("QA_PIXEL")
    # Cloud (bit 3), cloud shadow (bit 4), dilated cloud (bit 1), snow (bit 5)
    cloud = qa.bitwiseAnd(1 << 3).eq(0)
    shadow = qa.bitwiseAnd(1 << 4).eq(0)
    snow = qa.bitwiseAnd(1 << 5).eq(0)
    return image.updateMask(cloud.And(shadow).And(snow))


def sentinel2_to_reflectance(image: ee.Image) -> ee.Image:
    """Scale Sentinel-2 SR to 0–1 surface reflectance (radiometric normalization)."""
    # Harmonized SR: reflectance = DN / 10000
    scaled = image.select(["B4", "B8", "B3", "B11"]).divide(10000).clamp(0, 1)
    return scaled.rename(["red", "nir", "green", "swir1"])


def landsat_to_reflectance(image: ee.Image) -> ee.Image:
    """Landsat C2 L2 optical bands to 0–1 reflectance (TOA-like surface reflectance scaling)."""
    # SR_B4 red, SR_B5 nir — USGS scale factors
    optical = image.select(["SR_B4", "SR_B5", "SR_B3", "SR_B6"]).multiply(0.0000275).add(-0.2).clamp(0, 1)
    return optical.rename(["red", "nir", "green", "swir1"])


def _prep_sentinel2(img: ee.Image) -> ee.Image:
    return sentinel2_to_reflectance(mask_s2_clouds(img))


def _prep_landsat(img: ee.Image) -> ee.Image:
    return landsat_to_reflectance(mask_l8_clouds(img))


def composite_median(
    collection: ee.ImageCollection,
    satellite: str,
) -> Tuple[ee.Image, ee.Image]:
    """
    Build cloud-masked per-image reflectance, return median composite + per-band observation count.
    """
    prep = _prep_sentinel2 if satellite == "sentinel2" else _prep_landsat
    prepared = collection.map(prep)
    median = prepared.median()
    count = prepared.select("red").count().rename("obs_count")
    return median, count


def latest_clear_composite(
    collection: ee.ImageCollection,
    satellite: str,
) -> ee.Image:
    """Median of the 5 most recent cloud-masked composites (real-time / latest NDVI)."""
    prep = _prep_sentinel2 if satellite == "sentinel2" else _prep_landsat
    recent = collection.sort("system:time_start", False).limit(5).map(prep)
    return recent.median()
