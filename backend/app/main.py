import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import auth, dashboard, products, reports, scans
from app.storage import ensure_buckets

logger = logging.getLogger(__name__)

app = FastAPI(title="LMPC Compliance System API", version="0.1.0")

# Permissive CORS settings for local development.
# NOTE: Must be tightened with specific allowed origins before production deployment.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(products.router)
app.include_router(scans.router)
app.include_router(reports.router)
app.include_router(dashboard.router)


@app.on_event("startup")
async def startup_event():
    try:
        ensure_buckets()
    except Exception as exc:
        logger.warning("MinIO bucket initialization failed on startup: %s", exc)


@app.get("/")
async def root():
    return {"message": "LMPC Compliance System API", "status": "running"}
