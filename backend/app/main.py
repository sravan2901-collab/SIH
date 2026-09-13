import logging
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded

from app.limiter import limiter
from app.routers import auth, dashboard, products, reports, scans
from app.storage import ensure_buckets

logger = logging.getLogger(__name__)

app = FastAPI(title="LMPC Compliance System API", version="0.1.0")

# Rate limiting stub
app.state.limiter = limiter


async def rate_limit_exceeded_handler(request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={"detail": f"Rate limit exceeded: {exc.detail}"},
    )


app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

# CORS configuration
CORS_ALLOWED_ORIGINS = os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:5173")
allowed_origins = [
    origin.strip()
    for origin in CORS_ALLOWED_ORIGINS.split(",")
    if origin.strip()
]

# NOTE: allow_credentials=False because the API uses Bearer tokens in Authorization headers, not cookies.
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# TLS stub (production would terminate TLS at a reverse proxy in front of the api service)
FORCE_HTTPS = os.getenv("FORCE_HTTPS", "false").lower() in ("true", "1", "yes")
if FORCE_HTTPS:
    from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware

    app.add_middleware(HTTPSRedirectMiddleware)

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
