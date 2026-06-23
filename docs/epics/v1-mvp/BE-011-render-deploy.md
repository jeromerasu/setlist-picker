# BE-011 — Render deploy (`render.yaml` + managed Postgres + `/healthz` smoke)

**Wave:** 1
**Type:** Infra
**Blocked by:** BE-001
**Blocks:** every endpoint that needs to be hit from a real device
**ADR references:** [ADR-001](../../decisions/ADR-001-tech-stack.md), [ARCHITECTURE.md § Hosting](../../ARCHITECTURE.md)

## 1. Problem statement

Local-only API is fine for tests; it doesn't help a phone on cellular. We need a Render web service + Render-managed Postgres provisioned, the FastAPI app deployed behind HTTPS, and `/healthz` reachable from the public internet so FE-102 can target a real URL.

## 2. Actual solution

Add `render.yaml` (Infrastructure-as-Code blueprint) at the repo root.

```yaml
services:
  - type: web
    name: setlist-picker-api
    env: python
    region: oregon
    plan: starter
    rootDir: services/api
    buildCommand: pip install uv && uv sync --frozen && uv run alembic upgrade head
    startCommand: uv run uvicorn app.main:app --host 0.0.0.0 --port $PORT --proxy-headers
    healthCheckPath: /healthz
    autoDeploy: true
    envVars:
      - key: DATABASE_URL
        fromDatabase:
          name: setlist-picker-db
          property: connectionString
      - key: JWT_SECRET
        generateValue: true
      - key: APPLE_BUNDLE_ID
        sync: false  # set manually in Render dashboard
      - key: GOOGLE_CLIENT_ID
        sync: false
      - key: SPOTIFY_CLIENT_ID
        sync: false
      - key: SPOTIFY_CLIENT_SECRET
        sync: false
      - key: LASTFM_API_KEY
        sync: false
      - key: ADMIN_TOKEN
        generateValue: true
      - key: LOG_LEVEL
        value: INFO

databases:
  - name: setlist-picker-db
    plan: starter
    region: oregon
    postgresMajorVersion: 16
```

Add CORS middleware (FastAPI `CORSMiddleware`) allowing the Expo dev origin during development. Production CORS = only the app's deep-link origin scheme. Add `TrustedHostMiddleware` allowing `*.onrender.com` and (eventually) the custom domain.

Add `services/api/Dockerfile`? No — Render's native `env: python` is sufficient and avoids a Docker maintenance burden. Document in the README.

`startCommand` includes `--proxy-headers` because Render's edge terminates TLS and forwards `X-Forwarded-Proto`. Without this flag, `request.url.scheme` would be `http`, which downstream code (OpenAPI server URL, redirect URLs) would render incorrectly.

`alembic upgrade head` runs at build time, not at startup. Reasoning: ensures deploys fail loud if a migration breaks; avoids racy multi-instance start.

## 3. Files to touch

| Path | Edit purpose |
|---|---|
| `render.yaml` | New file at repo root. |
| `services/api/app/main.py` | Wire CORS + TrustedHost middleware. |
| `services/api/app/config.py` | Add `cors_origins: list[str] = []`, `trusted_hosts: list[str] = ["*"]`. |
| `services/api/.env.example` | Add CORS and admin-token entries. |
| `services/api/README.md` | "Deploying to Render" section — link to `render.yaml`. |
| `docs/CODEBASE_GUIDE.md` | Add deploy section. |

## 4. Method signatures / new APIs

No new endpoints. CORS / TrustedHost are middleware:

```python
# app/main.py
def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    configure_logging(level=settings.log_level)
    app = FastAPI(title="setlist-picker", version="0.1.0")
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.trusted_hosts,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
        allow_credentials=False,
    )
    app.add_middleware(RequestIdMiddleware)
    app.include_router(health.router)
    # ... other routers
    return app
```

## 5. Constants and thresholds

