from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)


def test_liveness_endpoint() -> None:
    response = client.get("/health/liveness")
    assert response.status_code == 200
    assert response.json()["status"] == "alive"


def test_readiness_endpoint() -> None:
    response = client.get("/health/readiness")
    assert response.status_code == 200
    assert response.json()["status"] == "ready"


def test_root_endpoint() -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "Swagger" in response.json()["message"]
