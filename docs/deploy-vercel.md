# Deploying Certeverin to Vercel

Certeverin ships to Vercel as **one project**: the Next.js dashboard is the site,
and the FastAPI backend runs as a Python serverless function at `api/index.py`.
All `/api/*` traffic is rewritten to that function, so the browser only ever talks
to one origin and there is no CORS to configure.

```
repository root
├── app/ components/ charts/ lib/   Next.js dashboard
├── api/index.py                    Vercel Python function -> FastAPI
├── backend/app/                    the FastAPI package (unchanged)
├── shared/                         skill taxonomy, certification catalog, weights
├── requirements.txt                Python deps for the function
└── vercel.json                     function memory, timeout, bundled files
```

## 1. Create a Postgres database (required)

A Vercel function's filesystem is **read-only and per-instance**, so SQLite cannot
be used for anything that has to survive a request. Without `DATABASE_URL` the
deployment still boots, but it falls back to a throwaway SQLite file and
`/health` reports a warning.

The quickest option is Neon through the Vercel Marketplace:

1. Vercel dashboard → **Storage** → **Create Database** → **Neon** (Postgres).
2. Connect it to this project. Vercel injects `DATABASE_URL`, `POSTGRES_URL`,
   and friends into every environment automatically.

Any Postgres works — Neon, Supabase, Railway, RDS. Copy its connection string
into `DATABASE_URL` yourself if you are not using the Marketplace integration.

Certeverin normalizes whatever form the provider hands you:
`postgres://`, `postgresql://`, and `postgresql+psycopg://` are all accepted,
`sslmode=require` is added when missing, and provider-only query parameters
(`pgbouncer`, `supa`, …) are stripped before psycopg sees them.

**Use the pooled connection string** if your provider offers one. Serverless
instances open a connection per request, so the provider's pooler does the
pooling for you.

## 2. Push the repository

```powershell
git add -A
git commit -m "Prepare Vercel deployment"
git push origin main
```

`.env` is gitignored and stays local — the API keys in it must be re-entered as
Vercel environment variables in the next step.

## 3. Import the project into Vercel

1. [vercel.com/new](https://vercel.com/new) → import the repository.
2. **Framework Preset**: Next.js (auto-detected).
3. **Root Directory**: leave it at the repository root — do **not** point it at a
   subfolder. The Python function lives at the root and needs `backend/` and
   `shared/` next to it.
4. Leave Build Command, Output Directory, and Install Command on their defaults.

## 4. Set environment variables

Project → **Settings** → **Environment Variables**. Apply each to Production,
Preview, and Development.

| Variable | Required | Value |
| --- | --- | --- |
| `DATABASE_URL` | Yes | Postgres connection string (auto-set by the Neon integration) |
| `ADZUNA_APP_ID` | For Adzuna | Your Adzuna app id |
| `ADZUNA_APP_KEY` | For Adzuna | Your Adzuna app key |
| `USA_JOBS_EMAIL` | For USAJOBS | The email registered with USAJOBS |
| `USA_JOBS_API_KEY` | For USAJOBS | Your USAJOBS API key |
| `GREENHOUSE_BOARD_SLUGS_FILE` | For Greenhouse | `shared/job_sources/greenhouse_board_slugs.txt` |
| `GREENHOUSE_BOARD_SLUGS` | Optional | Comma-separated board slugs, overrides the file |
| `LEVER_COMPANY_NAMES_FILE` | For Lever | `shared/job_sources/lever_company_names.txt` |
| `LEVER_COMPANY_NAMES` | Optional | Comma-separated company slugs, overrides the file |
| `ALLOWED_ORIGINS` | No | Extra browser origins allowed to call the API cross-origin |

**Do not set `NEXT_PUBLIC_API_BASE`.** The dashboard calls the API same-origin
through the rewrite. Setting it points the browser somewhere else and breaks the
deployment.

A source with missing credentials is skipped rather than failing the run, and the
reason shows up in the dashboard's collection warning and in the PDF's source
table.

## 5. Deploy and verify

Deploy, then check in order:

1. `https://<your-app>.vercel.app/health` →
   `{"status":"ok","database":"postgres","serverless":true}`.
   A `warning` field means `DATABASE_URL` did not reach the function.
2. `https://<your-app>.vercel.app/api/certifications` → the 10 seeded
   certifications. The first call creates the schema and loads the seed data;
   it is slower than the rest.
3. Open the dashboard, run a search, then **Export PDF** and download it.

If the schema ever needs rebuilding after a database reset:

```powershell
curl -X POST https://<your-app>.vercel.app/api/admin/bootstrap
```

## Runtime limits to know about

- **Function timeout.** `vercel.json` requests `maxDuration: 300`. Hobby projects
  without Fluid Compute cap at 60 seconds, so a large multi-source run can be cut
  off. Connectors now run concurrently rather than one after another, which helps,
  but keep the per-source posting targets modest — the dashboard defaults to 50
  per source. Raise them for local runs where nothing times out.
- **Generated PDFs live in the database.** `report_exports.content` holds the
  bytes, because the instance that generated a report is usually not the instance
  that serves the download.
- **Cold starts.** The first request after a deploy creates tables and loads seed
  data. Afterwards it is two probe queries per instance.
- **Python version.** Vercel's Python runtime defaults to 3.12, which is what this
  project targets.

## Local development after this restructure

The Next.js app now lives at the repository root instead of `frontend/`.

```powershell
# terminal 1
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
uvicorn app.main:app

# terminal 2 (repository root)
npm install
npm run dev
```

`next.config.ts` proxies `/api/*` to `http://127.0.0.1:8000` in development, so
the dashboard behaves exactly as it does in production. Override the target with
`API_PROXY_TARGET` if uvicorn runs elsewhere.

To reproduce the deployed setup locally, run `vercel dev` from the repository
root after `npm i -g vercel`.

## Troubleshooting

**Every `/api/*` route returns 404.** The rewrite in `next.config.ts` did not
reach the Python function. Confirm `api/index.py` shows up in the deployment's
Functions tab.

**`RuntimeError: .../backend is missing from the function bundle`.** The
`includeFiles` glob in `vercel.json` did not match. The error message lists what
did get bundled; adjust `"includeFiles": "{backend,shared}/**"` accordingly.

**`FileNotFoundError` for `shared/skill_taxonomy/skills.json`.** Same cause —
`shared/` was not bundled.

**`sqlalchemy.exc.OperationalError` on the first request.** The database is
unreachable. Check that `DATABASE_URL` exists in the environment the deployment
runs in, and that the host allows connections from Vercel.

**Reports 404 on download.** Only affects runs created before this change, whose
`report_exports` rows have no stored bytes. Generate the report again.

**A run returns zero jobs.** The credentials for the selected sources are
missing. `/api/search-runs/{id}/analysis` and the dashboard warning name the
missing variables.
