import asyncio

from app.db.session import SessionLocal, init_db
from app.schemas.api import SearchRunCreate
from app.scoring.certifications import score_certifications, skill_statistics
from app.services.pipeline import run_analysis
from app.services.seeds import seed_all


def test_pipeline_scores_certifications():
    init_db()
    with SessionLocal() as db:
        seed_all(db)
        run = asyncio.run(run_analysis(db, SearchRunCreate(limit=5, sources=["demo"])))
        skills = skill_statistics(db, run.id)
        certs = score_certifications(db, run.id)
        assert skills
        assert certs
        assert certs[0]["score"] > 0

