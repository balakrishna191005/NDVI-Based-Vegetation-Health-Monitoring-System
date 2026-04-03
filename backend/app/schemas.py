"""Pydantic request/response schemas."""

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class ROIRequest(BaseModel):
    """GeoJSON Polygon geometry or Feature with geometry."""

    roi: Dict[str, Any] = Field(..., description="GeoJSON Polygon or Feature")


class SamplePointRequest(ROIRequest):
    lat: float = Field(..., ge=-90, le=90)
    lon: float = Field(..., ge=-180, le=180)
    start_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    end_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    satellite: Literal["sentinel2", "landsat89"] = "sentinel2"
    max_cloud_pct: Optional[float] = Field(default=None, ge=0, le=100)


class SamplePointResponse(BaseModel):
    ndvi: Optional[float] = None
    vegetation_status: str = ""
    class_color: str = "#888888"


class NDVIRequest(ROIRequest):
    start_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    end_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    satellite: Literal["sentinel2", "landsat89"] = "sentinel2"
    max_cloud_pct: Optional[float] = Field(default=None, ge=0, le=100)


class TimeseriesRequest(ROIRequest):
    start_date: str
    end_date: str
    satellite: Literal["sentinel2", "landsat89"] = "sentinel2"
    max_cloud_pct: Optional[float] = None


class AnalysisRequest(NDVIRequest):
    include_kmeans: bool = True
    rf_trees: int = Field(default=50, ge=10, le=200)


class NDVIResponse(BaseModel):
    success: bool = True
    message: Optional[str] = None
    map_id: Optional[str] = None
    map_token: Optional[str] = None
    tile_fetcher: Optional[str] = None  # GEE XYZ tile URL template
    classification_map_id: Optional[str] = None
    classification_token: Optional[str] = None
    classification_tile_url: Optional[str] = None
    ndvi_stats: Dict[str, Any] = {}
    legend: List[Dict[str, Any]] = []
    bounds: Optional[List[float]] = None
    run_id: Optional[str] = None


class TimeseriesPoint(BaseModel):
    date: str
    mean_ndvi: Optional[float] = None
    median_ndvi: Optional[float] = None
    cloud_fraction: Optional[float] = None
    note: Optional[str] = None


class TimeseriesResponse(BaseModel):
    success: bool = True
    series: List[TimeseriesPoint] = []
    change_summary: Dict[str, Any] = {}
    anomalies: List[Dict[str, Any]] = []


class AnalysisResponse(BaseModel):
    success: bool = True
    zonal: Dict[str, Any] = {}
    zones: List[Dict[str, Any]] = []
    health_distribution: Dict[str, Any] = {}
    anomaly_detection: Dict[str, Any] = {}
    model_performance: Dict[str, Any] = {}
    rf_map_id: Optional[str] = None
    rf_token: Optional[str] = None
    rf_tile_url: Optional[str] = None
    rf_legend: List[Dict[str, Any]] = []
    kmeans_map_id: Optional[str] = None
    kmeans_token: Optional[str] = None
    kmeans_tile_url: Optional[str] = None
    fertilizer_recommendation: Dict[str, Any] = {}
    irrigation_plan: Dict[str, Any] = {}
