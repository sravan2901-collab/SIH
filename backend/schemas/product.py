"""Pydantic v2 request/response schemas for the Product resource."""
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ProductCreate(BaseModel):
    name: str
    brand: str | None = None
    manufacturer_name: str | None = None
    manufacturer_address: str | None = None
    category: str | None = None
    barcode: str | None = None


class ProductRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    product_id: uuid.UUID
    name: str
    brand: str | None = None
    manufacturer_name: str | None = None
    manufacturer_address: str | None = None
    category: str | None = None
    barcode: str | None = None
    created_at: datetime
