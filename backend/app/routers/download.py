"""GET /download-report — PDF, CSV, GeoTIFF link."""

from __future__ import annotations

import csv
import io
import uuid as uuid_mod

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse, Response, StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import AnalysisRun
from app.services import analysis_service
from app.services.report_service import build_pdf_report

router = APIRouter()


@router.get("/download-report")
def get_download_report(
    run_id: uuid_mod.UUID = Query(..., description="Analysis run UUID from /get-ndvi"),
    export_format: str = Query("pdf", alias="format", description="pdf | csv | geotiff"),
    db: Session = Depends(get_db),
):
    row = db.get(AnalysisRun, run_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Run not found")

    fmt = export_format.lower().strip()
    params = row.params_snapshot or {}
    roi = params.get("roi") or row.roi_geojson
    if not roi:
        raise HTTPException(status_code=400, detail="No ROI stored for this run")

    start = params.get("start_date") or row.start_date
    end = params.get("end_date") or row.end_date
    sat = params.get("satellite") or row.satellite
    cloud = float(params.get("max_cloud_pct", 20.0))

    if fmt == "pdf":
        sections = {
            "Summary": {
                "Satellite": sat,
                "Period": f"{start} — {end}",
                "Mean NDVI": row.mean_ndvi,
                "Min NDVI": row.min_ndvi,
                "Max NDVI": row.max_ndvi,
                "Alert": row.health_summary or "",
            },
            "Notes": "Automated NDVI report from Google Earth Engine pipeline (DOS, cloud mask, median composite).",
        }
        if row.extra_stats:
            sections["Extra"] = row.extra_stats
        pdf_bytes = build_pdf_report("NDVI Vegetation Report", sections)
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="ndvi-report-{run_id}.pdf"'},
        )

    if fmt == "csv":
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(["field", "value"])
        w.writerow(["run_id", str(run_id)])
        w.writerow(["satellite", sat])
        w.writerow(["start_date", start])
        w.writerow(["end_date", end])
        w.writerow(["mean_ndvi", row.mean_ndvi])
        w.writerow(["min_ndvi", row.min_ndvi])
        w.writerow(["max_ndvi", row.max_ndvi])
        w.writerow(["health", row.health_summary])
        return StreamingResponse(
            iter([buf.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="ndvi-stats-{run_id}.csv"'},
        )

    if fmt == "geotiff":
        try:
            url = analysis_service.geotiff_download_url(roi, start, end, sat, cloud)
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e)) from e
        return RedirectResponse(url)

    raise HTTPException(status_code=400, detail="format must be pdf, csv, or geotiff")