| Constant | Value | Rationale |
|---|---|---|
| Region | `oregon` | Lowest p99 from West-coast iOS test devices; matches Render's default. |
| Plan | `starter` | Smallest tier with 24/7 uptime — sufficient for v1 launch traffic. Upgrade to `standard` post-launch if needed. |
| Postgres version | `16` | Latest stable; matches what BE-002 was developed against. |
| Health-check path | `/healthz` | Matches BE-001. |
| `--proxy-headers` | enabled | Render fronts TLS. |
| Auto-deploy | `true` | Every push to main deploys after CI green. |
| `JWT_SECRET` strategy | `generateValue: true` | Render generates a 64-byte random secret on first deploy; persisted in the env. |
| `ADMIN_TOKEN` strategy | `generateValue: true` | Used by BE-018's admin import endpoint. |

## 6. Edge cases enumerated

| Case | Expected behavior |
|---|---|
| Migration fails on a new deploy | Build fails; old deploy stays running. Render's default behavior — confirmed by reading their docs. |
| Render's edge sends a `Host: setlist-picker-api.onrender.com` header | TrustedHostMiddleware passes — `*.onrender.com` is in `trusted_hosts`. |
| Client hits the HTTP port (not HTTPS) | Render redirects to HTTPS at the edge. App never sees HTTP traffic. |
| Postgres connection lost mid-request | asyncpg raises `ConnectionDoesNotExistError`; FastAPI returns 500. Render's TCP health check still passes if `/healthz` succeeds (no DB read in `/healthz`). |
| `DATABASE_URL` rotates (Render does this on free-tier sometimes) | App reads from env at start; restart picks up the new URL. Render restarts on DB credential rotation automatically. |
| Multi-instance deploy (autoscale) | `alembic upgrade head` ran at build, not start — no race. |
| `JWT_SECRET` rotated | All existing JWTs become invalid; users re-login. No data loss. (Not done routinely.) |

## 7. Acceptable validation

**Deploy-time checks:**

1. Push to a branch → Render's preview environment provisions (if enabled) OR push to `main` → production deploy.
2. Read Render logs — `app.startup` event present, `db.engine_created` present.
3. `curl -sf https://setlist-picker-api.onrender.com/healthz` returns 200 with the expected body.
4. `psql $DATABASE_URL -c '\dt'` (from a local with the Render DB connection string) shows 13 tables.

**Tests (added to `services/api/tests/test_app_startup.py`):**

| Test name | Assertion |
|---|---|
| `test_app_starts_with_default_settings` | `create_app()` returns a FastAPI instance with the expected middleware stack. |
| `test_cors_middleware_present` | App middleware list includes `CORSMiddleware`. |
| `test_trusted_host_middleware_present` | App middleware list includes `TrustedHostMiddleware`. |
| `test_request_id_middleware_present` | App middleware list includes `RequestIdMiddleware`. |

**Manual QA:**

1. Open `https://setlist-picker-api.onrender.com/docs` — Swagger UI renders.
2. From Expo dev client running on physical phone (LAN-connected), confirm a fetch to `/healthz` succeeds.

**Structured-log lines:**

(All inherited from BE-001 + BE-002.)

**Failure modes:**

- Deploy fails on migration → Render shows the alembic stderr in build logs.
- Health check fails 3 times → Render keeps the previous deploy.
- Render Postgres tier exhausted → all DB ops return 500; the FE shows a network-error toast.

## 8. Out of scope

| Item | Where |
|---|---|
| Custom domain | Ops setup post-launch. |
| Sentry / error tracking | BACKLOG-014. |
| Log aggregation (e.g. Logtail) | Render's stdout JSON is enough for v1. |
| CDN for static assets | No static assets — Expo serves the mobile build. |
| Auto-scaling tuning | Default sufficient at v1 scale. |
| Backup / restore strategy beyond Render's daily snapshots | Acceptable for v1. |

## 9. Structured-log events

(See BE-001 + BE-002.)

## 10. Rollback plan

Render's "Previous deploys" dashboard lets us redeploy any prior commit. To roll back a bad migration: roll back the deploy (which reverts the binary), then run `alembic downgrade -1` against the Render DB manually via the Render CLI (`render psql`). Document the procedure in `docs/CODEBASE_GUIDE.md`.
