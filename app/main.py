"""Flask application entrypoint.

Exposes ``create_app`` (application factory) and a module-level ``app`` instance
consumed by Gunicorn (``app.main:app``) and the Flask CLI.
"""

import logging
import os
from typing import Any

from flask import Flask, Response, jsonify
from werkzeug.exceptions import HTTPException

logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


def create_app(config: dict[str, Any] | None = None) -> Flask:
    """Build and configure the Flask application.

    Configuration is read from environment variables (12-Factor) and can be
    overridden with ``config``, mainly for tests.
    """
    app = Flask(__name__)
    app.config.update(
        APP_NAME=os.environ.get("APP_NAME", "CI/CD Pipeline"),
        APP_VERSION=os.environ.get("APP_VERSION", "1.0.0"),
    )
    if config:
        app.config.update(config)

    @app.get("/")
    def index() -> Response:
        """Service metadata endpoint."""
        logger.info("Request received at /")
        return jsonify(
            status="success",
            message=f"Bienvenido a la API de {app.config['APP_NAME']}",
            version=app.config["APP_VERSION"],
        )

    @app.get("/health")
    def health() -> tuple[Response, int]:
        """Liveness probe for load balancers, Docker HEALTHCHECK and orchestrators."""
        return jsonify(status="healthy"), 200

    @app.errorhandler(HTTPException)
    def handle_http_error(error: HTTPException) -> tuple[Response, int]:
        """Return HTTP errors (404, 405, ...) as JSON instead of HTML."""
        return jsonify(
            status="error", error=error.name, message=error.description
        ), error.code or 500

    @app.errorhandler(Exception)
    def handle_unexpected_error(error: Exception) -> tuple[Response, int]:
        """Log unhandled exceptions and return a generic 500 without leaking internals."""
        logger.exception("Unhandled exception: %s", error)
        return jsonify(
            status="error",
            error="Internal Server Error",
            message="An unexpected error occurred.",
        ), 500

    return app


app = create_app()


if __name__ == "__main__":
    # Local-only entrypoint; production runs through Gunicorn (see Dockerfile).
    # Default to loopback: binding to all interfaces must be opted into via HOST.
    app.run(
        host=os.environ.get("HOST", "127.0.0.1"),
        port=int(os.environ.get("PORT", "5000")),
    )
