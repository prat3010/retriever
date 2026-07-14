from fastapi.testclient import TestClient

from src.main import app

client = TestClient(app)


def test_liveness_endpoint() -> None:
    response = client.get("/health/liveness")
    assert response.status_code == 200
    assert response.json()["status"] == "alive"


from unittest.mock import AsyncMock, patch


@patch("src.main.redis_client.ping", new_callable=AsyncMock)
@patch("src.main.engine", autospec=True)
def test_readiness_endpoint(mock_engine, mock_ping) -> None:
    # Setup async context manager mocks for database connection pool
    mock_conn = AsyncMock()
    mock_engine.connect.return_value.__aenter__.return_value = mock_conn
    mock_ping.return_value = True

    response = client.get("/health/readiness")
    assert response.status_code == 200
    assert response.json()["status"] == "ready"


@patch("src.main.redis_client.ping", new_callable=AsyncMock)
@patch("src.main.engine", autospec=True)
def test_readiness_db_down(mock_engine, mock_ping) -> None:
    mock_engine.connect.side_effect = Exception("DB unreachable")
    response = client.get("/health/readiness")
    assert response.status_code == 503
    assert "Readiness check failed" in response.json()["detail"]


def test_root_endpoint() -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "Swagger" in response.json()["message"]
