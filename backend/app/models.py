from uuid import uuid4
from sqlalchemy import (
    Column, String, Text, Float, Boolean, DateTime, Date, Enum, ForeignKey, func
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.database import Base


class User(Base):
    __tablename__ = "users"
    user_id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name            = Column(String(255), nullable=False)
    email           = Column(String(255), unique=True, nullable=False)
    password_hash   = Column(String(255), nullable=False)
    role            = Column(Enum("Inspector","Reviewer","Admin", name="role_enum"), nullable=False)
    region          = Column(String(100))
    created_at      = Column(DateTime, default=func.now())


class Product(Base):
    __tablename__ = "products"
    product_id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name                  = Column(String(255), nullable=False)
    brand                 = Column(String(255))
    manufacturer_name     = Column(String(255))
    manufacturer_address  = Column(Text)
    category              = Column(String(100))
    barcode               = Column(String(100), unique=True)
    created_at            = Column(DateTime, default=func.now())


class Scan(Base):
    __tablename__ = "scans"
    scan_id                 = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    product_id              = Column(UUID(as_uuid=True), ForeignKey("products.product_id"), nullable=False)
    uploaded_by             = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)
    raw_image_path          = Column(Text)
    preprocessed_image_path = Column(Text)
    capture_timestamp       = Column(DateTime)
    status                  = Column(Enum("queued","processing","done","needs_review","error", name="scan_status_enum"), nullable=False, default="queued")


class Declaration(Base):
    __tablename__ = "declarations"
    declaration_id        = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    scan_id               = Column(UUID(as_uuid=True), ForeignKey("scans.scan_id"), nullable=False)
    field_name            = Column(Enum("MRP","net_quantity","mfg_date","manufacturer_address","consumer_care","unit_sale_price","dimensions", name="field_name_enum"), nullable=False)
    extracted_value       = Column(Text)
    bounding_box          = Column(JSONB)
    confidence_score      = Column(Float)
    font_height_mm        = Column(Float)
    language_detected     = Column(String(20))
    is_manually_corrected = Column(Boolean, default=False)


class RuleConfig(Base):
    __tablename__ = "rule_configs"
    rule_id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    field_name            = Column(String(100), nullable=False)
    mandatory             = Column(Boolean, nullable=False)
    regex_pattern         = Column(String(500))
    min_font_height_mm    = Column(Float)
    placement_zone        = Column(String(100))
    language_requirement  = Column(String(50))
    version               = Column(String(20))
    effective_date        = Column(Date)


class Violation(Base):
    __tablename__ = "violations"
    violation_id   = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    scan_id        = Column(UUID(as_uuid=True), ForeignKey("scans.scan_id"), nullable=False)
    declaration_id = Column(UUID(as_uuid=True), ForeignKey("declarations.declaration_id"), nullable=True)
    rule_id        = Column(UUID(as_uuid=True), ForeignKey("rule_configs.rule_id"), nullable=False)
    category       = Column(Enum("missing","format","font","placement","misleading","language", name="violation_category_enum"), nullable=False)
    severity       = Column(Enum("critical","minor", name="severity_enum"), nullable=False)
    description    = Column(Text)


class InspectionReport(Base):
    __tablename__ = "inspection_reports"
    report_id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    scan_id            = Column(UUID(as_uuid=True), ForeignKey("scans.scan_id"), nullable=False, unique=True)
    generated_by       = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)
    reviewed_by        = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=True)
    compliance_status  = Column(Enum("compliant","non_compliant","needs_review", name="compliance_enum"))
    pdf_path           = Column(Text)
    docx_path          = Column(Text)
    remarks            = Column(Text)
    status             = Column(Enum("draft","submitted","approved","sent_back","escalated", name="report_status_enum"), nullable=False, default="draft")
    created_at         = Column(DateTime, default=func.now())
    finalized_at       = Column(DateTime, nullable=True)
