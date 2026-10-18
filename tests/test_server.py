from fastapi.testclient import TestClient

from shamba.server import app


def test_health_endpoint():
    with TestClient(app) as client:
        response = client.get("/healthz")
    assert response.status_code == 200
    assert "ok" in response.json()
