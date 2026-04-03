"""
Local GeoTIFF helpers using Rasterio (e.g. after downloading from GEE).
The live NDVI pipeline runs entirely in Earth Engine.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import rasterio


def read_geotiff_profile(path: str | Path) -> Dict[str, Any]:
    """Return raster metadata profile for a GeoTIFF on disk."""
    with rasterio.open(path) as ds:
        return dict(ds.profile)
