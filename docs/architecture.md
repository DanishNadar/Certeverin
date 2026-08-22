# Architecture

Certeverin is split into a FastAPI backend (`backend/`), a Next.js dashboard (repository root), and shared evidence assets (`shared/`).

On Vercel both halves ship as one project: the dashboard is the Next.js build, and `api/index.py` mounts the same FastAPI app as a Python serverless function that all `/api/*` traffic is rewritten to.

Backend flow:

1. A search run is created through the API or CLI.
2. Permissioned connectors return normalized job objects.
3. Job descriptions are cleaned and stored locally for analysis.
4. Skill extraction writes job-skill mentions with snippets and confidence.
5. Certification seed data is loaded from official-source metadata.
6. Scoring compares job-demand vectors with certification skill vectors.
7. The dashboard reads aggregate records and PDF export writes a university-ready report.

The database layer supports SQLite for the local MVP and PostgreSQL for production. Serverless deployments require PostgreSQL: the function filesystem is read-only and per-instance, so generated PDFs are stored as bytes on `report_exports` rather than on disk. Docker Compose includes PostgreSQL with pgvector and Redis so the project can grow into embedding search and background jobs.

