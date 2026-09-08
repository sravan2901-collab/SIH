from fastapi import APIRouter

router = APIRouter(prefix="/products", tags=["products"])


@router.get("/health")
async def health():
    return {"status": "ok", "service": "products"}
