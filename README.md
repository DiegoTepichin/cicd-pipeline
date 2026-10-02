# CI/CD Pipeline — API Flask lista para producción

[![CI/CD Pipeline](https://github.com/DiegoTepichin/cicd-pipeline/actions/workflows/ci-cd.yml/badge.svg)](https://github.com/DiegoTepichin/cicd-pipeline/actions/workflows/ci-cd.yml)
![Python](https://img.shields.io/badge/python-3.11%20%7C%203.12-blue)
![Docker](https://img.shields.io/badge/docker-multi--stage-2496ED)
![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-D7FF64)

Una API REST en Flask deliberadamente pequeña. Su propósito es servir de **vehículo para una cadena de entrega de software completa**: cada cambio pasa por lint, tipado estático, análisis de seguridad, pruebas con umbral de cobertura, construcción de una imagen endurecida, una prueba de humo y un escaneo de vulnerabilidades. Solo después de todo eso se publica en un registro de contenedores.

---

## El problema que resuelve

En muchos equipos el camino de "funciona en mi máquina" a "está en producción" es manual, inconsistente y sin controles de seguridad. Este repositorio muestra una plantilla reproducible para que:

- **Ningún cambio llegue a `main` sin pasar quality gates automáticos.** Esos gates son los mismos en local (`make check`, pre-commit) y en CI.
- **Las vulnerabilidades se detecten antes del despliegue**, a nivel de código (Bandit, SAST) y de imagen (Trivy: CVEs del SO y de librerías).
- **El artefacto desplegable sea inmutable y trazable**: cada imagen se etiqueta con el SHA del commit que la produjo.
- **El entorno local sea idéntico al de producción**, con Docker multi-stage y un target de desarrollo con hot-reload.

---

## Arquitectura

### Flujo del pipeline

```mermaid
flowchart LR
    dev[Developer] -->|git commit| hooks[pre-commit<br/>ruff · mypy · hadolint]
    hooks -->|git push / PR| gha{GitHub Actions}

    subgraph QG[Quality gates · matriz Python 3.11 / 3.12]
        lint[Ruff<br/>lint + format] --> types[mypy] --> sast[Bandit<br/>SAST] --> tests[pytest<br/>cobertura ≥ 90%]
    end
    gha --> QG
    gha --> hl[Hadolint<br/>Dockerfile]

    QG --> build[Buildx<br/>target: runner<br/>caché GHA]
    hl --> build
    build --> smoke[Smoke test<br/>GET /health]
    smoke --> trivy[Trivy<br/>CRITICAL/HIGH = fail]
    trivy -->|solo push a main| hub[(Docker Hub<br/>:sha · :latest)]
```

### Imagen Docker multi-stage

```mermaid
flowchart TB
    builder["builder<br/>pip wheel → /build/wheels"] -. bind mount .-> base
    base["base<br/>python:3.11-slim + deps runtime"] --> development["development<br/>+ deps dev · flask --debug<br/>(docker compose)"]
    base --> runner["runner (producción)<br/>UID 10001 no-root · Gunicorn<br/>HEALTHCHECK /health"]
```

### Estructura del repositorio

```
.
├── app/
│   ├── main.py              # create_app() factory, rutas y manejadores de error
│   └── requirements.txt     # Dependencias runtime (consumidas por Docker)
├── tests/
│   └── test_main.py         # Pruebas de endpoints y rutas de error
├── .github/workflows/
│   └── ci-cd.yml            # Pipeline: quality gates → build → smoke → scan → push
├── Dockerfile               # builder / base / development / runner
├── docker-compose.yml       # Stack local con hot-reload
├── pyproject.toml           # Metadatos, dependencias y config de ruff/mypy/pytest/bandit
├── .pre-commit-config.yaml  # Mismos gates que CI, antes de cada commit
├── Makefile                 # Interfaz única de comandos (make help)
└── .env.example             # Variables de entorno documentadas
```

### API

| Método | Ruta      | Descripción                                       | Respuesta                                             |
|--------|-----------|---------------------------------------------------|-------------------------------------------------------|
| GET    | `/`       | Metadatos del servicio                            | `200 {"status":"success","message":…,"version":…}`    |
| GET    | `/health` | Liveness probe (Docker, balanceadores, K8s)       | `200 {"status":"healthy"}`                            |
| *      | otra ruta | Error HTTP serializado como JSON                  | `404/405 {"status":"error","error":…,"message":…}`    |
| *      | excepción | Error interno genérico, sin filtrar detalles      | `500 {"status":"error","error":"Internal Server Error"}` |

---

## Stack tecnológico y decisiones

| Área | Elección | Por qué |
|------|----------|---------|
| Framework | **Flask 3** + application factory | Mínimo y explícito. `create_app()` permite instancias aisladas por test y configuración inyectable. |
| Servidor WSGI | **Gunicorn** | El servidor de desarrollo de Flask no sirve para producción. Workers e hilos se ajustan con `GUNICORN_CMD_ARGS` sin reconstruir la imagen. |
| Empaquetado | **pyproject.toml** (PEP 621) | Una sola fuente de verdad para dependencias y herramientas. `requirements.txt` queda solo con lo de runtime para que la imagen sea ligera. |
| Lint / formato | **Ruff** | Sustituye a flake8, isort, black y pyupgrade con una sola herramienta muy rápida. Incluye reglas `S` (bandit) y `B` (bugbear). |
| Tipado | **mypy** (`disallow_untyped_defs`) | Exige firmas tipadas, así los errores de contrato aparecen antes de ejecutar el código. |
| SAST | **Bandit** | Detecta patrones inseguros en Python. Ya encontró un caso real: un bind a `0.0.0.0` hardcodeado. |
| Contenedor | **Docker multi-stage** | Las wheels se montan desde el builder sin convertirse en capa. El usuario es no-root con UID numérico fijo (compatible con `runAsNonRoot` de Kubernetes), e incluye `HEALTHCHECK`. |
| Escaneo de imagen | **Trivy** | Bloquea el pipeline ante CVEs `CRITICAL`/`HIGH` que ya tengan parche. |
| CI/CD | **GitHub Actions** | Matriz de Python, caché de pip y de capas Buildx (GHA), `concurrency` para cancelar ejecuciones obsoletas y `permissions: contents: read`. |
| Shift-left | **pre-commit** | Ruff, mypy y Hadolint corren antes de cada commit, así se falla en local y no en CI. |

---

## Puesta en marcha

### Requisitos

- Python 3.11+
- Docker 24+ con BuildKit (incluido en Docker Desktop)
- `make` (opcional, pero recomendado)

### 1. Configuración

```bash
git clone https://github.com/DiegoTepichin/cicd-pipeline.git
cd cicd-pipeline
cp .env.example .env          # ajusta valores si lo necesitas
```

| Variable            | Default                                                | Uso |
|---------------------|--------------------------------------------------------|-----|
| `APP_NAME`          | `CI/CD Pipeline`                                       | Nombre que devuelve `/` |
| `APP_VERSION`       | `1.0.0`                                                | Versión que devuelve `/` |
| `LOG_LEVEL`         | `INFO`                                                 | Nivel de logging (`DEBUG`, `INFO`, `WARNING`…) |
| `HOST` / `PORT`     | `127.0.0.1` / `5000`                                   | Solo para `python -m app.main` |
| `GUNICORN_CMD_ARGS` | `--workers 2 --threads 4 --timeout 30 --access-logfile -` | Tuning de Gunicorn en la imagen de producción |

### 2. Desarrollo local

**Opción A, con virtualenv:**

```bash
python -m venv .venv && source .venv/bin/activate
make install                  # pip install -e ".[dev]" + pre-commit install
make dev                      # http://localhost:5000 con auto-reload
```

**Opción B, con Docker Compose (hot-reload):**

```bash
make up                       # docker compose up --build
```

### 3. Verificación (los mismos gates que CI)

```bash
make check                    # lint + typecheck + security + test
make help                     # lista todos los comandos
```

### 4. Imagen de producción

```bash
make build                    # docker build --target runner
make run                      # http://localhost:5000
curl localhost:5000/health    # {"status":"healthy"}
```

### 5. Publicación continua (Docker Hub)

El job `build-scan-push` publica `:<sha>` y `:latest` en cada push a `main`. Para activarlo, configura en **Settings → Secrets and variables → Actions**:

- `DOCKERHUB_USERNAME`
- `DOCKERHUB_TOKEN` (un [access token](https://docs.docker.com/security/for-developers/access-tokens/) con permiso *Read & Write*, nunca la contraseña)

Si faltan los secretos, el pipeline igual construye, prueba y escanea la imagen. Solo omite el push y deja un *warning*, sin romper el build.

### Integración en producción

La imagen `runner` es stateless y se configura por completo con variables de entorno, así que se despliega igual en cualquier orquestador:

- **Kubernetes:** usa `/health` como `livenessProbe` y `readinessProbe`. El UID numérico 10001 cumple `runAsNonRoot: true`.
- **AWS ECS / Cloud Run / Azure Container Apps:** expón el puerto `5000` y ajusta la concurrencia con `GUNICORN_CMD_ARGS`.
- **Rollbacks:** despliega por tag de SHA, no por `:latest`. Cada imagen es inmutable y trazable a su commit.

---

## Métricas y buenas prácticas

Medido localmente sobre este commit:

| Métrica | Valor |
|---------|-------|
| Cobertura de pruebas | **97%** (umbral obligatorio: 90%) |
| Suite de pruebas | 5 tests en < 1 s |
| Imagen de producción (`runner`) | **234 MB** (vs. 353 MB del target `development`) |
| Hallazgos de Bandit / Hadolint / mypy | **0** |
| CVEs CRITICAL/HIGH con parche (Trivy) | **0** |
| Usuario en runtime | `uid=10001` (no-root) |

**Escalabilidad.** La API no guarda estado, así que escala horizontalmente detrás de un balanceador sin cambios. Verticalmente, Gunicorn usa workers (procesos) × threads, configurable en runtime. Una regla habitual de partida es `workers = 2 × CPU + 1`.

**Prácticas aplicadas:** 12-Factor App (configuración por entorno, logs a stdout), principio de mínimo privilegio (contenedor no-root, token de CI de solo lectura), shift-left security (SAST + escaneo de imagen + pre-commit), artefactos inmutables, errores que no exponen detalles internos y Conventional Commits.

---

## Roadmap

- [ ] Fijar las GitHub Actions por SHA (protección de supply chain)
- [ ] Generar SBOM y firmar la imagen (Syft + Cosign)
- [ ] Logging estructurado en JSON y endpoint `/metrics` (Prometheus)
- [ ] Separar `liveness` y `readiness` cuando existan dependencias externas
- [ ] Despliegue automático a un entorno de staging

---

## Contribuir

Consulta [CLAUDE.md](CLAUDE.md) para ver las convenciones de código, el flujo de Git y los comandos del repositorio.

## Autor

**Diego Durón Tepichín** · [GitHub @DiegoTepichin](https://github.com/DiegoTepichin)
