from io import BytesIO
from pathlib import Path
from typing import IO

from reportlab.graphics.charts.barcharts import HorizontalBarChart, VerticalBarChart
from reportlab.graphics.shapes import Drawing
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.entities import JobPosting, JobSearchRun, ReportExport, SourceLog
from app.scoring.certifications import score_certifications, skill_statistics


def percent(value: float) -> str:
    return f"{value:.1f}%"


def generate_pdf(db: Session, run_id: int) -> ReportExport:
    run = db.get(JobSearchRun, run_id)
    if not run:
        raise ValueError("Search run not found")
    settings = get_settings()
    buffer = BytesIO()
    build_report(db, run, buffer)
    data = buffer.getvalue()
    output = settings.reports_dir / f"certeverin-run-{run_id}.pdf"
    try:
        output.write_bytes(data)
        file_path = str(output)
    except OSError:
        file_path = ""
    export = ReportExport(run_id=run_id, file_path=file_path, format="pdf", content=data)
    db.add(export)
    db.commit()
    db.refresh(export)
    return export


def build_report(db: Session, run: JobSearchRun, target: Path | str | IO[bytes]) -> None:
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(str(target) if isinstance(target, (Path, str)) else target, pagesize=letter, title="Certeverin Funding Recommendation")
    jobs = db.query(JobPosting).filter_by(run_id=run.id).all()
    logs = db.query(SourceLog).filter_by(run_id=run.id).all()
    skills = skill_statistics(db, run.id)
    certs = score_certifications(db, run.id)
    recommendations = run.summary.get("recommendations") or [recommendation_line(cert) for cert in certs[:5]]
    story = [
        Paragraph("Certification Funding Recommendation", styles["Title"]),
        Paragraph(f"Target role: {run.target_title}", styles["Heading2"]),
        Paragraph(f"Generated for ML Club funding review. Jobs analyzed: {len(jobs)}.", styles["Normal"]),
        Spacer(1, 16),
        Paragraph(run.summary.get("recommendation", ""), styles["BodyText"]),
    ]
    story.extend([Paragraph("Recommendation List", styles["Heading1"])])
    for item in recommendations:
        story.append(Paragraph(item, styles["BodyText"]))
    story.extend([
        PageBreak(),
        Paragraph("Executive Summary", styles["Heading1"]),
        Paragraph("This report maps job-market skill demand to certifications that validate those skills. The recommendation-strength percentage combines skill coverage, required-skill coverage, role alignment, provider signal, cost-benefit, beginner accessibility, and source confidence.", styles["BodyText"]),
        Spacer(1, 12),
        Paragraph("Skill Demand by Job Share", styles["Heading2"]),
        skill_bar_chart(skills[:12]),
        Spacer(1, 16),
        Paragraph("Certification Recommendation Strength", styles["Heading2"]),
        certification_bar_chart(certs),
    ])
    table_from_rows(story, ["Skill", "Category", "Job Share", "Required Share"], [[s["skill"], s["category"], f"{s['job_frequency']:.0%}", mention_share(s)] for s in skills])
    story.extend([
        PageBreak(),
        Paragraph("Methodology", styles["Heading1"]),
        Paragraph("Certeverin collects permissioned job data, stores source URLs, extracts skills with a transparent taxonomy, normalizes aliases, and scores certifications against demanded skills. Full job descriptions are used locally for analysis but are not republished.", styles["BodyText"]),
        Paragraph("Scoring formula: 30% job skill demand, 20% required skill coverage, 15% role alignment, 10% provider signal, 10% cost-benefit, 10% beginner accessibility, and 5% source confidence.", styles["BodyText"]),
        PageBreak(),
        Paragraph("Certification Comparison", styles["Heading1"]),
    ])
    table_from_rows(story, ["Certification", "Provider", "Status", "Strength", "Official URL"], [[c["certification_name"], c["provider"], c["status"], percent(c["score"]), c["official_url"]] for c in certs])
    story.extend([PageBreak(), Paragraph("Certification-to-Skill Coverage", styles["Heading1"])])
    table_from_rows(story, ["Certification", "Covered Demanded Skills", "Missing High-Demand Skills"], [[c["certification_name"], ", ".join(c["covered_skills"]) or "None in top set", ", ".join(c["missing_top_skills"]) or "None"] for c in certs])
    story.extend(
        [
            PageBreak(),
            Paragraph("Recommended Certification Path", styles["Heading1"]),
            Paragraph("1. Start with a foundational AI/cloud certification for broad vocabulary and confidence.", styles["BodyText"]),
            Paragraph("2. Fund the highest-ranked role-aligned AI/ML certification for students pursuing cloud AI roles.", styles["BodyText"]),
            Paragraph("3. Add a data or MLOps certification when postings emphasize pipelines, Kubernetes, and model operations.", styles["BodyText"]),
            PageBreak(),
            Paragraph("Limitations and Source Transparency", styles["Heading1"]),
            Paragraph("Recommendations are data-informed but not a guarantee of employment. Confidence depends on sample size, source mix, recency, and the completeness of certification objective pages.", styles["BodyText"]),
        ]
    )
    table_from_rows(story, ["Source", "Status", "Message"], [[log.source, log.status, log.message[:90]] for log in logs])
    doc.build(story)


def recommendation_line(cert: dict) -> str:
    covered = ", ".join(cert["covered_skills"][:5]) or "few current top skills"
    return f"{cert['certification_name']} ({percent(cert['score'])}) aligns with {covered}."


def mention_share(skill: dict) -> str:
    total = skill["required_mentions"] + skill["preferred_mentions"]
    if not total:
        return "0%"
    return f"{skill['required_mentions'] / total:.0%}"


def skill_bar_chart(skills: list[dict]) -> Drawing:
    drawing = Drawing(470, 220)
    chart = HorizontalBarChart()
    chart.x = 120
    chart.y = 20
    chart.height = 180
    chart.width = 310
    chart.data = [[round(skill["job_frequency"] * 100) for skill in skills]]
    chart.categoryAxis.categoryNames = [skill["skill"][:24] for skill in skills]
    chart.valueAxis.valueMin = 0
    chart.valueAxis.valueMax = 100
    chart.valueAxis.valueStep = 25
    chart.bars[0].fillColor = colors.HexColor("#0f766e")
    drawing.add(chart)
    return drawing


def certification_bar_chart(certs: list[dict]) -> Drawing:
    drawing = Drawing(470, 220)
    chart = VerticalBarChart()
    chart.x = 35
    chart.y = 45
    chart.height = 145
    chart.width = 390
    chart.data = [[cert["score"] for cert in certs]]
    chart.categoryAxis.categoryNames = [cert["provider"][:10] for cert in certs]
    chart.valueAxis.valueMin = 0
    chart.valueAxis.valueMax = 100
    chart.valueAxis.valueStep = 25
    chart.bars[0].fillColor = colors.HexColor("#10233f")
    drawing.add(chart)
    return drawing


def table_from_rows(story: list, headers: list, rows: list) -> None:
    data = [headers] + (rows or [["No data", *("" for _ in headers[1:])]])
    table = Table(data, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#10233f")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#c7d2fe")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ]
        )
    )
    story.extend([table, Spacer(1, 12)])
