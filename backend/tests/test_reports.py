import asyncio
import re
from pathlib import Path

from app.core.config import get_settings
from app.db.session import SessionLocal, init_db
from app.reports.pdf import generate_pdf
from app.schemas.api import SearchRunCreate
from app.services.pipeline import run_analysis
from app.services.seeds import seed_all


def test_pdf_generation_creates_file(tmp_path, monkeypatch):
    monkeypatch.setattr(get_settings(), "reports_dir", tmp_path)
    init_db()
    with SessionLocal() as db:
        seed_all(db)
        run = asyncio.run(run_analysis(db, SearchRunCreate(limit=5, sources=["demo"])))
        report = generate_pdf(db, run.id)
        assert Path(report.file_path).exists()
        assert report.content is not None
        assert report.content.startswith(b"%PDF-")
        assert Path(report.file_path).read_bytes() == report.content
        # Guard against silently regressing to a short text dump. The visual
        # report intentionally spans decision, evidence, and method pages.
        assert len(re.findall(rb"/Type\s*/Page\b", report.content)) >= 8
