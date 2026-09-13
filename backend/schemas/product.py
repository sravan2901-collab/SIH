"""Pydantic v2 request/response schemas for the Product resource."""
import uuid
from typing import Any
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ProductCreate(BaseModel):
    name: str = Field(..., min_length=1)
    brand: str | None = None
    manufacturer_name: str | None = None
    manufacturer_address: str | None = None
    category: str | None = None
    barcode: str | None = None

    @field_validator("name", mode="before")
    @classmethod
    def strip_and_validate_name(cls, v: Any) -> Any:
        if isinstance(v, str):
            v = v.strip()
            if not v:
                raise ValueError("Name cannot be empty or whitespace")
        return v


class ProductUpdate(BaseModel):
    name: str | None = None
    brand: str | None = None
    manufacturer_name: str | None = None
    manufacturer_address: str | None = None
    category: str | None = None
    barcode: str | None = None

    @field_validator("name", mode="before")
    @classmethod
    def strip_and_validate_name(cls, v: Any) -> Any:
        if isinstance(v, str):
            v = v.strip()
            if not v:
                raise ValueError("Name cannot be empty or whitespace")
        return v


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
