import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.app.api.v1 import (
    analytics, assistant, audit, auth, citizen_requests, data_sources, gis, models, nlp, predictions, recommendations,
    scenarios, wards,
)
from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.database.session import init_db


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=("Decision support for Greater Mumbai: multilingual grievance NLP, OSM/Census/Sentinel-2 GIS analytics, "
                 "infrastructure gap benchmarking, demand forecasting, scenario evaluation, MCDA recommendations and an "
                 "LLM assistant grounded in the municipal database."),
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    logger.info(f"METHOD={request.method} PATH={request.url.path} STATUS={response.status_code} "
                f"DURATION={(time.time() - start) * 1000:.1f}ms")
    return response


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception(f"Unhandled error on {request.method} {request.url.path}")
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "HEALTHY", "service": settings.PROJECT_NAME, "version": settings.VERSION, "timestamp": time.time()}


p = settings.API_V1_STR
app.include_router(auth.router, prefix=f"{p}/auth", tags=["Authentication & RBAC"])
app.include_router(wards.router, prefix=f"{p}/wards", tags=["Wards"])
app.include_router(citizen_requests.router, prefix=f"{p}/citizen-requests", tags=["Citizen Feedback"])
app.include_router(nlp.router, prefix=f"{p}/nlp", tags=["NLP & Documents"])
app.include_router(gis.router, prefix=f"{p}/gis", tags=["GIS"])
app.include_router(gis.public_router, prefix=f"{p}/gis", tags=["GIS"])
app.include_router(analytics.router, prefix=f"{p}/analytics", tags=["Analytics"])
app.include_router(predictions.router, prefix=f"{p}/predictions", tags=["Forecasting"])
app.include_router(scenarios.router, prefix=f"{p}/scenarios", tags=["Scenarios"])
app.include_router(recommendations.router, prefix=f"{p}/recommendations", tags=["Recommendations"])
app.include_router(assistant.router, prefix=f"{p}/assistant", tags=["AI Assistant"])
app.include_router(data_sources.router, prefix=f"{p}/data-sources", tags=["Data Governance"])
app.include_router(models.router, prefix=f"{p}/models", tags=["Model Registry"])
app.include_router(audit.router, prefix=f"{p}/audit", tags=["Audit"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host="127.0.0.1", port=8000, reload=True)
