import os
import logging
from flask import Flask, jsonify

# Configuración de logging estructurado y nivel INFO
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)

app = Flask(__name__)

@app.route("/")
def index():
    """Endpoint principal."""
    app.logger.info("Request recibida en /")
    return jsonify({
        "status": "success",
        "message": "Bienvenido a la API de CI/CD Pipeline",
        "version": "1.0.0"
    })

@app.route("/health")
def health():
    """Health check endpoint para balanceadores de carga y orquestadores."""
    return jsonify({
        "status": "healthy"
    }), 200

if __name__ == "__main__":
    # Leer el puerto desde las variables de entorno (12-Factor App)
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
