"""Vercel serverless entrypoint for the Certeverin FastAPI backend.

Vercel builds every file under `api/` as a serverless function. The rewrite in
`next.config.ts` sends all `/api/*` traffic here; the rewrite only selects the
function, so the ASGI app still receives the original request path and the routes
defined in `backend/app/api/routes.py` match as-is.

`vercel.json` supplies the function's memory, timeout, and the includeFiles glob
that bundles `backend/` and `shared/` alongside this file.
"""

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if not BACKEND_DIR.is_dir():
    # Turns an opaque ModuleNotFoundError into something actionable.
    siblings = sorted(entry.name for entry in BACKEND_DIR.parent.iterdir())
    raise RuntimeError(
        f"{BACKEND_DIR} is missing from the function bundle. Check the includeFiles "
        f"glob in vercel.json. Bundle contains: {siblings}"
    )
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.main import app  # noqa: E402

__all__ = ["app"]
