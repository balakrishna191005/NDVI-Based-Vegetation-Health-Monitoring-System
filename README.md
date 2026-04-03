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

```bash
docker compose up -d
```

### 2. Backend Setup

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### 3. Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

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
