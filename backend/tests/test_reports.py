import asyncio
from pathlib import Path

from app.db.session import SessionLocal, init_db
from app.reports.pdf import generate_pdf
from app.schemas.api import SearchRunCreate
from app.services.pipeline import run_analysis
from app.services.seeds import seed_all


def test_pdf_generation_creates_file():
    init_db()
    with SessionLocal() as db:
        seed_all(db)
        run = asyncio.run(run_analysis(db, SearchRunCreate(limit=5, sources=["demo"])))
        report = generate_pdf(db, run.id)
        assert Path(report.file_path).exists()
        assert Path(report.file_path).stat().st_size > 0

