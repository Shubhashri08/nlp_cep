from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import time

from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.api.v1 import (
    auth, wards, citizen_requests, nlp, gis, analytics,
    predictions, scenarios, recommendations, assistant,
    data_sources, models, audit
)

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=(
        "Production-grade AI-Driven Urban Planning Decision Support System. "
        "Provides Multilingual NLP for Citizen Grievances, PostGIS / Spatial Hotspot Analysis, "
        "Infrastructure Gap Benchmarking, Satellite Remote Sensing, Time-Series Demand Forecasting, "
        "Scenario Simulation, Explainable Recommendations, and Grounded AI Assistant."
    ),
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows local dev and container origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Middleware for request logging & timing
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = (time.time() - start_time) * 1000
    logger.info(
        f"METHOD={request.method} PATH={request.url.path} STATUS={response.status_code} DURATION={process_time:.2f}ms"
    )
    return response

# Root Health Check
@app.get("/health", tags=["Health"])
def health_check():
    return {
        "status": "HEALTHY",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "timestamp": time.time()
    }

# Register API v1 Routers
api_prefix = settings.API_V1_STR
app.include_router(auth.router, prefix=f"{api_prefix}/auth", tags=["Authentication & RBAC"])
app.include_router(wards.router, prefix=f"{api_prefix}/wards", tags=["Municipal Wards & Zones"])
app.include_router(citizen_requests.router, prefix=f"{api_prefix}/citizen-requests", tags=["Citizen Feedback & Semantic Search"])
app.include_router(nlp.router, prefix=f"{api_prefix}/nlp", tags=["Multilingual NLP Pipeline"])
app.include_router(gis.router, prefix=f"{api_prefix}/gis", tags=["Interactive GIS & Hotspots"])
app.include_router(analytics.router, prefix=f"{api_prefix}/analytics", tags=["Dashboard & Gap Analytics"])
app.include_router(predictions.router, prefix=f"{api_prefix}/predictions", tags=["Demand Forecasting & ML"])
app.include_router(scenarios.router, prefix=f"{api_prefix}/scenarios", tags=["Scenario Simulation Studio"])
app.include_router(recommendations.router, prefix=f"{api_prefix}/recommendations", tags=["Explainable Recommendations & Priority Map"])
app.include_router(assistant.router, prefix=f"{api_prefix}/assistant", tags=["Grounded AI Planning Assistant"])
app.include_router(data_sources.router, prefix=f"{api_prefix}/data-sources", tags=["Data Provenance & Quality Monitor"])
app.include_router(models.router, prefix=f"{api_prefix}/models", tags=["Model Registry & Evaluation"])
app.include_router(audit.router, prefix=f"{api_prefix}/audit", tags=["Audit Trail"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=True)
