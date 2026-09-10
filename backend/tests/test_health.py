def test_root(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "running"


def test_auth_health(client):
    response = client.get("/auth/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "auth"}


def test_products_health(client):
    response = client.get("/products/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "products"}


def test_scans_health(client):
    response = client.get("/scans/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "scans"}


def test_reports_health(client):
    response = client.get("/reports/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "reports"}


def test_dashboard_health(client):
    response = client.get("/dashboard/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "dashboard"}
