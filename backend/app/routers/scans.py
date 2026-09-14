from datetime import datetime
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, require_inspector
from app.database import get_db
from app.models import Declaration, Product, Scan, User
from app.storage import ensure_buckets, s3_client
from app.tasks import (
    check_font,
    classify_fields,
    generate_report,
    preprocess,
    run_ocr,
    validate_rules,
)
from schemas.scan import DeclarationRead, ScanRead, ScanStatusRead

router = APIRouter(prefix="/scans", tags=["scans"])

MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/jpg", "image/png"}
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png"}


@router.get("/health")
async def health():
    return {"status": "ok", "service": "scans"}


@router.post("/upload", response_model=ScanRead, status_code=status.HTTP_201_CREATED)
async def upload_scan(
    product_id: UUID = Form(...),
    file: UploadFile = File(...),
    current_user: User = Depends(require_inspector),
    db: AsyncSession = Depends(get_db),
):
    """Upload a packaged commodity label image and enqueue processing chain."""
    # Verify product exists
    product = await db.get(Product, product_id)
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product '{product_id}' not found",
        )

    # Validate file format
    filename = (file.filename or "").lower()
    has_valid_ext = any(filename.endswith(ext) for ext in ALLOWED_EXTENSIONS)
    has_valid_type = file.content_type in ALLOWED_CONTENT_TYPES

    if not (has_valid_ext or has_valid_type):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file type. Only JPEG and PNG images are allowed.",
        )

    ext = "png" if (filename.endswith(".png") or file.content_type == "image/png") else "jpg"

    content = await file.read()
    if len(content) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size exceeds maximum allowed limit of {MAX_FILE_SIZE // (1024 * 1024)}MB.",
        )

    scan_id = uuid4()
    s3_key = f"{scan_id}/original.{ext}"
    raw_image_path = f"raw-images/{s3_key}"

    # Upload raw image to MinIO
    ensure_buckets()
    try:
        s3_client.put_object(
            Bucket="raw-images",
            Key=s3_key,
            Body=content,
            ContentType=file.content_type or f"image/{ext}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to store uploaded image in storage: {e}",
        )

    # Insert Scan record with status="queued" and preprocessed_image_path=null
    scan = Scan(
        scan_id=scan_id,
        product_id=product_id,
        uploaded_by=current_user.user_id,
        raw_image_path=raw_image_path,
        preprocessed_image_path=None,
        capture_timestamp=datetime.utcnow(),
        status="queued",
    )
    db.add(scan)
    await db.commit()
    await db.refresh(scan)

    scan_read = ScanRead.model_validate(scan)

    # Enqueue async Celery chain
    chain = (
        preprocess.s(str(scan_id))
        | run_ocr.s()
        | classify_fields.s()
        | check_font.s()
        | validate_rules.s()
        | generate_report.s()
    )
    chain.apply_async()

    return scan_read


@router.get("/{scan_id}/status", response_model=ScanStatusRead)
async def get_scan_status(
    scan_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve scan processing status."""
    scan = await db.get(Scan, scan_id)
    if scan is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scan not found",
        )
    return ScanStatusRead(scan_id=scan.scan_id, status=scan.status)


@router.get("/{scan_id}/declarations", response_model=list[DeclarationRead])
async def get_scan_declarations(
    scan_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve declarations extracted for a scan."""
    scan = await db.get(Scan, scan_id)
    if scan is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scan not found",
        )
    result = await db.execute(
        select(Declaration).where(Declaration.scan_id == scan_id)
    )
    declarations = result.scalars().all()
    return [DeclarationRead.model_validate(d) for d in declarations]

