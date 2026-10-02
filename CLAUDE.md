# CLAUDE.md — Guía de desarrollo

Guía para desarrolladores (humanos o asistentes) que trabajan en este repositorio. Para la visión general del proyecto consulta [README.md](README.md).

## Resumen

API Flask mínima que sirve como vehículo de un pipeline CI/CD con quality gates, escaneo de seguridad e imagen Docker endurecida. **Lo importante del repo es la cadena de entrega.** Cualquier cambio debe mantener verdes todos los gates.

## Comandos

| Tarea | Comando |
|-------|---------|
| Instalar (dev + hooks) | `make install` |
| Servidor dev (auto-reload) | `make dev` |
| Stack dev en Docker | `make up` / `make down` |
| **Todos los gates de CI** | `make check` |
| Lint + formato (verificación) | `make lint` |
| Autoformatear | `make format` |
| Tipado | `make typecheck` |
| SAST | `make security` |
| Tests + cobertura | `make test` |
| Un test concreto | `pytest tests/test_main.py::test_health_endpoint -v` |
| Imagen de producción | `make build` y luego `make run` |
| Limpiar cachés | `make clean` |

Antes de hacer push, ejecuta siempre `make check`. Es exactamente lo que corre el job `quality-gates` en CI.

## Arquitectura

- `app/main.py` contiene la **application factory** `create_app(config=None)` y un `app = create_app()` a nivel de módulo. Gunicorn (`app.main:app`) y Flask CLI (`--app app.main`) consumen ese objeto. Ese entrypoint no debe cambiar sin actualizar el `Dockerfile`.
- La configuración se lee de variables de entorno dentro de `create_app` (12-Factor). Cada variable nueva se documenta en `.env.example` y en la tabla del README.
- Las rutas, los `errorhandler` y cualquier blueprint futuro se registran **dentro** de `create_app`. No se usan objetos `app` globales en otros módulos.
- Los errores siempre se devuelven como JSON con la forma `{"status": "error", "error": <nombre>, "message": <texto>}`. Las excepciones no controladas se registran con `logger.exception` y responden con un 500 genérico. **Nunca se exponen mensajes internos al cliente.**

### Dependencias: dos archivos, una regla

- `pyproject.toml` es la fuente de verdad (runtime en `dependencies` y herramientas en `[dev]`).
- `app/requirements.txt` contiene **solo** las dependencias de runtime, con las mismas versiones pineadas. Lo usa el stage `builder` del Dockerfile.
- Si añades o actualizas una dependencia de runtime, **actualiza los dos archivos** en el mismo commit.
- Si cambias la versión de Ruff, mypy o Hadolint, sincroniza `pyproject.toml` y `.pre-commit-config.yaml`.

### Docker

Los stages son `builder` → `base` → `development` | `runner`.

- `runner` es la imagen de producción: corre como UID/GID numérico `10001`, tiene `HEALTHCHECK` sobre `/health` y Gunicorn se ajusta con `GUNICORN_CMD_ARGS`.
- `development` lo usa `docker-compose.yml`, que monta `./app` para hot-reload.
- Todo lo que no necesita la imagen se excluye en `.dockerignore` (tests, docs, secretos). Si un stage necesita un archivo nuevo, revisa ese archivo primero.

## Convenciones de código

- **Python 3.11+.** Usa sintaxis moderna: `X | None`, `dict[str, Any]`, `collections.abc`.
- **Tipado obligatorio.** mypy corre con `disallow_untyped_defs`, así que toda función (incluidas las de tests y fixtures) lleva anotaciones.
- **Ruff** se encarga del formato (line-length 100, comillas dobles) y del lint (`E,F,W,I,B,UP,S,SIM`). No desactives reglas sin justificarlo en un comentario.
- Las docstrings van en todas las funciones públicas y los endpoints. Los comentarios explican el *por qué*, no el *qué*.
- Usa `logging` (`logger = logging.getLogger(__name__)`), nunca `print`.
- **Seguridad:** no hardcodees binds a `0.0.0.0` en código Python (Bandit B104). El bind de producción vive en el `CMD` del Dockerfile. Tampoco pongas secretos en el código ni en `.env.example`.

## Tests

- Usa `pytest` con las fixtures `app` (instancia nueva vía `create_app({"TESTING": True, ...})`) y `client`.
- No importes ni mutes el `app` global del módulo en los tests. Crea instancias con la factory.
- Cada endpoint o handler nuevo necesita tests del caso feliz y de error.
- La cobertura mínima es **90%** (`fail_under` en `pyproject.toml`) y CI falla por debajo de ese valor.

## Flujo de Git

- **Ramas:** `main` siempre es desplegable. Trabaja en ramas `feat/…`, `fix/…`, `docs/…`, `ci/…` o `refactor/…` y abre un PR hacia `main`. El PR dispara todos los gates, incluidos el build y el escaneo de la imagen.
- **Conventional Commits:** `<tipo>(<scope opcional>): <descripción en imperativo>`
  - Tipos: `feat`, `fix`, `refactor`, `perf`, `test`, `docs`, `build`, `ci`, `chore`, `style`
  - Ejemplos: `feat(api): add readiness endpoint`, `fix(docker): run healthcheck as non-root`
- **Commits atómicos:** un cambio lógico por commit, y cada commit deja los gates en verde.
- **pre-commit** está instalado vía `make install`. No uses `--no-verify` para saltarte los hooks.
- **Autoría:** los commits se hacen con la identidad Git del desarrollador (`user.name` / `user.email`). No se añaden trailers `Co-authored-by` de herramientas.

## CI/CD (`.github/workflows/ci-cd.yml`)

1. `quality-gates`: matriz con Python 3.11 y 3.12 que corre Ruff, mypy, Bandit y pytest con cobertura.
2. `dockerfile-lint`: Hadolint.
3. `build-scan-push`: Buildx (target `runner`, caché GHA), smoke test de `/health` y Trivy (falla con CVEs CRITICAL/HIGH). Hace push a Docker Hub (`:sha` y `:latest`) **solo** en push a `main` y si existen los secretos `DOCKERHUB_USERNAME` y `DOCKERHUB_TOKEN`.

Si un gate falla en CI, reprodúcelo en local con `make check` (o con `make build` y `docker run` para la parte de la imagen) antes de tocar el workflow.
