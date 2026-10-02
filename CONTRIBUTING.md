# Contributing

Thanks for your interest in this project! This guide explains how to set up a development environment, run the same checks CI runs and structure your changes. For an overview of the project, see the [README](README.md).

## Prerequisites

- Python 3.11+
- Docker 24+ with BuildKit, needed only for image builds and `docker compose`
- `make`

## Setup

```bash
git clone https://github.com/DiegoTepichin/cicd-pipeline.git
cd cicd-pipeline
python3 -m venv .venv && source .venv/bin/activate
make install        # pip install -e ".[dev]" + pre-commit install
```

## Everyday commands

| Task | Command |
|------|---------|
| Dev server with auto-reload | `make dev` |
| Dev stack in Docker (hot-reload) | `make up` / `make down` |
| **Every CI quality gate** | `make check` |
| Lint + format check | `make lint` |
| Auto-fix and format | `make format` |
| Type checking | `make typecheck` |
| Security scan (SAST) | `make security` |
| Tests + coverage | `make test` |
| A single test | `pytest tests/test_main.py::test_health_endpoint -v` |
| Production image | `make build`, then `make run` |
| List all targets | `make help` |

**Run `make check` before every push.** It runs the same gates as the `quality-gates` CI job: Ruff, mypy, Bandit and pytest with a 90% coverage floor.

## Pre-commit hooks

`make install` registers hooks that run Ruff, mypy, Hadolint and basic file hygiene checks on every commit. Hadolint runs through [`hadolint-py`](https://github.com/AleksaC/hadolint-py), so **Docker does not need to be running** to commit. Please don't bypass the hooks with `--no-verify`.

## Code conventions

- **Python 3.11+ syntax:** `X | None`, `dict[str, Any]`, `collections.abc`.
- **Type hints are mandatory.** mypy runs with `disallow_untyped_defs`, including on tests and fixtures.
- **Ruff** owns formatting (line length 100, double quotes) and linting (`E,F,W,I,B,UP,S,SIM`). If you disable a rule, justify it in a comment.
- Write docstrings for public functions and endpoints. Comments explain *why*, not *what*.
- Use `logging`, never `print`.
- **Security:** never hardcode a `0.0.0.0` bind in Python (Bandit B104); the production bind lives in the Dockerfile `CMD`. Never commit secrets. `.env` is git-ignored.

### Application structure

- `app/main.py` exposes the `create_app()` factory and a module-level `app` used by Gunicorn (`app.main:app`). Register routes and error handlers **inside** `create_app`.
- Configuration comes from environment variables. Document any new variable in `.env.example` and in both READMEs.
- Errors are always JSON (`{"status": "error", "error": ..., "message": ...}`). Unhandled exceptions return a generic 500 and never expose internal details.

### Dependencies

`pyproject.toml` is the source of truth. `app/requirements.txt` mirrors **only** the runtime dependencies, because the Docker builder stage uses it. When you add or bump a runtime dependency, update both files in the same commit.

## Tests

- Use the `app` fixture, a fresh instance from `create_app({"TESTING": True, ...})`, and the `client` fixture. Don't import or mutate the module-level `app`.
- Every new endpoint or handler needs tests for the happy path and the error path.
- Coverage below **90%** fails CI.

## Git workflow

- `main` is always releasable. Branch off as `feat/…`, `fix/…`, `docs/…`, `ci/…` or `refactor/…` and open a pull request against `main`. PRs run every gate, including the image build, smoke test and Trivy scan.
- Use [Conventional Commits](https://www.conventionalcommits.org/): `<type>(<optional scope>): <imperative summary>`
  - Types: `feat`, `fix`, `refactor`, `perf`, `test`, `docs`, `build`, `ci`, `chore`, `style`
  - Examples: `feat(api): add readiness endpoint`, `fix(docker): run healthcheck as non-root`
- Keep commits atomic: one logical change per commit, and every gate passes after each commit.
