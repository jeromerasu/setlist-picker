# setlist-picker-api

FastAPI backend for setlist-picker. Deployed to Render (see `render.yaml` at repo root).

## Local dev

```bash
uv sync
cp .env.example .env       # fill in secrets
uv run uvicorn app.main:app --reload
```

## Quality gates (must pass before every commit)

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy --strict .
uv run pytest -x --tb=short
```

## Migrations

```bash
uv run alembic upgrade head
uv run alembic downgrade -1
```

## Environment variables

See `.env.example` for the full list. Key vars:

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://postgres:dev@localhost/setlist` | asyncpg-scheme Postgres URL |
| `JWT_SECRET` | `change-me-in-production-32-bytes!` | HS256 signing key |
| `CORS_ORIGINS` | `[]` | JSON list of allowed CORS origins |
| `TRUSTED_HOSTS` | `["*"]` | JSON list of allowed Host header values |
| `APPLE_BUNDLE_ID` | `com.setlistpicker.app` | Apple Sign-In audience |
| `GOOGLE_CLIENT_ID` | `replace-with-google-client-id` | Google OAuth client ID |

## Render deploy

Managed via `render.yaml` at the repo root. Pushes to `main` auto-deploy.
