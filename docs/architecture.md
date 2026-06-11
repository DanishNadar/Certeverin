# Architecture

Certeverin is split into a FastAPI backend, a Next.js frontend, and shared evidence assets.

Backend flow:

1. A search run is created through the API or CLI.
2. Permissioned connectors return normalized job objects.
3. Job descriptions are cleaned and stored locally for analysis.
4. Skill extraction writes job-skill mentions with snippets and confidence.
5. Certification seed data is loaded from official-source metadata.
6. Scoring compares job-demand vectors with certification skill vectors.
7. The dashboard reads aggregate records and PDF export writes a university-ready report.

The database layer supports SQLite for the local MVP and PostgreSQL for production. Docker Compose includes PostgreSQL with pgvector and Redis so the project can grow into embedding search and background jobs.

