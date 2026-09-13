"""Integration tests for the /products endpoints.

Covers catalog search, creation, retrieval, and partial updates with role-based access control.
Requires a reachable, migrated Postgres database (same as test_auth.py).
"""
import asyncio
import uuid

import asyncpg
import pytest

from app.database import DATABASE_URL, engine

ADMIN_EMAIL = "admin@lmpc.gov"
ADMIN_PASSWORD = "ChangeMe_Dev_Only!123"

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module", autouse=True)
def _reset_db_engine():
    engine.sync_engine.dispose()
    yield
    engine.sync_engine.dispose()


async def _delete_user_by_email(email: str) -> None:
    conn = await asyncpg.connect(dsn=DATABASE_URL.replace("+asyncpg", ""))
    try:
        await conn.execute("DELETE FROM users WHERE email = $1", email)
    finally:
        await conn.close()


async def _delete_product_by_id(product_id: uuid.UUID | str) -> None:
    conn = await asyncpg.connect(dsn=DATABASE_URL.replace("+asyncpg", ""))
    try:
        await conn.execute(
            "DELETE FROM products WHERE product_id = $1",
            uuid.UUID(str(product_id)),
        )
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
def inspector_token(client, admin_token):
    email = f"pytest.inspector.{uuid.uuid4().hex[:8]}@lmpc.gov"
    reg = client.post(
        "/auth/register",
        json={
            "name": "Pytest Inspector",
            "email": email,
            "password": "TempPass!123",
            "role": "Inspector",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert reg.status_code == 201

    login = client.post(
        "/auth/login", json={"email": email, "password": "TempPass!123"}
    )
    assert login.status_code == 200

    yield login.json()["access_token"]

    asyncio.run(_delete_user_by_email(email))


@pytest.fixture
def reviewer_token(client, admin_token):
    email = f"pytest.reviewer.{uuid.uuid4().hex[:8]}@lmpc.gov"
    reg = client.post(
        "/auth/register",
        json={
            "name": "Pytest Reviewer",
            "email": email,
            "password": "TempPass!123",
            "role": "Reviewer",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert reg.status_code == 201

    login = client.post(
        "/auth/login", json={"email": email, "password": "TempPass!123"}
    )
    assert login.status_code == 200

    yield login.json()["access_token"]

    asyncio.run(_delete_user_by_email(email))


@pytest.fixture
def created_products():
    product_ids: list[str] = []
    yield product_ids

    if product_ids:

        async def _cleanup():
            conn = await asyncpg.connect(dsn=DATABASE_URL.replace("+asyncpg", ""))
            try:
                for pid in product_ids:
                    await conn.execute(
                        "DELETE FROM products WHERE product_id = $1",
                        uuid.UUID(str(pid)),
                    )
            finally:
                await conn.close()

        asyncio.run(_cleanup())


def test_search_products_unauthenticated(client):
    resp = client.get("/products?q=test")
    assert resp.status_code == 401


def test_search_finds_product_by_name_and_barcode(
    client, inspector_token, admin_token, created_products
):
    tag = uuid.uuid4().hex[:8]
    barcode = f"890{uuid.uuid4().int % 10000000000:010d}"
    payload = {
        "name": f"SpecialTea UniqueBlend {tag}",
        "brand": f"ChaiBrand {tag}",
        "manufacturer_name": "Tea Producers Ltd",
        "manufacturer_address": "Estate 4, Hill Road",
        "category": "Beverages",
        "barcode": barcode,
    }
    create_resp = client.post(
        "/products",
        json=payload,
        headers={"Authorization": f"Bearer {inspector_token}"},
    )
    assert create_resp.status_code == 201
    prod = create_resp.json()
    created_products.append(prod["product_id"])

    # Search by fragment of name
    search_name_resp = client.get(
        "/products?q=UniqueBlend",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert search_name_resp.status_code == 200
    results = search_name_resp.json()
    assert any(p["product_id"] == prod["product_id"] for p in results)

    # Search by exact barcode
    search_barcode_resp = client.get(
        f"/products?q={barcode}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert search_barcode_resp.status_code == 200
    results = search_barcode_resp.json()
    assert any(p["product_id"] == prod["product_id"] for p in results)


def test_search_finds_product_with_null_brand(
    client, inspector_token, admin_token, created_products
):
    tag = uuid.uuid4().hex[:8]
    barcode = f"890{uuid.uuid4().int % 10000000000:010d}"
    payload = {
        "name": f"Unbranded Commodity {tag}",
        "brand": None,
        "manufacturer_name": "Generic Miller",
        "category": "Grains",
        "barcode": barcode,
    }
    create_resp = client.post(
        "/products",
        json=payload,
        headers={"Authorization": f"Bearer {inspector_token}"},
    )
    assert create_resp.status_code == 201
    prod = create_resp.json()
    assert prod["brand"] is None
    created_products.append(prod["product_id"])

    # Search by name fragment when brand IS NULL
    search_resp = client.get(
        f"/products?q=Commodity+{tag}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert search_resp.status_code == 200
    results = search_resp.json()
    assert any(p["product_id"] == prod["product_id"] for p in results)


def test_create_product_reviewer_forbidden(client, reviewer_token):
    payload = {
        "name": "Reviewer Attempt Product",
        "category": "Test",
    }
    resp = client.post(
        "/products",
        json=payload,
        headers={"Authorization": f"Bearer {reviewer_token}"},
    )
    assert resp.status_code == 403
    assert resp.json()["detail"] == "Inspector role required"


def test_create_product_rejects_empty_and_whitespace_name(client, inspector_token):
    for bad_name in ("", "   "):
        resp = client.post(
            "/products",
            json={"name": bad_name},
            headers={"Authorization": f"Bearer {inspector_token}"},
        )
        assert resp.status_code == 422


def test_create_product_inspector_success(client, inspector_token, created_products):
    barcode = f"890{uuid.uuid4().int % 10000000000:010d}"
    payload = {
        "name": "Organic Honey 500g",
        "brand": "PureBee",
        "manufacturer_name": "Honey Farms Co",
        "manufacturer_address": "Village Green, Forest District",
        "category": "Sweeteners",
        "barcode": barcode,
    }
    resp = client.post(
        "/products",
        json=payload,
        headers={"Authorization": f"Bearer {inspector_token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    created_products.append(data["product_id"])

    # Verify UUID format and created_at presence
    assert uuid.UUID(data["product_id"])
    assert "created_at" in data and data["created_at"]

    # Verify submitted fields echoed back
    for field, value in payload.items():
        assert data[field] == value


def test_create_product_duplicate_barcode_conflict(
    client, inspector_token, created_products
):
    barcode = f"890{uuid.uuid4().int % 10000000000:010d}"
    payload1 = {"name": "First Product With Barcode", "barcode": barcode}
    resp1 = client.post(
        "/products",
        json=payload1,
        headers={"Authorization": f"Bearer {inspector_token}"},
    )
    assert resp1.status_code == 201
    created_products.append(resp1.json()["product_id"])

    payload2 = {"name": "Second Product Same Barcode", "barcode": barcode}
    resp2 = client.post(
        "/products",
        json=payload2,
        headers={"Authorization": f"Bearer {inspector_token}"},
    )
    assert resp2.status_code == 409
    assert resp2.json()["detail"] == "A product with this barcode already exists"


def test_get_product_by_id_roles_and_not_found(
    client, inspector_token, reviewer_token, admin_token, created_products
):
    create_resp = client.post(
        "/products",
        json={"name": "Lookup Product Test"},
        headers={"Authorization": f"Bearer {inspector_token}"},
    )
    assert create_resp.status_code == 201
    prod = create_resp.json()
    prod_id = prod["product_id"]
    created_products.append(prod_id)

    # Any authenticated role can GET by id
    for token in (inspector_token, reviewer_token, admin_token):
        resp = client.get(
            f"/products/{prod_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["product_id"] == prod_id
        assert resp.json()["name"] == "Lookup Product Test"

    # Unknown UUID -> 404
    nonexistent_id = str(uuid.uuid4())
    resp_404 = client.get(
        f"/products/{nonexistent_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp_404.status_code == 404
    assert resp_404.json()["detail"] == "Product not found"


def test_patch_product_reviewer_forbidden(
    client, inspector_token, reviewer_token, created_products
):
    create_resp = client.post(
        "/products",
        json={"name": "Patch Role Test"},
        headers={"Authorization": f"Bearer {inspector_token}"},
    )
    assert create_resp.status_code == 201
    prod_id = create_resp.json()["product_id"]
    created_products.append(prod_id)

    patch_resp = client.patch(
        f"/products/{prod_id}",
        json={"name": "Reviewer Attempt Patch"},
        headers={"Authorization": f"Bearer {reviewer_token}"},
    )
    assert patch_resp.status_code == 403
    assert patch_resp.json()["detail"] == "Inspector or Admin role required"


def test_patch_product_inspector_and_admin_partial_updates(
    client, inspector_token, admin_token, created_products
):
    barcode = f"890{uuid.uuid4().int % 10000000000:010d}"
    create_resp = client.post(
        "/products",
        json={
            "name": "Initial Product Name",
            "brand": "Initial Brand",
            "manufacturer_name": "Original Maker",
            "manufacturer_address": "Address 101",
            "category": "Snacks",
            "barcode": barcode,
        },
        headers={"Authorization": f"Bearer {inspector_token}"},
    )
    assert create_resp.status_code == 201
    prod_id = create_resp.json()["product_id"]
    created_products.append(prod_id)

    # 1. Inspector patches brand only
    patch_insp = client.patch(
        f"/products/{prod_id}",
        json={"brand": "InspectorPatchedBrand"},
        headers={"Authorization": f"Bearer {inspector_token}"},
    )
    assert patch_insp.status_code == 200
    data_insp = patch_insp.json()
    assert data_insp["brand"] == "InspectorPatchedBrand"
    assert data_insp["name"] == "Initial Product Name"
    assert data_insp["manufacturer_name"] == "Original Maker"
    assert data_insp["manufacturer_address"] == "Address 101"
    assert data_insp["category"] == "Snacks"
    assert data_insp["barcode"] == barcode

    # 2. Admin patches category only
    patch_admin = client.patch(
        f"/products/{prod_id}",
        json={"category": "AdminPatchedCategory"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert patch_admin.status_code == 200
    data_admin = patch_admin.json()
    assert data_admin["category"] == "AdminPatchedCategory"
    assert data_admin["brand"] == "InspectorPatchedBrand"  # preserved from previous patch
    assert data_admin["name"] == "Initial Product Name"
    assert data_admin["barcode"] == barcode


def test_patch_product_duplicate_barcode_conflict(
    client, inspector_token, created_products
):
    bc1 = f"890{uuid.uuid4().int % 10000000000:010d}"
    bc2 = f"890{uuid.uuid4().int % 10000000000:010d}"

    p1 = client.post(
        "/products",
        json={"name": "Prod 1", "barcode": bc1},
        headers={"Authorization": f"Bearer {inspector_token}"},
    ).json()
    created_products.append(p1["product_id"])

    p2 = client.post(
        "/products",
        json={"name": "Prod 2", "barcode": bc2},
        headers={"Authorization": f"Bearer {inspector_token}"},
    ).json()
    created_products.append(p2["product_id"])

    # Patching p2 to use p1's barcode -> 409
    resp_conflict = client.patch(
        f"/products/{p2['product_id']}",
        json={"barcode": bc1},
        headers={"Authorization": f"Bearer {inspector_token}"},
    )
    assert resp_conflict.status_code == 409
    assert resp_conflict.json()["detail"] == "A product with this barcode already exists"

    # Patching p1 with its own barcode -> 200 (not a conflict)
    resp_self = client.patch(
        f"/products/{p1['product_id']}",
        json={"barcode": bc1},
        headers={"Authorization": f"Bearer {inspector_token}"},
    )
    assert resp_self.status_code == 200
    assert resp_self.json()["barcode"] == bc1


def test_patch_product_not_found(client, admin_token):
    nonexistent_id = str(uuid.uuid4())
    resp = client.patch(
        f"/products/{nonexistent_id}",
        json={"name": "Nonexistent"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Product not found"
