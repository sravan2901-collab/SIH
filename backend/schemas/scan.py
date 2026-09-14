"""Pydantic v2 request/response schemas for the Scan resource."""
import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class ScanCreate(BaseModel):
    product_id: uuid.UUID


class ScanRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    scan_id: uuid.UUID
    product_id: uuid.UUID
    uploaded_by: uuid.UUID
    raw_image_path: str | None = None
    preprocessed_image_path: str | None = None
    capture_timestamp: datetime | None = None
    status: str


class ScanStatusRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    scan_id: uuid.UUID
    status: str


class DeclarationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    declaration_id: uuid.UUID
    scan_id: uuid.UUID
    field_name: str
    extracted_value: str | None = None
    bounding_box: Any | None = None
    confidence_score: float | None = None
    font_height_mm: float | None = None
    language_detected: str | None = None
    is_manually_corrected: bool = False
