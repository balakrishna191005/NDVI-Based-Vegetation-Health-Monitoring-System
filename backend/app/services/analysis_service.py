"""
Zonal statistics, Random Forest (pseudo vegetation classes), KMeans, time series, anomalies.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Tuple

import ee
import numpy as np
from sklearn.ensemble import IsolationForest

from app.services import gee_service, ndvi_service

logger = logging.getLogger(__name__)

RF_LEGEND = [
    {"class_id": 0, "label": "Bare / Water", "color": "#e53935"},
    {"class_id": 1, "label": "Stressed", "color": "#fb8c00"},
    {"class_id": 2, "label": "Moderate", "color": "#fdd835"},
    {"class_id": 3, "label": "Healthy", "color": "#2e7d32"},
]


def _month_starts(start: str, end: str) -> List[Tuple[str, str]]:
    """Split [start, end] into monthly windows (inclusive)."""
    s = datetime.strptime(start, "%Y-%m-%d")
    e = datetime.strptime(end, "%Y-%m-%d")
    windows = []
    cur = s.replace(day=1)
    while cur <= e:
        nxt = (cur.replace(day=28) + timedelta(days=4)).replace(day=1)
        w0 = max(cur, s)
        w1 = min(nxt - timedelta(days=1), e)
        if w0 <= w1:
            windows.append((w0.strftime("%Y-%m-%d"), w1.strftime("%Y-%m-%d")))
        cur = nxt
    return windows


def run_extended_analysis(
    roi_geojson: Dict[str, Any],
    start_date: str,
    end_date: str,
    satellite: str,
    max_cloud_pct: float,
    include_kmeans: bool,
    rf_trees: int,
) -> Dict[str, Any]:
    """RF + KMeans maps + zonal stats + anomaly intelligence + agronomic recommendations."""
    pipe = ndvi_service.compute_ndvi_pipeline(
        roi_geojson, start_date, end_date, satellite, max_cloud_pct, False
    )
    region = pipe["region"]
    scale_m = pipe["scale_m"]
    dos_img = pipe["dos_img"]
    ndvi = pipe["ndvi"]
    classified = pipe["classified"]

    candidate_bands = ["red", "nir", "green", "swir1"]
    available_bands = set(dos_img.bandNames().getInfo() or [])
    bands = [b for b in candidate_bands if b in available_bands]
    if not {"red", "nir"}.issubset(available_bands):
        raise RuntimeError(
            "Required reflectance bands are missing for analysis. "
            f"Available bands: {sorted(available_bands)}"
        )

    training_img = dos_img.select(bands).addBands(classified.rename("natural"))

    # Random sample with NDVI-derived labels (pseudo vegetation types)
    sample = training_img.sample(
        region=region,
        scale=scale_m,
        numPixels=2500,
        seed=42,
        geometries=False,
    )

    classifier = ee.Classifier.smileRandomForest(numberOfTrees=rf_trees).train(
        features=sample,
        classProperty="natural",
        inputProperties=bands,
    )
    rf_classified = dos_img.select(bands).classify(classifier).rename("rf_class")

    # Accuracy is computed on the training sample (resubstitution), so treat as indicative.
    rf_eval = sample.classify(classifier)
    rf_confusion = rf_eval.errorMatrix("natural", "classification")
    rf_accuracy = rf_confusion.accuracy().getInfo()
    rf_kappa = rf_confusion.kappa().getInfo()

    rf_vis = {"min": 0, "max": 3, "palette": ["#e53935", "#fb8c00", "#fdd835", "#2e7d32"]}
    rf_map = rf_classified.getMapId(rf_vis)

    zonal = ndvi.reduceRegion(
        reducer=ee.Reducer.mean().combine(reducer2=ee.Reducer.minMax(), sharedInputs=True),
        geometry=region,
        scale=scale_m,
        maxPixels=1e13,
        bestEffort=True,
        tileScale=2,
    ).getInfo()

    mean_ndvi = zonal.get("ndvi_mean")
    health_distribution = _class_distribution_percentages(classified, region, scale_m)
    zones = _split_two_zone_stats(region, ndvi, scale_m)
    anomaly_detection = _detect_ai_anomalies(ndvi, region, scale_m, health_distribution)
    fertilizer_recommendation = _fertilizer_plan(mean_ndvi, health_distribution, anomaly_detection)
    irrigation_plan = _irrigation_plan(mean_ndvi, health_distribution, anomaly_detection)

    out: Dict[str, Any] = {
        "zonal": {
            "mean_ndvi": mean_ndvi,
            "min_ndvi": zonal.get("ndvi_min"),
            "max_ndvi": zonal.get("ndvi_max"),
            "std_ndvi": _std_ndvi(ndvi, region, scale_m),
        },
        "zones": zones,
        "health_distribution": health_distribution,
        "anomaly_detection": anomaly_detection,
        "model_performance": {
            "rf_accuracy_pct": float(rf_accuracy) * 100.0 if rf_accuracy is not None else None,
            "rf_kappa": float(rf_kappa) if rf_kappa is not None else None,
            "rf_trees": int(rf_trees),
            "evaluation": "resubstitution",
            "note": "Accuracy uses the RF training sample and may overestimate generalization.",
        },
        "rf_map_id": rf_map["mapid"],
        "rf_token": rf_map["token"],
        "rf_tile_url": rf_map["tile_fetcher"].url_format,
        "rf_legend": RF_LEGEND,
        "kmeans_map_id": None,
        "kmeans_token": None,
        "kmeans_tile_url": None,
        "fertilizer_recommendation": fertilizer_recommendation,
        "irrigation_plan": irrigation_plan,
    }

    if include_kmeans:
        try:
            training = dos_img.select(bands).sample(
                region=region,
                scale=scale_m * 3,
                numPixels=1500,
                seed=7,
                geometries=False,
            )
            clusterer = ee.Clusterer.wekaKMeans(nClusters=4).train(training)
            kmeans_result = clusterer.cluster(dos_img.select(bands)).rename("km")
            km_vis = {"min": 0, "max": 3, "palette": ["#4e79a7", "#f28e2b", "#e15759", "#76b7b2"]}
            km_map2 = kmeans_result.getMapId(km_vis)
            out["kmeans_map_id"] = km_map2["mapid"]
            out["kmeans_token"] = km_map2["token"]
            out["kmeans_tile_url"] = km_map2["tile_fetcher"].url_format
        except Exception as ex:
            logger.warning("KMeans clustering skipped: %s", ex)

    return out


def _std_ndvi(ndvi: ee.Image, region: ee.Geometry, scale_m: float) -> float | None:
    stats = ndvi.reduceRegion(
        reducer=ee.Reducer.stdDev(),
        geometry=region,
        scale=scale_m,
        maxPixels=1e13,
        bestEffort=True,
        tileScale=2,
    ).getInfo()
    return stats.get("ndvi")


def _safe_zone_stats(zone: ee.Geometry, ndvi: ee.Image, scale_m: float, name: str) -> Dict[str, Any]:
    stats = ndvi.reduceRegion(
        reducer=ee.Reducer.mean().combine(reducer2=ee.Reducer.minMax(), sharedInputs=True),
        geometry=zone,
        scale=scale_m,
        maxPixels=1e13,
        bestEffort=True,
        tileScale=2,
    ).getInfo()
    std = _std_ndvi(ndvi, zone, scale_m)
    return {
        "zone_name": name,
        "mean_ndvi": stats.get("ndvi_mean"),
        "min_ndvi": stats.get("ndvi_min"),
        "max_ndvi": stats.get("ndvi_max"),
        "std_ndvi": std,
    }


def _split_two_zone_stats(region: ee.Geometry, ndvi: ee.Image, scale_m: float) -> List[Dict[str, Any]]:
    # Split region bounds vertically into two management zones.
    coords = region.bounds().coordinates().getInfo()[0]
    xs = [c[0] for c in coords]
    ys = [c[1] for c in coords]
    west, east = min(xs), max(xs)
    south, north = min(ys), max(ys)
    mid_x = (west + east) / 2.0

    zone_a = ee.Geometry.Rectangle([west, south, mid_x, north]).intersection(region, 1)
    zone_b = ee.Geometry.Rectangle([mid_x, south, east, north]).intersection(region, 1)

    return [
        _safe_zone_stats(zone_a, ndvi, scale_m, "Field A"),
        _safe_zone_stats(zone_b, ndvi, scale_m, "Field B"),
    ]


def _class_distribution_percentages(classified: ee.Image, region: ee.Geometry, scale_m: float) -> Dict[str, Any]:
    hist = classified.reduceRegion(
        reducer=ee.Reducer.frequencyHistogram(),
        geometry=region,
        scale=scale_m,
        maxPixels=1e13,
        bestEffort=True,
        tileScale=2,
    ).getInfo()
    bucket = hist.get("class") or {}

    counts = {
        "bare_water": float(bucket.get("0", 0) or 0),
        "stressed": float(bucket.get("1", 0) or 0),
        "moderate": float(bucket.get("2", 0) or 0),
        "healthy": float(bucket.get("3", 0) or 0),
    }
    total = sum(counts.values())
    if total <= 0:
        return {
            "total_pixels": 0,
            "healthy_pct": 0.0,
            "stressed_pct": 0.0,
            "moderate_pct": 0.0,
            "bare_water_pct": 0.0,
            "counts": counts,
        }

    return {
        "total_pixels": int(total),
        "healthy_pct": (counts["healthy"] / total) * 100.0,
        "stressed_pct": (counts["stressed"] / total) * 100.0,
        "moderate_pct": (counts["moderate"] / total) * 100.0,
        "bare_water_pct": (counts["bare_water"] / total) * 100.0,
        "counts": counts,
    }


def _detect_ai_anomalies(
    ndvi: ee.Image,
    region: ee.Geometry,
    scale_m: float,
    health_distribution: Dict[str, Any],
) -> Dict[str, Any]:
    sampled = ndvi.sample(
        region=region,
        scale=scale_m,
        numPixels=1200,
        seed=23,
        geometries=False,
    ).aggregate_array("ndvi").getInfo()
    values = [float(v) for v in (sampled or []) if v is not None]

    if len(values) < 30:
        return {
            "model": "isolation_forest",
            "status": "insufficient_samples",
            "sample_size": len(values),
            "anomaly_ratio_pct": 0.0,
            "severity": "unknown",
            "note": "Not enough valid NDVI samples for AI anomaly scoring.",
        }

    X = np.array(values, dtype=float).reshape(-1, 1)
    model = IsolationForest(contamination=0.12, random_state=42)
    pred = model.fit_predict(X)
    score = model.score_samples(X)
    anomaly_mask = pred == -1
    anomaly_ratio = float(np.mean(anomaly_mask) * 100.0)
    anomaly_values = X[anomaly_mask]
    avg_anomaly_ndvi = float(np.mean(anomaly_values)) if anomaly_values.size else None
    baseline_ndvi = float(np.mean(X))
    severity = "high" if anomaly_ratio >= 20 else ("moderate" if anomaly_ratio >= 10 else "low")

    stressed_pct = float(health_distribution.get("stressed_pct", 0.0) or 0.0)
    if stressed_pct >= 35 and severity != "high":
        severity = "high"

    return {
        "model": "isolation_forest",
        "status": "ok",
        "sample_size": len(values),
        "anomaly_ratio_pct": anomaly_ratio,
        "severity": severity,
        "baseline_mean_ndvi": baseline_ndvi,
        "anomaly_mean_ndvi": avg_anomaly_ndvi,
        "score_min": float(np.min(score)),
        "score_max": float(np.max(score)),
    }


def _fertilizer_plan(
    mean_ndvi: float | None,
    health_distribution: Dict[str, Any],
    anomaly_detection: Dict[str, Any],
) -> Dict[str, Any]:
    stressed_pct = float(health_distribution.get("stressed_pct", 0.0) or 0.0)
    healthy_pct = float(health_distribution.get("healthy_pct", 0.0) or 0.0)
    severity = anomaly_detection.get("severity", "unknown")

    if mean_ndvi is None:
        return {
            "priority": "undetermined",
            "rate_hint": "Collect field samples before fertilization changes.",
            "recommended_products": [
                "Urea (46-0-0)",
                "DAP - Diammonium Phosphate (18-46-0)",
                "MOP - Muriate of Potash (0-0-60)",
                "Zinc Sulphate (ZnSO4 33%)",
            ],
            "actions": ["Run soil test for N-P-K and pH.", "Delay variable-rate fertilizer prescription."],
        }
    if mean_ndvi < 0.3 or stressed_pct > 30 or severity == "high":
        return {
            "priority": "high",
            "rate_hint": "Apply split nitrogen using specific products in stressed zones.",
            "recommended_products": [
                "Urea (46-0-0)",
                "CAN - Calcium Ammonium Nitrate (26-0-0)",
                "NPK 19-19-19 (water-soluble)",
                "Zinc Sulphate (ZnSO4 33%)",
            ],
            "actions": [
                "Use zone-specific top-dressing in Field A/B instead of uniform broadcast.",
                "Prioritize N + Zn in low-NDVI patches after irrigation event.",
                "Re-check NDVI in 7-10 days to verify response.",
            ],
        }
    if mean_ndvi < 0.5 or stressed_pct > 15:
        return {
            "priority": "medium",
            "rate_hint": "Maintain moderate nutrient program using balanced products.",
            "recommended_products": [
                "NPK 20-20-20",
                "DAP - Diammonium Phosphate (18-46-0)",
                "MOP - Muriate of Potash (0-0-60)",
                "Urea (46-0-0)",
            ],
            "actions": [
                "Increase nutrient rate only where NDVI remains below field median.",
                "Use slow-release N to reduce leaching risk.",
            ],
        }
    return {
        "priority": "low",
        "rate_hint": "Maintain baseline fertility; avoid over-application.",
        "recommended_products": [
            "NPK 10-26-26",
            "SSP - Single Super Phosphate (0-16-0)",
            "MOP - Muriate of Potash (0-0-60)",
        ],
        "actions": [
            "Apply maintenance fertilizer based on expected yield.",
            "Healthy area above %.1f%%: keep current nutrient schedule." % healthy_pct,
        ],
    }


def _irrigation_plan(
    mean_ndvi: float | None,
    health_distribution: Dict[str, Any],
    anomaly_detection: Dict[str, Any],
) -> Dict[str, Any]:
    stressed_pct = float(health_distribution.get("stressed_pct", 0.0) or 0.0)
    anomaly_ratio = float(anomaly_detection.get("anomaly_ratio_pct", 0.0) or 0.0)

    if mean_ndvi is None:
        return {
            "strategy": "monitor",
            "frequency_hint": "Use soil moisture probes before scheduling irrigation.",
            "actions": ["Validate irrigation block flow rates.", "Map dry spots with field scouting."],
        }
    if mean_ndvi < 0.3 or stressed_pct >= 30 or anomaly_ratio >= 18:
        return {
            "strategy": "intensive",
            "frequency_hint": "Short, frequent irrigation cycles focused on stressed zones.",
            "actions": [
                "Prioritize Field with lower NDVI for first irrigation turn.",
                "Irrigate early morning to reduce evapotranspiration loss.",
                "Reassess NDVI and anomaly score after 3-5 days.",
            ],
        }
    if mean_ndvi < 0.5 or stressed_pct >= 15:
        return {
            "strategy": "balanced",
            "frequency_hint": "Maintain normal schedule, increase depth only in stressed sub-zones.",
            "actions": [
                "Use alternating zone irrigation to avoid runoff.",
                "Track field moisture variability weekly.",
            ],
        }
    return {
        "strategy": "maintenance",
        "frequency_hint": "Keep current schedule; avoid excessive watering.",
        "actions": [
            "Maintain baseline irrigation with weather-adjusted offsets.",
            "Inspect emitters for uniform distribution once per week.",
        ],
    }


def build_timeseries(
    roi_geojson: Dict[str, Any],
    start_date: str,
    end_date: str,
    satellite: str,
    max_cloud_pct: float,
) -> Dict[str, Any]:
    """Monthly NDVI composites + change detection + simple anomaly flags."""
    gee_service.initialize_gee()
    region = gee_service.geojson_to_ee_geometry(roi_geojson)
    scale_m = 10.0 if satellite == "sentinel2" else 30.0

    series: List[Dict[str, Any]] = []
    windows = _month_starts(start_date, end_date)
    if not windows:
        windows = [(start_date, end_date)]

    for w0, w1 in windows:
        if satellite == "sentinel2":
            col = gee_service.sentinel2_collection(w0, w1, region, max_cloud_pct)
        else:
            col = gee_service.landsat89_collection(w0, w1, region, max_cloud_pct)

        if col.size().getInfo() == 0:
            series.append(
                {
                    "date": w0[:7],
                    "mean_ndvi": None,
                    "median_ndvi": None,
                    "cloud_fraction": None,
                    "note": "no_data",
                }
            )
            continue

        reflectance, _ = gee_service.composite_median(col, satellite)
        _, ndvi = ndvi_service.full_preprocess_pipeline(reflectance, region, scale_m)
        stat = ndvi.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=region,
            scale=scale_m,
            maxPixels=1e13,
            bestEffort=True,
            tileScale=2,
        ).getInfo()
        stat_med = ndvi.reduceRegion(
            reducer=ee.Reducer.median(),
            geometry=region,
            scale=scale_m,
            maxPixels=1e13,
            bestEffort=True,
            tileScale=2,
        ).getInfo()
        mean_ndvi = stat.get("ndvi")
        med_ndvi = stat_med.get("ndvi")
        series.append(
            {
                "date": w0[:7],
                "mean_ndvi": mean_ndvi,
                "median_ndvi": med_ndvi,
                "cloud_fraction": None,
            }
        )

    values = [s["mean_ndvi"] for s in series if s.get("mean_ndvi") is not None]
    change_summary: Dict[str, Any] = {}
    anomalies: List[Dict[str, Any]] = []

    if len(values) >= 2:
        first, last = values[0], values[-1]
        delta = last - first
        change_summary = {
            "first_mean_ndvi": first,
            "last_mean_ndvi": last,
            "delta": delta,
            "trend": "increase" if delta > 0.02 else ("decrease" if delta < -0.02 else "stable"),
        }

    if values:
        import statistics

        mu = statistics.mean(values)
        try:
            sigma = statistics.pstdev(values)
        except statistics.StatisticsError:
            sigma = 0.0
        for s in series:
            v = s.get("mean_ndvi")
            if v is None or sigma == 0:
                continue
            z = (v - mu) / sigma if sigma else 0.0
            if z < -1.5:
                anomalies.append(
                    {
                        "period": s["date"],
                        "type": "stress_or_drought_signal",
                        "z_score": z,
                        "detail": "NDVI significantly below period average.",
                    }
                )
            elif z > 1.5:
                anomalies.append(
                    {
                        "period": s["date"],
                        "type": "high_vigor",
                        "z_score": z,
                        "detail": "NDVI above typical for this series.",
                    }
                )

    return {"series": series, "change_summary": change_summary, "anomalies": anomalies}


def geotiff_download_url(
    roi_geojson: Dict[str, Any],
    start_date: str,
    end_date: str,
    satellite: str,
    max_cloud_pct: float,
) -> str:
    pipe = ndvi_service.compute_ndvi_pipeline(
        roi_geojson, start_date, end_date, satellite, max_cloud_pct, False
    )
    ndvi = pipe["ndvi"]
    region = pipe["region"]
    scale_m = pipe["scale_m"]
    return ndvi_service.export_geotiff_url(ndvi, region, scale_m)
