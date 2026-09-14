"""Integration tests for the /scans endpoints and image upload processing pipeline.

Covers:
- POST /scans/upload (Inspector-only, image validation, 20MB limit, MinIO storage, Celery chain)
- GET /scans/{scan_id}/status (any authenticated role)
- GET /scans/{scan_id}/declarations (any authenticated role)
"""
import asyncio
import io
import uuid

from pathlib import Path
import sys

import asyncpg
from botocore.exceptions import ClientError
import cv2
import numpy as np
from PIL import Image, ImageDraw
import pytest

from app.celery_app import celery_app
from app.database import DATABASE_URL
from app.storage import ensure_buckets, s3_client

repo_root = Path(__file__).resolve().parent.parent.parent
ml_pipeline_dir = repo_root / "ml-pipeline"
if str(ml_pipeline_dir) not in sys.path:
    sys.path.insert(0, str(ml_pipeline_dir))

from tasks.image_processing import _compute_skew_angle  # noqa: E402

ADMIN_EMAIL = "admin@lmpc.gov"
ADMIN_PASSWORD = "ChangeMe_Dev_Only!123"

pytestmark = pytest.mark.integration


# Minimal valid 1x1 JPEG byte stream
TINY_JPEG = (
    b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
    b"\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c"
    b"\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c"
    b"\x1c $.' \",#\x1c\x1c(7),01444\x1f'9=82<.342\xff\xc0\x00\x0b\x08\x00\x01"
    b"\x00\x01\x01\x01\x11\x00\xff\xc4\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01"
    b"\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08"
    b"\t\n\x0b\xff\xda\x00\x08\x01\x01\x00\x00?\x00\xbf\x00\xff\xd9"
)

# Minimal valid PNG byte stream
_, _tiny_png_buf = cv2.imencode(".png", np.full((10, 10, 3), 255, dtype=np.uint8))
TINY_PNG = _tiny_png_buf.tobytes()


async def _delete_user_by_email(email: str) -> None:
    conn = await asyncpg.connect(dsn=DATABASE_URL.replace("+asyncpg", ""))
    try:
        user_row = await conn.fetchrow("SELECT user_id FROM users WHERE email = $1", email)
        if user_row:
            user_id = user_row["user_id"]
            await conn.execute("DELETE FROM scans WHERE uploaded_by = $1", user_id)
            await conn.execute("DELETE FROM users WHERE user_id = $1", user_id)
    finally:
        await conn.close()


async def _delete_product_by_id(product_id: uuid.UUID) -> None:
    conn = await asyncpg.connect(dsn=DATABASE_URL.replace("+asyncpg", ""))
    try:
        await conn.execute("DELETE FROM scans WHERE product_id = $1", product_id)
        await conn.execute("DELETE FROM products WHERE product_id = $1", product_id)
    finally:
        await conn.close()



async def _delete_scan_by_id(scan_id: uuid.UUID) -> None:
    conn = await asyncpg.connect(dsn=DATABASE_URL.replace("+asyncpg", ""))
    try:
        await conn.execute("DELETE FROM scans WHERE scan_id = $1", scan_id)
    finally:
        await conn.close()


