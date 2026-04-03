"""PostgreSQL ORM models for analysis runs and cached metadata."""

import uuid
from datetime import datetime

from sqlalchemy import JSON, Column, DateTime, Float, String, Text, Uuid

from app.database import Base


class AnalysisRun(Base):
    __tablename__ = "analysis_runs"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    satellite = Column(String(32), nullable=False)
    start_date = Column(String(10), nullable=False)
    end_date = Column(String(10), nullable=False)
    roi_geojson = Column(JSON, nullable=False)
    mean_ndvi = Column(Float, nullable=True)
    min_ndvi = Column(Float, nullable=True)
    max_ndvi = Column(Float, nullable=True)
    health_summary = Column(Text, nullable=True)
    extra_stats = Column(JSON, nullable=True)
    params_snapshot = Column(JSON, nullable=True)


class TimeseriesCache(Base):
    """Optional row for tracking heavy time-series job ids (future use)."""

    __tablename__ = "timeseries_cache"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cache_key = Column(String(256), unique=True, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    payload = Column(JSON, nullable=True)
