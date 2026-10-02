from collections.abc import Iterator

import pytest
from flask import Flask
from flask.testing import FlaskClient

from app.main import create_app


@pytest.fixture
def app() -> Flask:
    """Fresh application instance per test, isolated from the module-level app."""
    return create_app({"TESTING": True, "APP_VERSION": "9.9.9"})


@pytest.fixture
def client(app: Flask) -> Iterator[FlaskClient]:
    """Flask test client."""
    with app.test_client() as client:
        yield client


def test_index_endpoint(client: FlaskClient) -> None:
    """The root endpoint returns service metadata from config."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "success"
    assert data["version"] == "9.9.9"


def test_health_endpoint(client: FlaskClient) -> None:
    """The health check returns 200 and a healthy status."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json() == {"status": "healthy"}


def test_unknown_route_returns_json_404(client: FlaskClient) -> None:
    """Unknown routes return a JSON error body instead of HTML."""
    response = client.get("/does-not-exist")
    assert response.status_code == 404
    assert response.is_json
    assert response.get_json()["status"] == "error"


def test_method_not_allowed_returns_json_405(client: FlaskClient) -> None:
    """Unsupported HTTP methods return a JSON 405."""
    response = client.post("/health")
    assert response.status_code == 405
    assert response.get_json()["error"] == "Method Not Allowed"


def test_unhandled_exception_returns_generic_500(app: Flask) -> None:
    """Unexpected exceptions are returned as a generic JSON 500 without internals."""

    @app.get("/boom")
    def boom() -> str:
        raise RuntimeError("secret internal detail")

    response = app.test_client().get("/boom")
    assert response.status_code == 500
    body = response.get_json()
    assert body["status"] == "error"
    assert "secret internal detail" not in response.get_data(as_text=True)
