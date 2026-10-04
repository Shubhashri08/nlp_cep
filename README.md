# Urban Planning Decision Support System — Greater Mumbai

An AI-driven decision support system for municipal planners. It brings together citizen feedback, planning documents, Census demographics, OpenStreetMap infrastructure and land use, Sentinel-2 remote sensing and elevation data. On top of these it runs NLP, machine learning, forecasting, scenario evaluation and an LLM assistant grounded in the database.

**Stack:** FastAPI · SQLAlchemy (SQLite) · scikit-learn · shapely / rasterio · OpenAI or Gemini (optional) · React + TypeScript + Vite + Tailwind + Leaflet + Recharts

---

## What the system does

| Problem-statement capability | Implementation |
|---|---|
| **Classify & summarise planning information** | Multi-label grievance classifier (TF-IDF word + char n-grams → One-vs-Rest logistic regression, 17 sectors, English / Hinglish / Hindi / Marathi) evaluated on a held-out split **and** a hand-written gold set. TextRank extractive summaries; abstractive LLM summaries when a provider is configured. |
| **Named Entity Recognition** | Hybrid NER: longest-match gazetteer of ~3,900 OpenStreetMap places, roads, stations and landmarks in Greater Mumbai, plus tight patterns for ward references and unseen road names, plus lexicons for infrastructure, incidents, time expressions and organisations. |
| **Urban development reports** | PDF/TXT upload → section segmentation → sector classification per section → summary → entities → wards linked to the map. |
| **Urban growth patterns** | Sentinel-2 L2A dry-season median composites for 2019 / 2022 / 2026 (12 scenes each, SCL cloud mask, PIF radiometric normalisation) → NDVI / NDBI / NDWI → built-up, vegetation and water per ward → growth classes (rapid expansion, densifying, greening, stable). |
| **Infrastructure gaps** | Norm-based requirements (CPHEEO 135 lpcd water, MoHUA 0.45 kg/capita waste, URDPFI health / school / open-space norms, BRIMSTOWAD 50 mm/h drainage) against OSM facilities, Sentinel land cover and Copernicus DEM exposure. Seven sectors × 24 wards. |
| **Predict future demand** | Gradient-boosting panel forecasters per metric (complaints, water, waste, transit), back-tested against a seasonal-naive baseline, with widening 95 % intervals. Norm-based infrastructure needs for 2031 / 2036 / 2041 from Census projections. |
| **Evaluate planning scenarios** | Ten levers (transit, bus stops, drainage upgrade, growth, rezoning, water, waste, clinics, schools, green cover). Each uses a cited elasticity or norm. Baseline comes from the database for any ward scope. 8-criterion adequacy score, capital cost, cost-effectiveness and side-by-side comparison. |
| **Actionable recommendations** | Ward priority (MCDA over 5 criteria) plus scored interventions for every critical or high gap, each with its factors, supporting evidence, indicative cost, approval workflow and an optional LLM brief. |
| **Dashboards with geospatial visualisation** | Leaflet GIS explorer: 13 choropleths (priority, density, flood, land use, transit, PM2.5, elevation, growth …), DBSCAN hotspots, complaint points, OSM assets, Sentinel NDVI and new-built-up overlays, and a ward drawer with profile tabs. |
| **LLM** | OpenAI or Gemini with function calling over 10 read-only database tools. Evidence citations (tables, record IDs, the SQL actually executed) come from the tool calls, never from the model's text. Without a key, a deterministic rule-based engine uses the same tools. |

### Data provenance — what is real and what is not

