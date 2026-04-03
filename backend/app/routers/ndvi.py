"""POST /get-ndvi — NDVI tiles, classification, stats."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import AnalysisRun
from app.schemas import NDVIRequest, NDVIResponse, SamplePointRequest, SamplePointResponse
from app.services.cache_service import ndvi_cache
from app.services import ndvi_service

router = APIRouter()


@router.post("/sample-ndvi-point", response_model=SamplePointResponse)
def post_sample_ndvi_point(body: SamplePointRequest):
    max_cloud = body.max_cloud_pct if body.max_cloud_pct is not None else 20.0
    try:
        out = ndvi_service.sample_ndvi_at_point(
            body.lat, body.lon, body.roi, body.start_date, body.end_date, body.satellite, max_cloud
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return SamplePointResponse(
        ndvi=out.get("ndvi"),
        vegetation_status=out.get("vegetation_status", ""),
        class_color=out.get("class_color", "#888888"),
    )


@router.post("/get-ndvi", response_model=NDVIResponse)
def post_get_ndvi(body: NDVIRequest, db: Session = Depends(get_db)):
    max_cloud = body.max_cloud_pct if body.max_cloud_pct is not None else 20.0
    cache_payload = {
        "roi": body.roi,
        "start": body.start_date,
        "end": body.end_date,
        "satellite": body.satellite,
        "cloud": max_cloud,
    }
    cached = ndvi_cache.get_json("ndvi", cache_payload)
    if cached:
        return NDVIResponse(**cached)

    try:
        result = ndvi_service.run_ndvi_for_request(
            body.roi, body.start_date, body.end_date, body.satellite, max_cloud, False
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    mean = result["ndvi_stats"].get("mean")
    health = "Low Vegetation Detected" if mean is not None and mean < 0.3 else "Vegetation within acceptable range"

    run_id = str(uuid.uuid4())
    row = AnalysisRun(
        id=uuid.UUID(run_id),
        satellite=body.satellite,
        start_date=body.start_date,
        end_date=body.end_date,
        roi_geojson=body.roi if isinstance(body.roi, dict) else {},
        mean_ndvi=mean,
        min_ndvi=result["ndvi_stats"].get("min"),
        max_ndvi=result["ndvi_stats"].get("max"),
        health_summary=health,
        extra_stats={"ndvi_stats": result["ndvi_stats"], "legend": result["legend"]},
        params_snapshot={
            "roi": body.roi,
            "start_date": body.start_date,
            "end_date": body.end_date,
            "satellite": body.satellite,
            "max_cloud_pct": max_cloud,
        },
    )
    db.add(row)
    db.commit()

    resp = NDVIResponse(
        map_id=result["ndvi_map_id"],
        map_token=result["ndvi_token"],
        tile_fetcher=result["ndvi_tile_url"],
        classification_map_id=result["classification_map_id"],
        classification_token=result["classification_token"],
        classification_tile_url=result["classification_tile_url"],
        ndvi_stats=result["ndvi_stats"],
        legend=result["legend"],
        bounds=result["bounds"],
        run_id=run_id,
        message=health if mean is not None and mean < 0.3 else None,
    )
    ndvi_cache.set_json("ndvi", cache_payload, resp.model_dump(), expire=7200)
    return resp


@router.post("/get-ndvi/latest", response_model=NDVIResponse)
def post_get_ndvi_latest(body: NDVIRequest, db: Session = Depends(get_db)):
    """Real-time style NDVI: median of latest clear scenes (widens search if needed)."""
    max_cloud = body.max_cloud_pct if body.max_cloud_pct is not None else 30.0
    try:
        result = ndvi_service.run_ndvi_for_request(
            body.roi, body.start_date, body.end_date, body.satellite, max_cloud, True
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    mean = result["ndvi_stats"].get("mean")
    health = "Low Vegetation Detected" if mean is not None and mean < 0.3 else "Vegetation within acceptable range"
    run_id = str(uuid.uuid4())
    row = AnalysisRun(
        id=uuid.UUID(run_id),
        satellite=body.satellite,
        start_date=body.start_date,
        end_date=body.end_date,
        roi_geojson=body.roi if isinstance(body.roi, dict) else {},
        mean_ndvi=mean,
        min_ndvi=result["ndvi_stats"].get("min"),
        max_ndvi=result["ndvi_stats"].get("max"),
        health_summary=health,
        extra_stats={"ndvi_stats": result["ndvi_stats"], "legend": result["legend"], "mode": "latest"},
        params_snapshot={
            "roi": body.roi,
            "start_date": body.start_date,
            "end_date": body.end_date,
            "satellite": body.satellite,
            "max_cloud_pct": max_cloud,
        },
    )
    db.add(row)
    db.commit()

    return NDVIResponse(
        map_id=result["ndvi_map_id"],
        map_token=result["ndvi_token"],
        tile_fetcher=result["ndvi_tile_url"],
        classification_map_id=result["classification_map_id"],
        classification_token=result["classification_token"],
        classification_tile_url=result["classification_tile_url"],
        ndvi_stats=result["ndvi_stats"],
        legend=result["legend"],
        bounds=result["bounds"],
        run_id=run_id,
        message="Latest available composite" + (f" — {health}" if mean is not None and mean < 0.3 else ""),
    )
