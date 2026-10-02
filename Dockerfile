# syntax=docker/dockerfile:1.7
ARG PYTHON_VERSION=3.11

# ═══════════════════════════════════════════════
# Stage 1: Builder — resolve runtime deps into wheels
# ═══════════════════════════════════════════════
FROM python:${PYTHON_VERSION}-slim AS builder

WORKDIR /build
COPY app/requirements.txt .
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /build/wheels -r requirements.txt

# ═══════════════════════════════════════════════
# Stage 2: Base — shared Python runtime settings
# ═══════════════════════════════════════════════
FROM python:${PYTHON_VERSION}-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Apply Debian security patches not yet rolled into the upstream base image
# hadolint ignore=DL3005
RUN apt-get update && \
    apt-get upgrade -y --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Wheels are bind-mounted, so they never become an image layer
RUN --mount=type=bind,from=builder,source=/build/wheels,target=/wheels \
    pip install /wheels/*

EXPOSE 5000

# ═══════════════════════════════════════════════
# Stage 3: Development — hot-reload + dev tooling
# ═══════════════════════════════════════════════
FROM base AS development

COPY pyproject.toml .
COPY app/ app/
RUN pip install -e ".[dev]"

CMD ["flask", "--app", "app.main", "run", "--host", "0.0.0.0", "--port", "5000", "--debug"]

# ═══════════════════════════════════════════════
# Stage 4: Runner — minimal, non-root production image
# ═══════════════════════════════════════════════
FROM base AS runner

# Tunable at runtime without rebuilding (e.g. -e GUNICORN_CMD_ARGS="--workers 4")
ENV GUNICORN_CMD_ARGS="--workers 2 --threads 4 --timeout 30 --access-logfile -"

# Build tooling is not needed at runtime and only adds attack surface (CVE-flagged
# vendored packages); pip itself is kept for debugging inside the container.
RUN pip uninstall -y setuptools wheel && \
    groupadd --system --gid 10001 appuser && \
    useradd --system --no-create-home --uid 10001 --gid 10001 appuser

COPY --chown=10001:10001 app/ app/

USER 10001:10001

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD ["python", "-c", "import urllib.request,sys; sys.exit(urllib.request.urlopen('http://127.0.0.1:5000/health', timeout=2).status != 200)"]

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app.main:app"]
