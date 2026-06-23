# BE-001 — FastAPI repo scaffold (uv + ruff + mypy --strict + pytest + structlog)

**Wave:** 1
**Type:** BE
**Blocked by:** —
**Blocks:** every other BE ticket
**ADR references:** [ARCHITECTURE.md § Backend](../../ARCHITECTURE.md), [CLAUDE.md § Hard Rules](../../../CLAUDE.md)

## 1. Problem statement

There's no `services/api/` directory yet. Every other BE ticket needs a runnable FastAPI app with the project quality bar (ruff + mypy --strict + pytest) green from the first commit. This ticket lands that skeleton — application factory, settings, structured logging, health check, test harness — and nothing else.

## 2. Actual solution

Create `services/api/` with `pyproject.toml` (uv-managed). Configure ruff (line length 100, the project's existing trifecta of `E`, `F`, `I` rules) and mypy `strict = true`. Add `app/main.py` exposing a FastAPI `app` factory (`def create_app() -> FastAPI`). Configure `structlog` at startup to emit JSON to stdout with timestamp, level, event, and arbitrary context. Add one route — `GET /healthz` — returning `{"status": "ok", "service": "setlist-picker-api"}`. Add `tests/conftest.py` with a `pytest-asyncio` async client fixture and an empty `tests/test_health.py` covering the route. CI workflow at `.github/workflows/api.yml` runs `uv sync`, `ruff check .`, `mypy --strict .`, and `pytest -x` on every push.

No DB yet (migration is BE-002). No auth (BE-003). No settings beyond the env-var loader stub that BE-002 fills in.

## 3. Files to touch

| Path | Edit purpose |
|---|---|
| `services/api/pyproject.toml` | uv project config — dependencies, tool config (ruff, mypy, pytest). |
| `services/api/.python-version` | `3.12.7`. Pins the Python minor for CI + dev consistency. |
| `services/api/app/__init__.py` | Empty; package marker. |
| `services/api/app/main.py` | `create_app()` factory + `app = create_app()` module-level export. |
| `services/api/app/config.py` | `Settings(BaseSettings)` stub — environment loader (Pydantic v2 `BaseSettings`); fields populated in BE-002/003. |
| `services/api/app/logging.py` | `configure_logging()` — installs structlog JSON renderer at INFO level by default. |
| `services/api/app/routes/health.py` | `GET /healthz` handler. |
| `services/api/tests/__init__.py` | Empty. |
| `services/api/tests/conftest.py` | `client` async fixture + `pytest-asyncio` `asyncio_mode = "auto"` config. |
| `services/api/tests/test_health.py` | One test (see § 7). |
| `.github/workflows/api.yml` | CI: ubuntu-latest, Python 3.12, `uv sync --frozen`, ruff, mypy, pytest. |
| `services/api/.env.example` | `LOG_LEVEL=INFO`, `ENV=dev` only — DB / auth env vars added by later tickets. |
| `services/api/README.md` | "How to run" — 6 commands max: `uv sync`, `uv run uvicorn app.main:app --reload`, `uv run ruff check .`, `uv run mypy --strict .`, `uv run pytest`, `uv run pytest -x --lf`. |

## 4. Method signatures / new APIs

```python
# app/main.py
from fastapi import FastAPI
from app.config import Settings
from app.logging import configure_logging
from app.routes import health


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    configure_logging(level=settings.log_level)
    app = FastAPI(title="setlist-picker", version="0.1.0")
    app.include_router(health.router)
    return app


app = create_app()
```

```python
# app/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    env: str = "dev"
    log_level: str = "INFO"
```

```python
# app/routes/health.py
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class HealthResponse(BaseModel):
    status: str
    service: str


@router.get("/healthz", response_model=HealthResponse)
async def healthz() -> HealthResponse:
    return HealthResponse(status="ok", service="setlist-picker-api")
```

Endpoint:

| Method | Path | Body | Response | Status |
|---|---|---|---|---|
| `GET` | `/healthz` | — | `{"status": "ok", "service": "setlist-picker-api"}` | 200 |

## 5. Constants and thresholds

| Constant | Value | Rationale |
|---|---|---|
| `services/api` line length | 100 | ruff's default, matches FastAPI source style. |
| `mypy` config | `strict = true`, `disallow_any_explicit = false` | `Any` needed for JSON `dict[str, object]` shapes in BE-009. |
| `pytest-asyncio` mode | `auto` | All test functions become async-aware without per-function decoration. |
| `LOG_LEVEL` default | `INFO` | Quiet on prod, debug-able via env var. |
| Python version | `3.12.7` | Latest 3.12 patch; matches Render's available runtime. |
| FastAPI version | `>=0.110, <0.120` | Stable async middleware behavior; older has known async-context issues. |

## 6. Edge cases enumerated

| Case | Expected behavior |
|---|---|
| `uv sync` runs without a lockfile | Fail loud — `pyproject.toml` includes a generated `uv.lock`; commit it. |
| App starts with no `.env` file | `Settings()` uses defaults; no crash. |
| Structlog runs before `configure_logging` (e.g. in `Settings` validation) | OK — structlog falls back to stdlib `logging` which writes plain text. Acceptable for pre-config errors. |
| `/healthz` called concurrently from a smoke test | Idempotent; no shared state. |
| CI runs on a Python version other than 3.12 | Fail in `uv sync` (uv pins via `.python-version`). |
| `ruff check .` finds a violation in code added by a later ticket | Block the PR — this is the whole point of the gate. |
| `mypy --strict` warns about a missing return type hint in a future file | Block the PR. |
| Test file uses sync `def test_` without `pytest-asyncio` import | OK; sync tests are still supported by `asyncio_mode = auto`. |

## 7. Acceptable validation

**Tests that MUST exist (`services/api/tests/test_health.py`):**

| Test name | Assertion |
|---|---|
| `test_healthz_returns_200_and_status_ok` | `GET /healthz` → 200; body is `{"status": "ok", "service": "setlist-picker-api"}`. |
| `test_healthz_response_is_application_json` | Response `Content-Type` starts with `application/json`. |
| `test_create_app_returns_fresh_instance` | `create_app()` returns a new `FastAPI` instance per call (no global mutation). |

**CI gate (`.github/workflows/api.yml` must run in this order):**

1. `uv sync --frozen` — fails on a drifted lockfile.
2. `uv run ruff check .` — must report 0 violations.
3. `uv run ruff format --check .` — must report 0 changes needed.
4. `uv run mypy --strict .` — must report 0 errors.
5. `uv run pytest -x --tb=short` — must be green.

**Manual QA:**

1. `cd services/api && uv sync && uv run uvicorn app.main:app --reload`.
2. `curl -s http://localhost:8000/healthz | jq` — body matches the test assertion.
3. `curl -s http://localhost:8000/openapi.json | jq '.paths."/healthz"'` — confirms `GET /healthz` is in the OpenAPI schema.
4. Stop the server with Ctrl+C — no warnings about unclosed connections.

**Structured-log lines emitted on success:**

| Event | Fields | Trigger |
|---|---|---|
| `app.startup` | `env`, `log_level`, `version` | FastAPI lifespan startup. |
| `app.shutdown` | — | FastAPI lifespan shutdown. |

**Failure modes:**

- Port 8000 already in use → uvicorn exits with code 1. User-facing: error in terminal; no UI surface yet.
- Bad `.env` line → `Settings()` raises `pydantic.ValidationError` at startup; uvicorn exits with traceback.

## 8. Out of scope

| Item | Where it lives |
|---|---|
| Database connection / SQLAlchemy setup | BE-002. |
| Alembic config | BE-002. |
| JWT middleware | BE-003. |
| Render deploy config | BE-011. |
| Request-id middleware | BE-002 (added with the DB dependency). |
| CORS / trusted-hosts | BE-011 (Render-specific config). |
| Dockerfile | BE-011. |

## 9. Structured-log events

| Event tag | Fields | When |
|---|---|---|
| `app.startup` | `env: str`, `log_level: str`, `version: str` | App start. |
| `app.shutdown` | — | App stop. |

No request-scoped logging in this ticket — added in BE-002 with the request-id middleware.

## 10. Rollback plan

Revert the PR. `services/api/` disappears; CI workflow file disappears; nothing depends on this yet (it's the first ticket). No data loss because no data exists yet.
