# Setup

## Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
uvicorn app.main:app
```

If you need auto-reload on WSL or a Windows-mounted path, force polling so the Rust file watcher does not crash:

```powershell
$env:WATCHFILES_FORCE_POLLING="true"
uvicorn app.main:app --reload
```

## Frontend

The Next.js app lives at the repository root.

```powershell
npm install
npm run dev
```

`next.config.ts` proxies `/api/*` to the local backend, so no `NEXT_PUBLIC_API_BASE` is needed. Point `API_PROXY_TARGET` elsewhere if uvicorn is not on `http://127.0.0.1:8000`.

## Tests

```powershell
cd backend
pytest
```

## Deploying to Vercel

See [deploy-vercel.md](deploy-vercel.md).

## Docker

```powershell
docker compose up
```

## Migrations

The MVP creates tables from SQLAlchemy metadata on startup. Production migration workflow:

```powershell
cd backend
alembic init alembic
alembic revision --autogenerate -m "initial schema"
alembic upgrade head
```
