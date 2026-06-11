from pathlib import Path
import sys

backend = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(backend))

from app.cli import app  # noqa: E402

app()
