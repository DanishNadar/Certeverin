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

```powershell
cd frontend
npm install
npm run dev
```

## Tests

```powershell
cd backend
pytest
```

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
