from fastapi import APIRouter

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/health")
async def health():
    return {"status": "ok", "service": "reports"}
