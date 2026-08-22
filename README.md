# Certeverin

Certeverin helps a university ML/AI club decide which AI, ML, data, and cloud certifications are worth funding by mapping job-posting skill demand to certification objectives.

The repo contains a working FastAPI backend, a Next.js dashboard, seed skill taxonomy, seed certification catalog, scoring weights, PDF export, tests, and live-source connectors. Live sources are modular and only use API or permissioned connectors.

## Quick Start

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
uvicorn app.main:app
```

On WSL or Windows-mounted paths, `uvicorn --reload` can crash inside the file watcher with `Cannot allocate memory`. Use the stable command above, or use polling reload:

```powershell
$env:WATCHFILES_FORCE_POLLING="true"
uvicorn app.main:app --reload
```

In another terminal, from the repository root:

```powershell
npm install
npm run dev
```

Open `http://localhost:3000`. The API runs at `http://127.0.0.1:8000`, and the
dashboard reaches it through the `/api/*` rewrite in `next.config.ts`.

## CLI Commands

From the repo root after installing backend dependencies:

```powershell
certeverin ingest-jobs --title "AI Engineer" --location "United States" --limit 25
certeverin extract-skills --run-id 1
certeverin score-certs --run-id 1
certeverin export-report --run-id 1 --format pdf
```

The generated PDF is written under `backend/generated_reports/`.

## Layout

```
app/ components/ charts/ lib/   Next.js dashboard (repository root)
api/index.py                    Vercel Python function -> FastAPI
backend/app/                    FastAPI package
shared/                         skill taxonomy, certification catalog, weights
```

## Environment

Copy `.env.example` to `.env` for local settings.

Required only for live sources:

- `ADZUNA_APP_ID`
- `ADZUNA_APP_KEY`
- `USA_JOBS_EMAIL`
- `USA_JOBS_API_KEY`

The default database is SQLite for local setup. Use `DATABASE_URL=postgresql+psycopg://...`
for PostgreSQL; `postgres://` and `postgresql://` strings from hosted providers are
accepted and normalized automatically.

`NEXT_PUBLIC_API_BASE` is no longer needed — the dashboard calls the API
same-origin. Set `API_PROXY_TARGET` only if uvicorn is not on `http://127.0.0.1:8000`.

## Deployment

Certeverin deploys to Vercel as a single project: the Next.js dashboard plus the
FastAPI backend as a Python serverless function. It needs a Postgres database,
because the function filesystem is read-only and per-instance.

See [docs/deploy-vercel.md](docs/deploy-vercel.md) for the full walkthrough.

## API

- `POST /api/search-runs`
- `GET /api/search-runs/{id}`
- `GET /api/search-runs/{id}/jobs`
- `GET /api/search-runs/{id}/skills`
- `GET /api/search-runs/{id}/certifications`
- `GET /api/search-runs/{id}/analysis`
- `POST /api/search-runs/{id}/generate-report`
- `GET /api/reports/{report_id}`
- `GET /api/certifications`
- `POST /api/certifications/refresh`
- `POST /api/skills/normalize`
- `GET /health` and `GET /api/health`
- `POST /api/admin/bootstrap`

## Scoring

Weights live in `shared/scoring_weights.yaml`.

Default formula:

```text
final_score =
0.30 job skill demand +
0.20 required skill coverage +
0.15 role alignment +
0.10 provider signal +
0.10 cost-benefit +
0.10 beginner accessibility +
0.05 evidence confidence
```

## Compliance Notes

Certeverin does not scrape LinkedIn. It uses API and permissioned connectors, stores source URLs, avoids republishing full job descriptions in reports, and includes limitations about source mix, sample size, recency, and confidence.

## Current MVP Coverage

Implemented:

- Database schema for runs, jobs, skills, certifications, matches, reports, logs, and model runs.
- Demo connector plus Adzuna and USAJOBS API connectors.
- Greenhouse and Lever connector stubs for permissioned company board configuration.
- Rule-based skill extraction and alias normalization.
- Certification seed data with official URLs and status notes.
- Job-posting-driven certification scoring.
- Dashboard with setup, executive summary, skills charts, certification ranking, skill explorer, and PDF export.
- CLI commands and tests.

Next improvements:

- Alembic revision generation against the SQLAlchemy models.
- Background worker execution with Celery/RQ for long live-source runs.
- Embedding-based alias matching and Hugging Face zero-shot category fallback.
- Human review dashboard persistence for approved/rejected extractions.
- Playwright HTML-to-PDF renderer for richer report charts.
