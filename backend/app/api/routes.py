from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.entities import Certification, JobCertificationMatch, JobPosting, JobSearchRun, ReportExport
from app.nlp.skills import normalize_skill
from app.reports.pdf import generate_pdf
from app.schemas.api import NormalizeSkillRequest, SearchRunCreate, SearchRunRead
from app.scoring.certifications import score_certifications, skill_statistics
from app.services.pipeline import run_analysis
from app.services.seeds import seed_certifications

router = APIRouter(prefix="/api")


@router.post("/search-runs", response_model=SearchRunRead)
async def create_search_run(payload: SearchRunCreate, db: Session = Depends(get_db)):
    return await run_analysis(db, payload)


@router.get("/search-runs/{run_id}", response_model=SearchRunRead)
def get_search_run(run_id: int, db: Session = Depends(get_db)):
    run = db.get(JobSearchRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Search run not found")
    return run


@router.get("/search-runs/{run_id}/jobs")
def list_jobs(run_id: int, db: Session = Depends(get_db)):
    return db.query(JobPosting).filter_by(run_id=run_id).all()


@router.get("/search-runs/{run_id}/skills")
def list_skills(run_id: int, db: Session = Depends(get_db)):
    return skill_statistics(db, run_id)


@router.get("/search-runs/{run_id}/certifications")
def list_certifications_for_run(run_id: int, db: Session = Depends(get_db)):
    matches = db.query(JobCertificationMatch).filter_by(run_id=run_id).all()
    if not matches:
        return score_certifications(db, run_id)
    return score_certifications(db, run_id)


@router.get("/search-runs/{run_id}/analysis")
def analysis(run_id: int, db: Session = Depends(get_db)):
    return {"skills": skill_statistics(db, run_id), "jobs": db.query(JobPosting).filter_by(run_id=run_id).all()}


@router.post("/search-runs/{run_id}/generate-report")
def create_report(run_id: int, db: Session = Depends(get_db)):
    export = generate_pdf(db, run_id)
    return {"report_id": export.id, "download_url": f"/api/reports/{export.id}", "file_path": export.file_path}


@router.get("/reports/{report_id}")
def download_report(report_id: int, db: Session = Depends(get_db)):
    report = db.get(ReportExport, report_id)
    if not report or not Path(report.file_path).exists():
        raise HTTPException(status_code=404, detail="Report not found")
    return FileResponse(report.file_path, media_type="application/pdf", filename=Path(report.file_path).name)


@router.get("/certifications")
def certifications(db: Session = Depends(get_db)):
    return db.query(Certification).order_by(Certification.provider, Certification.certification_name).all()


@router.post("/certifications/refresh")
def refresh_certifications(db: Session = Depends(get_db)):
    seed_certifications(db)
    return {"status": "refreshed", "source": "seed_official_pages"}


@router.post("/skills/normalize")
def normalize(payload: NormalizeSkillRequest):
    return normalize_skill(payload.text)
