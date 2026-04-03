"""POST /get-timeseries — monthly NDVI series, change detection, anomalies."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.schemas import TimeseriesPoint, TimeseriesRequest, TimeseriesResponse
from app.services import analysis_service

router = APIRouter()


@router.post("/get-timeseries", response_model=TimeseriesResponse)
def post_get_timeseries(body: TimeseriesRequest):
    max_cloud = body.max_cloud_pct if body.max_cloud_pct is not None else 20.0
    try:
        out = analysis_service.build_timeseries(
            body.roi, body.start_date, body.end_date, body.satellite, max_cloud
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    series = [
        TimeseriesPoint(
            date=s["date"],
            mean_ndvi=s.get("mean_ndvi"),
            median_ndvi=s.get("median_ndvi"),
            cloud_fraction=s.get("cloud_fraction"),
            note=s.get("note"),
        )
        for s in out["series"]
    ]
    return TimeseriesResponse(
        series=series,
        change_summary=out.get("change_summary", {}),
        anomalies=out.get("anomalies", []),
    )
