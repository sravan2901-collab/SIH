from fastapi import APIRouter

router = APIRouter(prefix="/scans", tags=["scans"])


@router.get("/health")
async def health():
    return {"status": "ok", "service": "scans"}
