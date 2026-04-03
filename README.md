 HEAD
# NDVI Vegetation Health Monitor

End-to-end web application for **automated** NDVI analysis using **Google Earth Engine (GEE)** on the backend (FastAPI + PostgreSQL) and a **React + Vite + Tailwind + Leaflet + Recharts** dashboard.

No manual image uploads: the user draws an ROI (or uses coordinates), selects a date range and satellite source, and the pipeline pulls and processes imagery in GEE.

## Architecture

| Layer | Implementation |
|--------|----------------|
| Data source | Sentinel-2 `COPERNICUS/S2_SR_HARMONIZED`, Landsat 8/9 `LANDSAT/LC08|LC09/C02/T1_L2`, cloud &lt; configurable % |
| Preprocess | Surface reflectance scaling, QA cloud masks (S2 QA60, Landsat QA_PIXEL), **DOS** on red/NIR, median composite |
| NDVI | \((NIR - Red) / (NIR + Red)\), clamped to \([-1, 1]\) |
| Analysis | Zonal stats, **Random Forest** on spectral bands with NDVI-derived labels, optional **KMeans** |
| Temporal | Monthly NDVI composites, trend & z-score anomalies |
| Output | GEE map tiles, PDF/CSV/GeoTIFF download, disk cache |

## Prerequisites

- Python 3.11+ recommended (3.12 tested)
- Node.js 18+
- Docker (optional, for PostgreSQL)
- Google Earth Engine: [sign up](https://earthengine.google.com/), Cloud project, and authentication

### Earth Engine authentication

1. Install CLI: `pip install earthengine-api`
2. User auth (development): `earthengine authenticate`
3. Set `GEE_PROJECT` in `backend/.env` to your EE-registered Google Cloud project id.
4. For servers, use a **service account** with EE access and set `GEE_SERVICE_ACCOUNT_JSON` (or `GOOGLE_APPLICATION_CREDENTIALS`) to the JSON key path.
5. In Google Cloud: enable the **Earth Engine API** for that project, and register the service account per [Service accounts](https://developers.google.com/earth-engine/guides/service_account).
6. Verify from `backend/`: `python scripts/verify_gee.py` — should print `OK` after configuration is correct.

## Installation

### 1. PostgreSQL
=======
#  NDVI Vegetation Health Monitoring System

A smart agriculture system using satellite-based NDVI to monitor vegetation health, detect crop stress, and identify anomalies. It combines preprocessing and time-series analysis to support efficient precision agriculture.

---

## Features

*  NDVI-based vegetation monitoring
*  Vegetation classification (Healthy, Moderate, Stressed)
*  Time-series NDVI analysis
*  Crop stress and anomaly detection
*  Machine learning (Isolation Forest, KMeans)
*  Interactive map visualization
*  Export results (PDF, CSV, GeoTIFF)
*  Optional IoT sensor integration

---

##  Architecture

| Layer         | Implementation                               |
| ------------- | -------------------------------------------- |
| Data Source   | Sentinel-2, Landsat (Google Earth Engine)    |
| Preprocessing | Cloud masking, DOS correction, normalization |
| NDVI          | (NIR - Red) / (NIR + Red)                    |
| Analysis      | Zonal stats, ML models                       |
| Temporal      | NDVI time-series & change detection          |
| Output        | Maps, graphs, downloadable reports           |

---

##  Technologies Used

### Backend

* FastAPI
* NumPy, Pandas
* Scikit-learn
* Google Earth Engine API

### Frontend

* React (Vite)
* Tailwind CSS
* Leaflet (Maps)
* Recharts

### Database

* PostgreSQL

---

##  Installation

### 1. Start Database
>>>>>>> a07a70b0e94c7850b24c6ff3b5d1d09d94e23e14

```bash
docker compose up -d
```

 HEAD
This exposes PostgreSQL on `localhost:5432` with user/password/db `ndvi` / `ndvi` / `ndvi_db`.

### 2. Backend

```bash
cd backend
copy .env.example .env
# Edit .env — set GEE_PROJECT and DATABASE_URL if needed
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API (see OpenAPI at `http://127.0.0.1:8000/docs`):

- `POST /get-ndvi` — NDVI + classification tiles, stats, `run_id`
- `POST /get-ndvi/latest` — latest clear composite (widens search if needed)
- `POST /get-timeseries` — monthly NDVI series + change/anomalies
- `POST /get-analysis` — zonal stats, RF + optional KMeans, crop suggestions
- `POST /sample-ndvi-point` — NDVI + class at clicked location
- `GET /download-report?run_id=...&format=pdf|csv|geotiff`

### 3. Frontend
=======
### 2. Backend Setup

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### 3. Frontend Setup
>>>>>>> a07a70b0e94c7850b24c6ff3b5d1d09d94e23e14

```bash
cd frontend
npm install
npm run dev
```
HEAD
Open `http://localhost:5173`. The Vite dev server proxies API calls to `http://127.0.0.1:8000`.

## Sample test (no GEE)

From `backend/`:

```bash
pytest -q
```

Schema tests run without Earth Engine or database.

## Production notes

- Put Uvicorn behind **nginx** or a cloud load balancer; restrict CORS to your UI origin.
- GEE **GeoTIFF** `getDownloadURL` has size limits; very large ROIs may need `Export` to Cloud Storage instead.
- Tune `CACHE_DIR` and HTTP caching for repeated identical analyses.

## Project layout

```
NDVI/
  backend/           # FastAPI, GEE services, PostgreSQL models
  frontend/          # Vite React app
  docker-compose.yml # PostgreSQL
```

## License

Use and modify for your organization as needed.
=======
---

##  Usage

1. Select region (ROI) or coordinates
2. Choose date range and satellite source
3. Run NDVI analysis
4. View results on map and graphs
5. Download reports

---

##  Outputs

* NDVI maps
* Vegetation classification
* Time-series trends
* Anomaly detection
* Crop recommendations

---

##  Applications

* Precision agriculture
* Crop health monitoring
* Resource optimization
* Environmental analysis

---

## 🔮 Future Scope

* IoT sensor integration
* Weather data integration
* Mobile application
* Advanced AI models

---

##  Authors

* Balakrishna Yalamanchi
* Team Members

---

##  License

This project may be subject to patent protection. Unauthorized copying, distribution, or commercial use of this system or its components is prohibited without prior permission from the authors.
 a07a70b0e94c7850b24c6ff3b5d1d09d94e23e14
