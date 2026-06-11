import asyncio

import typer

from app.db.session import SessionLocal, init_db
from app.reports.pdf import generate_pdf
from app.schemas.api import SearchRunCreate
from app.scoring.certifications import score_certifications
from app.services.pipeline import run_analysis
from app.services.seeds import seed_all, seed_certifications

app = typer.Typer(help="Certeverin command line tools")


@app.callback()
def bootstrap():
    init_db()
    with SessionLocal() as db:
        seed_all(db)


@app.command("ingest-jobs")
def ingest_jobs(title: str = "AI Engineer", location: str = "United States", limit: int = 25):
    with SessionLocal() as db:
        run = asyncio.run(run_analysis(db, SearchRunCreate(target_title=title, location=location, limit=limit, sources=["adzuna", "usajobs"])))
        typer.echo(f"Created run {run.id} with {run.summary.get('jobs_analyzed')} jobs")


@app.command("extract-skills")
def extract_skills(run_id: int = typer.Option(..., "--run-id")):
    with SessionLocal() as db:
        from app.scoring.certifications import skill_statistics

        for row in skill_statistics(db, run_id)[:20]:
            typer.echo(f"{row['skill']}: {row['job_frequency']:.0%}")


@app.command("refresh-certs")
def refresh_certs():
    with SessionLocal() as db:
        seed_certifications(db)
    typer.echo("Certification catalog refreshed from seed data.")


@app.command("score-certs")
def score_certs(run_id: int = typer.Option(..., "--run-id")):
    with SessionLocal() as db:
        for row in score_certifications(db, run_id)[:10]:
            typer.echo(f"{row['score']:>5.1f}% {row['certification_name']}")


@app.command("export-report")
def export_report(run_id: int = typer.Option(..., "--run-id"), format: str = typer.Option("pdf", "--format")):
    if format != "pdf":
        raise typer.BadParameter("Only pdf is implemented in the MVP.")
    with SessionLocal() as db:
        report = generate_pdf(db, run_id)
        typer.echo(report.file_path)
