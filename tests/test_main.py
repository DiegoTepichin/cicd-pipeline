import pytest
from app.main import app

@pytest.fixture
def client():
    """Fixture de pytest para crear un cliente de pruebas de Flask."""
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client

def test_index_endpoint(client):
    """Prueba que el endpoint principal responde correctamente."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "success"
    assert "version" in data

def test_health_endpoint(client):
    """Prueba el endpoint de health check."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json()["status"] == "healthy"
