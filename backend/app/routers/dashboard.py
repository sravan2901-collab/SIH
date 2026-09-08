from fastapi import APIRouter

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/health")
async def health():
    return {"status": "ok", "service": "dashboard"}
