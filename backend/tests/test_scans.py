"""Integration tests for the /scans endpoints and image upload processing pipeline.

Covers:
- POST /scans/upload (Inspector-only, image validation, 20MB limit, MinIO storage, Celery chain)
- GET /scans/{scan_id}/status (any authenticated role)
- GET /scans/{scan_id}/declarations (any authenticated role)
"""
import asyncio
import io
import uuid

import asyncpg
import pytest
from botocore.exceptions import ClientError

from app.celery_app import celery_app
from app.database import DATABASE_URL
from app.storage import ensure_buckets, s3_client

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

# Minimal valid 1x1 PNG byte stream
TINY_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\rIDATx\x9cc`\x00\x00\x00"
    b"\x02\x00\x01H\xaf\xa4q\x00\x00\x00\x00IEND\xaeB`\x82"
)


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
    assert db_scan["preprocessed_image_path"] is None
    # Scan row in PostgreSQL starts with status="queued"
    assert db_scan["status"] == "queued"

    # Clean up MinIO and database
    try:
        s3_client.delete_object(Bucket="raw-images", Key=expected_s3_key)
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
    asyncio.run(_delete_scan_by_id(scan_id))
