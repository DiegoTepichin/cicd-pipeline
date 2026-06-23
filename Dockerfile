# Etapa 1: Builder
FROM python:3.11-slim AS builder

WORKDIR /app

# Solo copiamos el requirements primero para aprovechar la caché de Docker
COPY app/requirements.txt .
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /app/wheels -r requirements.txt

# Etapa 2: Runner
FROM python:3.11-slim

# Crear usuario no root por seguridad (Least Privilege)
RUN useradd -m -r appuser && \
    mkdir /app && \
    chown -R appuser /app

WORKDIR /app

# Copiar wheels desde el builder y dependencias
COPY --from=builder /app/wheels /wheels
COPY --from=builder /app/requirements.txt .

RUN pip install --no-cache /wheels/*

# Copiar el código de la app
COPY app/ app/

# Cambiar al usuario no root
USER appuser

# Exponer el puerto
EXPOSE 5000

# Comando para iniciar gunicorn (WSGI Server)
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app.main:app"]
