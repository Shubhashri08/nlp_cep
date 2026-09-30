# AI-Driven Urban Planning Decision Support System

A complete, production-grade, end-to-end Urban Planning Decision Support System (DSS) built with FastAPI, PostgreSQL/PostGIS, Scikit-learn, Sentinel-2 remote sensing processing, and React + TypeScript + Leaflet.

---

## 🏛️ System Features & Capabilities

1. **Multilingual NLP Grievance Pipeline**:
   - Ingests citizen feedback in English, Devanagari Hindi, Marathi, and code-mixed Hinglish.
   - Normalizes slang/urban terms (e.g., *khadde* &rarr; *potholes*, *paani* &rarr; *water*).
   - Multi-label classification across 17 municipal sectors (`ROAD_INFRASTRUCTURE`, `FLOODING`, `DRAINAGE`, `WASTE_MANAGEMENT`, etc.).
   - Named Entity Recognition for wards, roads, landmarks, and infrastructure types.
   - Geocoding resolution to exact coordinates with Nominatim & authoritative gazetteer fallback.
   - 64-dimensional dense semantic embedding generation for vector similarity search.

2. **Interactive GIS Explorer**:
   - Leaflet-based map with dark-matter cartography.
   - Municipal ward boundary GeoJSON polygons with population density & priority choropleth.
   - DBSCAN spatial clustering for grievance hotspots.
   - Click-to-inspect ward drawer with demographic profile, infrastructure gaps, environmental risks, and recommendations.

3. **Infrastructure Gap Analyzer**:
   - Compares real population demand against supply using URDPFI & CPHEEO national standards (135 LPCD potable water, 0.45 kg/day waste, WHO hospital beds, and storm drain length).

4. **Satellite Remote Sensing & Urban Growth**:
   - Processes multi-spectral optical reflectance bands into NDVI (Vegetation), NDBI (Built-up), and NDWI (Water bodies).
   - Tracks 2020–2026 urban built-up expansion and vegetation loss.

5. **Predictive Demand Forecasting**:
   - Trained `RandomForestRegressor` with recursive 12-month horizon and 95% confidence intervals.
   - Verifiable test metrics (MAE, RMSE, R²) and feature importance bars.

6. **Scenario Simulation Studio**:
   - Empirical elasticity simulation for transit capacity expansion, drainage investments, and population growth.
   - Computes differential deltas with explicit model assumptions.

7. **Evidence-Based Recommendations**:
   - Multi-Criteria Decision Analysis (MCDA) generating transparent, traceable capital intervention proposals with raw data citations.

8. **Grounded AI Planning Assistant**:
   - Conversational assistant with strict anti-hallucination controls that queries live municipal database records before generating grounded answers with executed SQL citations.

9. **Security, RBAC, & Data Governance**:
   - JWT authentication with Role-Based Access Control (`ADMIN`, `PLANNER`, `ANALYST`, `VIEWER`).
   - Immutable security audit logs and data quality scoring.

---

## 🚀 Quick Start Guide

### Option 1: Local Development

#### 1. Backend Setup
```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python requirements
pip install -r requirements.txt

# Ingest and seed real municipal datasets
PYTHONPATH=. python scripts/seed_real_data.py

# Run test suite
PYTHONPATH=. pytest tests/

# Start FastAPI server
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```
API Documentation available at: `http://localhost:8000/api/v1/docs`

#### 2. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```
Frontend Web App available at: `http://localhost:5173`

---

## 🔑 Demo Municipal Credentials

| Role | Email | Password | Scope |
|---|---|---|---|
| **Admin** | `admin@municipal.gov.in` | `Admin@2026#DSS` | Full governance & user management |
| **Town Planner** | `planner@municipal.gov.in` | `Planner@2026#DSS` | Scenarios, recommendations, analytics |
| **Data Analyst** | `analyst@municipal.gov.in` | `Analyst@2026#DSS` | Models, GIS, predictions |
| **Viewer** | `viewer@municipal.gov.in` | `Viewer@2026#DSS` | Read-only municipal views |

*(Note: One-click role login buttons are also available directly on the login screen for rapid evaluation.)*

---

## 📁 Repository Structure

```
.
├── backend/
│   └── app/
│       ├── api/            # FastAPI REST v1 routers
│       ├── core/           # Config, JWT security, structured logging
│       ├── database/       # SQLAlchemy 2.0 session & migrations
│       ├── forecasting/    # Time-series & demand regressor models
│       ├── gis/            # DBSCAN hotspots, spatial joins, remote sensing
│       ├── llm/            # Grounded AI assistant with RAG query tools
│       ├── models/         # SQLAlchemy ORM database models
│       ├── nlp/            # Multilingual cleaning, classifier, NER, embeddings
│       ├── recommendations/# MCDA priority & recommendation engine
│       ├── scenarios/      # Empirical elasticity scenario engine
│       ├── schemas/        # Pydantic request & response schemas
│       └── main.py         # Main FastAPI entrypoint
├── docs/                   # Full architectural & algorithmic documentation
├── frontend/               # React + TypeScript + Vite + Tailwind + Leaflet app
├── models/                 # Serialized model pickles (.pkl)
├── scripts/                # Real dataset seeder & training scripts
├── tests/                  # Pytest test suite (unit, NLP, GIS, API)
├── requirements.txt        # Python backend dependencies
└── README.md
```