@pytest.fixture(scope="module")
def admin_token(client):
    resp = client.post(
        "/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    )
    assert resp.status_code == 200
    return resp.json()["access_token"]


@pytest.fixture
def inspector_auth(client, admin_token):
    email = f"pytest.scan.insp.{uuid.uuid4().hex[:8]}@lmpc.gov"
    reg = client.post(
        "/auth/register",
        json={
            "name": "Scan Test Inspector",
            "email": email,
            "password": "TempPassword123!",
            "role": "Inspector",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert reg.status_code == 201
    user_id = uuid.UUID(reg.json()["user_id"])

    login = client.post(
        "/auth/login", json={"email": email, "password": "TempPassword123!"}
    )
    assert login.status_code == 200
    token = login.json()["access_token"]

    yield {"token": token, "user_id": user_id, "email": email}

    asyncio.run(_delete_user_by_email(email))


@pytest.fixture
def reviewer_token(client, admin_token):
    email = f"pytest.scan.rev.{uuid.uuid4().hex[:8]}@lmpc.gov"
    reg = client.post(
        "/auth/register",
        json={
            "name": "Scan Test Reviewer",
            "email": email,
            "password": "TempPassword123!",
            "role": "Reviewer",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert reg.status_code == 201

    login = client.post(
        "/auth/login", json={"email": email, "password": "TempPassword123!"}
    )
    assert login.status_code == 200
    token = login.json()["access_token"]

    yield token

    asyncio.run(_delete_user_by_email(email))


@pytest.fixture
def test_product(client, inspector_auth):
    barcode = f"890{uuid.uuid4().int % 10000000000:010d}"
    resp = client.post(
        "/products",
        json={
            "name": "Scan Test Product",
            "brand": "TestBrand",
            "barcode": barcode,
            "category": "Packaged Food",
        },
        headers={"Authorization": f"Bearer {inspector_auth['token']}"},
    )
    assert resp.status_code == 201
    product_id = uuid.UUID(resp.json()["product_id"])

    yield product_id

    asyncio.run(_delete_product_by_id(product_id))


@pytest.fixture(autouse=True)
def configure_celery_eager(monkeypatch):
    """Enable synchronous task execution for Celery chain tests."""
    monkeypatch.setattr(celery_app.conf, "task_always_eager", True)
    monkeypatch.setattr(celery_app.conf, "task_eager_propagates", True)


def test_upload_scan_success_and_chain_execution(client, inspector_auth, test_product):
    """Upload a small JPEG fixture, assert MinIO raw-images contains key,

    assert initial ScanRead status is queued, preprocessed_image_path is null,
    and assert Celery chain executes synchronously with task_always_eager=True.
    """
    ensure_buckets()

    resp = client.post(
        "/scans/upload",
        data={"product_id": str(test_product)},
        files={"file": ("label.jpg", io.BytesIO(TINY_JPEG), "image/jpeg")},
        headers={"Authorization": f"Bearer {inspector_auth['token']}"},
    )
    assert resp.status_code == 201
    data = resp.json()

    scan_id_str = data["scan_id"]
    scan_id = uuid.UUID(scan_id_str)

    # Initial ScanRead response contract assertions
    assert data["status"] == "queued"
    assert data["product_id"] == str(test_product)
    assert data["uploaded_by"] == str(inspector_auth["user_id"])
    assert data["raw_image_path"] == f"raw-images/{scan_id_str}/original.jpg"
    assert data["preprocessed_image_path"] is None

    # Verify MinIO bucket raw-images contains {scan_id}/original.jpg
    expected_s3_key = f"{scan_id_str}/original.jpg"
    s3_obj = s3_client.get_object(Bucket="raw-images", Key=expected_s3_key)
    stored_bytes = s3_obj["Body"].read()
    assert stored_bytes == TINY_JPEG

    # Verify PostgreSQL row
    async def _check_db():
        conn = await asyncpg.connect(dsn=DATABASE_URL.replace("+asyncpg", ""))
        try:
            row = await conn.fetchrow(
                "SELECT * FROM scans WHERE scan_id = $1", scan_id
            )
            return dict(row) if row else None
        finally:
            await conn.close()

    db_scan = asyncio.run(_check_db())
    assert db_scan is not None
    assert db_scan["product_id"] == test_product
    assert db_scan["uploaded_by"] == inspector_auth["user_id"]
    assert db_scan["raw_image_path"] == f"raw-images/{scan_id_str}/original.jpg"
    assert db_scan["preprocessed_image_path"] == f"preprocessed-images/{scan_id_str}/preprocessed.png"
    # Verify PostgreSQL row: by the time the eager Celery chain returns,
    # the stub tasks have updated the Scan row status in Postgres to "processing"
    assert db_scan["status"] == "processing"

    # Clean up MinIO and database
    try:
        s3_client.delete_object(Bucket="raw-images", Key=expected_s3_key)
    except ClientError:
        pass
    try:
        s3_client.delete_object(Bucket="preprocessed-images", Key=f"{scan_id_str}/preprocessed.png")
    except ClientError:
        pass
    asyncio.run(_delete_scan_by_id(scan_id))


def test_upload_scan_png_supported(client, inspector_auth, test_product):
    """Verify PNG upload sets original.png key and executes chain."""
    resp = client.post(
        "/scans/upload",
        data={"product_id": str(test_product)},
        files={"file": ("label.png", io.BytesIO(TINY_PNG), "image/png")},
        headers={"Authorization": f"Bearer {inspector_auth['token']}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    scan_id = uuid.UUID(data["scan_id"])
    assert data["raw_image_path"] == f"raw-images/{data['scan_id']}/original.png"

    # Cleanup
    try:
        s3_client.delete_object(Bucket="raw-images", Key=f"{data['scan_id']}/original.png")
    except ClientError:
        pass
    try:
        s3_client.delete_object(Bucket="preprocessed-images", Key=f"{data['scan_id']}/preprocessed.png")
    except ClientError:
        pass
    asyncio.run(_delete_scan_by_id(scan_id))


def test_upload_scan_unauthenticated_returns_401(client, test_product):
    resp = client.post(
        "/scans/upload",
        data={"product_id": str(test_product)},
        files={"file": ("label.jpg", io.BytesIO(TINY_JPEG), "image/jpeg")},
    )
    assert resp.status_code == 401


def test_upload_scan_reviewer_forbidden_returns_403(client, reviewer_token, test_product):
    resp = client.post(
        "/scans/upload",
        data={"product_id": str(test_product)},
        files={"file": ("label.jpg", io.BytesIO(TINY_JPEG), "image/jpeg")},
        headers={"Authorization": f"Bearer {reviewer_token}"},
    )
    assert resp.status_code == 403
    assert resp.json()["detail"] == "Inspector role required"


def test_upload_scan_rejects_non_image_file(client, inspector_auth, test_product):
    resp = client.post(
        "/scans/upload",
        data={"product_id": str(test_product)},
        files={"file": ("notes.txt", io.BytesIO(b"Hello world"), "text/plain")},
        headers={"Authorization": f"Bearer {inspector_auth['token']}"},
    )
    assert resp.status_code == 400
    assert "Invalid file type" in resp.json()["detail"]


def test_upload_scan_rejects_empty_file(client, inspector_auth, test_product):
    resp = client.post(
        "/scans/upload",
        data={"product_id": str(test_product)},
        files={"file": ("empty.jpg", io.BytesIO(b""), "image/jpeg")},
        headers={"Authorization": f"Bearer {inspector_auth['token']}"},
    )
    assert resp.status_code == 400
    assert "empty" in resp.json()["detail"].lower()


def test_upload_scan_rejects_oversized_file(client, inspector_auth, test_product):
    oversized = b"x" * (20 * 1024 * 1024 + 1)
    resp = client.post(
        "/scans/upload",
        data={"product_id": str(test_product)},
        files={"file": ("large.jpg", io.BytesIO(oversized), "image/jpeg")},
        headers={"Authorization": f"Bearer {inspector_auth['token']}"},
    )
    assert resp.status_code == 413
    assert "maximum allowed limit" in resp.json()["detail"].lower()


def test_upload_scan_nonexistent_product_returns_404(client, inspector_auth):
    fake_id = uuid.uuid4()
    resp = client.post(
        "/scans/upload",
        data={"product_id": str(fake_id)},
        files={"file": ("label.jpg", io.BytesIO(TINY_JPEG), "image/jpeg")},
        headers={"Authorization": f"Bearer {inspector_auth['token']}"},
    )
    assert resp.status_code == 404
    assert f"Product '{fake_id}' not found" in resp.json()["detail"]


def test_get_scan_status_and_declarations(client, inspector_auth, test_product):
    """Verify GET /scans/{scan_id}/status and GET /scans/{scan_id}/declarations."""
    resp = client.post(
        "/scans/upload",
        data={"product_id": str(test_product)},
        files={"file": ("label.jpg", io.BytesIO(TINY_JPEG), "image/jpeg")},
        headers={"Authorization": f"Bearer {inspector_auth['token']}"},
    )
    assert resp.status_code == 201
    scan_id = uuid.UUID(resp.json()["scan_id"])

    # GET status
    status_resp = client.get(
        f"/scans/{scan_id}/status",
        headers={"Authorization": f"Bearer {inspector_auth['token']}"},
    )
    assert status_resp.status_code == 200
    status_data = status_resp.json()
    assert status_data["scan_id"] == str(scan_id)
    assert status_data["status"] in ("queued", "processing")

    # GET declarations (empty array expected in Phase 3)
    decl_resp = client.get(
        f"/scans/{scan_id}/declarations",
        headers={"Authorization": f"Bearer {inspector_auth['token']}"},
    )
    assert decl_resp.status_code == 200
    assert decl_resp.json() == []

    # Non-existent scan returns 404
    non_existent = uuid.uuid4()
    assert (
        client.get(
            f"/scans/{non_existent}/status",
            headers={"Authorization": f"Bearer {inspector_auth['token']}"},
        ).status_code
        == 404
    )
    assert (
        client.get(
            f"/scans/{non_existent}/declarations",
            headers={"Authorization": f"Bearer {inspector_auth['token']}"},
        ).status_code
        == 404
    )

    # Cleanup
    try:
        s3_client.delete_object(Bucket="raw-images", Key=f"{scan_id}/original.jpg")
    except ClientError:
        pass
    try:
        s3_client.delete_object(Bucket="preprocessed-images", Key=f"{scan_id}/preprocessed.png")
    except ClientError:
        pass
    asyncio.run(_delete_scan_by_id(scan_id))


def test_preprocess_e2e_skewed_image(client, inspector_auth, test_product):
    """E2E test: upload synthetic skewed (+8 deg) JPEG image.

    Verify Celery preprocess task:
    1. Populates Scan.preprocessed_image_path in DB to 'preprocessed-images/{scan_id}/preprocessed.png'.
    2. Stores output PNG in MinIO preprocessed-images bucket with size > 0.
    3. Output image quality: deskews image so remaining skew is < 0.5 degrees.
    4. Downstream stubs execute without failure.
    """
    ensure_buckets()

    # Synthesize test image with deliberate +8 degree skew
    canvas = Image.new("RGB", (600, 600), color=(255, 255, 255))
    draw = ImageDraw.Draw(canvas)
    draw.rectangle([150, 200, 450, 400], fill=(0, 0, 0))
    rotated = canvas.rotate(8.0, expand=False, fillcolor=(255, 255, 255))

    buf = io.BytesIO()
    rotated.save(buf, format="JPEG", dpi=(72, 72))
    skewed_jpeg_bytes = buf.getvalue()

    resp = client.post(
        "/scans/upload",
        data={"product_id": str(test_product)},
        files={"file": ("skewed_label.jpg", io.BytesIO(skewed_jpeg_bytes), "image/jpeg")},
        headers={"Authorization": f"Bearer {inspector_auth['token']}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    scan_id_str = data["scan_id"]
    scan_id = uuid.UUID(scan_id_str)

    expected_raw_key = f"{scan_id_str}/original.jpg"
    expected_prep_key = f"{scan_id_str}/preprocessed.png"
    expected_prep_path = f"preprocessed-images/{expected_prep_key}"

    # 1. PostgreSQL verification: Scan.preprocessed_image_path populated and status="processing"
    async def _check_db():
        conn = await asyncpg.connect(dsn=DATABASE_URL.replace("+asyncpg", ""))
        try:
            row = await conn.fetchrow(
                "SELECT * FROM scans WHERE scan_id = $1", scan_id
            )
            return dict(row) if row else None
        finally:
            await conn.close()

    db_scan = asyncio.run(_check_db())
    assert db_scan is not None
    assert db_scan["preprocessed_image_path"] == expected_prep_path
    assert db_scan["status"] == "processing"

    # 2. MinIO verification: preprocessed-images contains output PNG with size > 0
    s3_obj = s3_client.get_object(Bucket="preprocessed-images", Key=expected_prep_key)
    preprocessed_bytes = s3_obj["Body"].read()
    assert len(preprocessed_bytes) > 0

    # 3. Image quality: remaining skew angle < 0.5 degrees
    out_arr = cv2.imdecode(np.frombuffer(preprocessed_bytes, np.uint8), cv2.IMREAD_GRAYSCALE)
    edges = cv2.Canny(out_arr, 50, 150)
    contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    assert contours, "Expected contours on deskewed preprocessed output"
    largest_c = max(contours, key=cv2.contourArea)
    remaining_skew = _compute_skew_angle(largest_c)
    assert abs(remaining_skew) < 0.5, f"Expected remaining skew < 0.5 deg, got {remaining_skew}"

    # Teardown
    try:
        s3_client.delete_object(Bucket="raw-images", Key=expected_raw_key)
    except ClientError:
        pass
    try:
        s3_client.delete_object(Bucket="preprocessed-images", Key=expected_prep_key)
    except ClientError:
        pass
    asyncio.run(_delete_scan_by_id(scan_id))