| Data | Source | Status |
|---|---|---|
| 24 BMC ward boundaries | OpenStreetMap (admin_level 10) | **Real** |
| Population, households, literacy, workers, SC/ST, sex ratio | Census of India 2011 PCA (ORGI via OpenCity), aggregated from census wards to BMC wards. Total 12,442,373 = official. | **Real** (2026 figure projected) |
| Hospitals, clinics, schools, bus stops, stations, parks … (~5,200) | OpenStreetMap | **Real** (OSM coverage incomplete; flagged) |
| Road km by class, building counts, land-use shares | OpenStreetMap (Overpass) | **Real** |
| NDVI / NDBI / NDWI, built-up / vegetation / water area | Copernicus Sentinel-2 L2A (Planetary Computer) | **Real** |
| Elevation, low-lying share | Copernicus DEM GLO-30 | **Real** |
| Citizen complaints (~3,200 over 36 months) | `scripts/synthetic.py` | **Synthetic**. Texts are generated, but locations use real OSM places and category rates follow real ward attributes. |
| Monthly water / waste / ridership series, ward supply levels | `scripts/synthetic.py` (Census population × norms / CMP trip rates) | **Synthetic** |
| Monthly rainfall / PM2.5 | IMD climatology and typical seasonality | **Synthetic** |

Every record carries a provenance tag that is shown in the UI. Real data can be loaded through **Data Sources → Import** (CSV / GeoJSON).

---

## Quick start

### 1. Backend

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate      macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt          # add -r requirements-rs.txt to (re)build Sentinel/DEM data
cp .env.example .env                     # optional: set LLM_PROVIDER + API key
python -m scripts.seed --reset           # builds backend/data/urban_planning.db (~2 min)
python -m pytest                         # 46 tests, isolated temp DB
uvicorn backend.app.main:app --reload --port 8000
```

API docs: http://localhost:8000/api/v1/docs

The processed open-data snapshots are committed in `backend/data/external/`, so seeding works offline. To refresh them from the live sources (needs internet; Sentinel takes about 10 minutes):

```bash
pip install -r requirements-rs.txt
python -m scripts.ingest.fetch_all --refresh
```

### 2. Frontend

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173  (proxies /api to :8000)
npm run build      # type-check + production build
```

With `DEMO_MODE=true`, the login page offers one-click role logins. Otherwise use the seeded accounts (`admin@`, `planner@`, `analyst@`, `viewer@municipal.gov.in`) with `DEMO_PASSWORD`, or the random password the seed prints.

### Roles

| Role | Can |
|---|---|
| VIEWER | Read dashboards, maps, analytics, assistant |
| ANALYST | + analyse documents, import data, retrain forecasters, recompute growth / gaps |
| PLANNER | + create / compare scenarios, approve recommendations, update complaint status |
| ADMIN | everything + users and audit trail |

---

## Repository layout

```
backend/app/
  api/v1/          REST routers (auth, wards, citizen-requests, nlp, gis, analytics, predictions, scenarios,
                   recommendations, assistant, data-sources, models, audit)
  analytics/       planning norms, growth classification, population projection
  forecasting/     gradient-boosting panel forecaster
  gis/             spatial ops, DBSCAN hotspots, gap analysis, spectral indices
  llm/             provider abstraction (OpenAI / Gemini), read-only tools, grounded assistant
  nlp/             lexicon, corpus, cleaner, classifier, gazetteer, NER, geocoder, embeddings, summariser, documents
  recommendations/ MCDA priority + intervention engine
  scenarios/       lever simulation + multi-criteria scoring
  services/        DB-backed analytics shared by the API and seed
backend/data/external/   processed open-data snapshots (OSM, Census, Sentinel-2, DEM)
scripts/ingest/          fetchers: OSM boundaries & features, Census, Sentinel-2, DEM
scripts/seed.py          builds the database and trains all models
scripts/synthetic.py     clearly labelled demonstration data generators
frontend/src/            React app (pages, GIS components, typed API client, theme tokens)
docs/                    architecture, data, NLP, GIS, forecasting, deployment notes
tests/                   pytest suite (NLP, GIS, forecasting / scenarios, API + RBAC + LLM tool loop)
```

Data attribution: © OpenStreetMap contributors (ODbL) · Census of India 2011 · contains modified Copernicus Sentinel data (2019–2026) · Copernicus DEM © DLR/Airbus.
