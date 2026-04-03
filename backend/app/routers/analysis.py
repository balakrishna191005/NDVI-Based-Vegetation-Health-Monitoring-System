"""POST /get-analysis — zonal stats, RF, KMeans."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.schemas import AnalysisRequest, AnalysisResponse
from app.services import analysis_service

router = APIRouter()


@router.post("/get-analysis", response_model=AnalysisResponse)
def post_get_analysis(body: AnalysisRequest):
    max_cloud = body.max_cloud_pct if body.max_cloud_pct is not None else 20.0
    try:
        out = analysis_service.run_extended_analysis(
            body.roi,
            body.start_date,
            body.end_date,
            body.satellite,
            max_cloud,
            body.include_kmeans,
            body.rf_trees,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    return AnalysisResponse(
        zonal=out.get("zonal", {}),
        zones=out.get("zones", []),
        health_distribution=out.get("health_distribution", {}),
        anomaly_detection=out.get("anomaly_detection", {}),
        model_performance=out.get("model_performance", {}),
        rf_map_id=out.get("rf_map_id"),
        rf_token=out.get("rf_token"),
        rf_tile_url=out.get("rf_tile_url"),
        rf_legend=out.get("rf_legend", []),
        kmeans_map_id=out.get("kmeans_map_id"),
        kmeans_token=out.get("kmeans_token"),
        kmeans_tile_url=out.get("kmeans_tile_url"),
        fertilizer_recommendation=out.get("fertilizer_recommendation", {}),
        irrigation_plan=out.get("irrigation_plan", {}),
    )
