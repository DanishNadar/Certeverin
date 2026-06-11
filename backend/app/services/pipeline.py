from datetime import datetime

from sqlalchemy.orm import Session

from app.connectors.adzuna import AdzunaConnector
from app.connectors.demo import DemoConnector
from app.connectors.greenhouse import GreenhouseConnector
from app.connectors.lever import LeverConnector
from app.connectors.usajobs import USAJobsConnector
from app.core.config import get_settings
from app.models.entities import ExtractedSkill, JobPosting, JobSearchRun, JobSkillMention, SourceLog
from app.nlp.skills import clean_text, extract_skills
from app.scoring.certifications import score_certifications, skill_statistics
from app.schemas.api import SearchRunCreate


CONNECTORS = {
    "demo": DemoConnector,
    "adzuna": AdzunaConnector,
    "usajobs": USAJobsConnector,
    "greenhouse": GreenhouseConnector,
    "lever": LeverConnector,
}


def source_limit(request: SearchRunCreate, source: str) -> int:
    return request.source_limits.get(source, request.limit)


async def run_analysis(db: Session, request: SearchRunCreate) -> JobSearchRun:
    settings = get_settings()
    total_limit = sum(source_limit(request, source) for source in request.sources) if request.sources else request.limit
    run = JobSearchRun(
        target_title=request.target_title,
        related_titles=", ".join(request.related_titles),
        location=request.location,
        seniority=request.seniority,
        limit=total_limit,
        date_range=request.date_range,
        sources=request.sources,
        output_format=request.output_format,
        status="running",
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    titles = [request.target_title, *request.related_titles]
    collected = []
    for source in request.sources:
        requested_limit = source_limit(request, source)
        connector_cls = CONNECTORS.get(source)
        if not connector_cls:
            db.add(SourceLog(run_id=run.id, source=source, status="skipped", message="Unknown source"))
            continue
        connector = connector_cls()
        if source == "demo":
            jobs = await connector.fetch(request.target_title, request.location, requested_limit)
            collected.extend(jobs)
            db.add(SourceLog(run_id=run.id, source=source, status="ok", message=f"Fetched {len(jobs)} of {requested_limit} requested labeled demo jobs"))
            continue
        if source == "adzuna" and (not settings.adzuna_app_id or not settings.adzuna_app_key):
            db.add(SourceLog(run_id=run.id, source=source, status="skipped", message="Missing ADZUNA_APP_ID or ADZUNA_APP_KEY."))
            continue
        if source == "usajobs" and (not settings.usa_jobs_email or not settings.usa_jobs_api_key):
            db.add(SourceLog(run_id=run.id, source=source, status="skipped", message="Missing USA_JOBS_EMAIL or USA_JOBS_API_KEY."))
            continue
        if source == "greenhouse" and not (settings.greenhouse_board_slugs or settings.greenhouse_board_slugs_file):
            db.add(SourceLog(run_id=run.id, source=source, status="skipped", message="Missing GREENHOUSE_BOARD_SLUGS or GREENHOUSE_BOARD_SLUGS_FILE. Use public board slugs from boards.greenhouse.io URLs."))
            continue
        if source == "lever" and not (settings.lever_company_names or settings.lever_company_names_file):
            db.add(SourceLog(run_id=run.id, source=source, status="skipped", message="Missing LEVER_COMPANY_NAMES or LEVER_COMPANY_NAMES_FILE. Use public company slugs from jobs.lever.co URLs."))
            continue
        for title in titles[:2]:
            try:
                title_limit = max(1, requested_limit // min(len(titles), 2))
                jobs = await connector.fetch(title, request.location, title_limit)
                collected.extend(jobs)
                status = "ok" if jobs else "empty"
                db.add(SourceLog(run_id=run.id, source=source, status=status, message=f"Fetched {len(jobs)} of {title_limit} requested jobs for {title}"))
            except Exception as exc:
                db.add(SourceLog(run_id=run.id, source=source, status="error", message=str(exc)))
    if not collected and "demo" not in request.sources:
        db.add(SourceLog(run_id=run.id, source="search", status="empty", message="No jobs were collected from selected live sources. Demo was not selected, so no fallback demo postings were used."))

    seen = set()
    for item in collected[:total_limit]:
        key = (item.source, item.job_id)
        if key in seen:
            continue
        seen.add(key)
        job_data = item.__dict__.copy()
        job_data["cleaned_description"] = clean_text(item.cleaned_description)
        job = JobPosting(**job_data, run_id=run.id)
        db.add(job)
        db.flush()
        for extracted in extract_skills(job.cleaned_description):
            db.add(
                ExtractedSkill(
                    run_id=run.id,
                    raw_text=extracted["raw_text"],
                    normalized_skill=extracted["normalized_skill"],
                    category=extracted["category"],
                    confidence=extracted["confidence"],
                )
            )
            db.add(
                JobSkillMention(
                    run_id=run.id,
                    job_id=job.id,
                    skill=extracted["normalized_skill"],
                    category=extracted["category"],
                    section=extracted["section"],
                    snippet=extracted["snippet"],
                    confidence=extracted["confidence"],
                )
            )
    db.commit()

    skills = skill_statistics(db, run.id)
    certs = score_certifications(db, run.id)
    run.status = "completed"
    run.completed_at = datetime.utcnow()
    demo_jobs_present = any(job.source == "demo" for job in db.query(JobPosting).filter_by(run_id=run.id).all())
    run.summary = {
        "jobs_analyzed": db.query(JobPosting).filter_by(run_id=run.id).count(),
        "top_skills": skills[:10],
        "top_certifications": certs,
        "recommendation": recommendation_text(skills, certs),
        "recommendations": recommendation_list(certs),
        "demo_labeled": demo_jobs_present,
        "demo_reason": demo_reason(request, demo_jobs_present),
        "collection_warning": collection_warning(db, run.id),
        "source_limits": {source: source_limit(request, source) for source in request.sources},
    }
    db.commit()
    db.refresh(run)
    return run


def demo_reason(request: SearchRunCreate, demo_jobs_present: bool) -> str | None:
    if not demo_jobs_present:
        return None
    if "demo" in request.sources:
        return "Demo source was selected, so labeled demo postings are included in this run."
    return "Labeled demo postings are included in this run."


def collection_warning(db: Session, run_id: int) -> str | None:
    logs = db.query(SourceLog).filter_by(run_id=run_id).all()
    if any(log.status == "empty" and log.source == "search" for log in logs):
        skipped = [log.message for log in logs if log.status == "skipped"]
        if skipped:
            return "No jobs were collected. " + " ".join(skipped)
        return "No jobs were collected from the selected sources. Try a broader title/location, lower seniority filtering, or confirm API access."
    return None


def recommendation_text(skills: list[dict], certs: list[dict]) -> str:
    if not certs:
        return "No certification recommendation is available yet because no certifications were scored."
    top = certs[0]
    top_skills = ", ".join(skill["skill"] for skill in skills[:5])
    return (
        f"Prioritize {top['certification_name']} first. Its recommendation strength is {top['score']:.1f}% for this sample because it covers "
        f"{len(top['covered_skills'])} of the most demanded skill clusters, while the leading job-market signals include {top_skills}."
    )


def recommendation_list(certs: list[dict]) -> list[str]:
    rows = []
    for index, cert in enumerate(certs[:5], start=1):
        covered = ", ".join(cert["covered_skills"][:5]) or "few currently detected top skills"
        rows.append(f"{index}. {cert['certification_name']} ({cert['score']:.1f}%): strongest fit around {covered}.")
    return rows
