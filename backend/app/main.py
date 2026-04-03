"""
NDVI Vegetation Monitor — FastAPI application.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import Base, engine
from app.routers import analysis, download, ndvi, timeseries


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


settings = get_settings()
app = FastAPI(title=settings.app_name, lifespan=lifespan)

origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ndvi.router, tags=["ndvi"])
app.include_router(timeseries.router, tags=["timeseries"])
app.include_router(analysis.router, tags=["analysis"])
app.include_router(download.router, tags=["download"])


@app.get("/health")
def health():
    return {"status": "ok", "service": settings.app_name}
