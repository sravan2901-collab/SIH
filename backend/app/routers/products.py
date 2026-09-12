"""Products router: catalog search, creation, retrieval, and partial updates."""
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import (
    get_current_user,
    require_inspector,
    require_inspector_or_admin,
)
from app.database import get_db
from app.models import Product, User
from schemas.product import ProductCreate, ProductRead, ProductUpdate

router = APIRouter(prefix="/products", tags=["products"])


@router.get("/health")
async def health():
    return {"status": "ok", "service": "products"}


@router.get("", response_model=list[ProductRead])
async def search_products(
    q: str = Query(..., min_length=1, description="Full-text search term"),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Full-text search across name, brand, and barcode."""
    search_document = func.to_tsvector(
        "english",
        func.concat_ws(
            " ",
            Product.name,
            Product.brand,
            Product.barcode,
        ),
    )
    search_query = func.plainto_tsquery("english", q)

    stmt = select(Product).where(search_document.op("@@")(search_query)).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("", response_model=ProductRead, status_code=status.HTTP_201_CREATED)
async def create_product(
    payload: ProductCreate,
    _inspector: User = Depends(require_inspector),
    db: AsyncSession = Depends(get_db),
):
    if payload.barcode is not None:
        existing = await db.execute(
            select(Product).where(Product.barcode == payload.barcode)
        )
        if existing.scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A product with this barcode already exists",
            )

    new_product = Product(**payload.model_dump())
    db.add(new_product)
    await db.commit()
    await db.refresh(new_product)
    return new_product


@router.get("/{product_id}", response_model=ProductRead)
async def get_product(
    product_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Product).where(Product.product_id == product_id))
    product = result.scalar_one_or_none()
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Product not found"
        )
    return product


@router.patch("/{product_id}", response_model=ProductRead)
async def update_product(
    product_id: uuid.UUID,
    payload: ProductUpdate,
    _user: User = Depends(require_inspector_or_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Product).where(Product.product_id == product_id))
    product = result.scalar_one_or_none()
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Product not found"
        )

    update_fields = payload.model_dump(exclude_unset=True)

    new_barcode = update_fields.get("barcode")
    if "barcode" in update_fields and new_barcode is not None:
        existing = await db.execute(
            select(Product).where(
                Product.barcode == new_barcode,
                Product.product_id != product_id,
            )
        )
        if existing.scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A product with this barcode already exists",
            )

    for field, value in update_fields.items():
        setattr(product, field, value)

    await db.commit()
    await db.refresh(product)
    return product

