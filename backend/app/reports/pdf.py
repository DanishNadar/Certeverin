"""Funding-committee PDF report.

The audience is a non-technical reviewer deciding which certifications to pay
for, so every number is paired with a chart or a plain-language caption that says
what it means. Charts are drawn directly with reportlab shapes rather than its
chart classes, which keeps labels, value badges, and truncation under our control.
"""

from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import IO
from xml.sax.saxutils import escape

from reportlab.graphics.charts.legends import Legend
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.shapes import Drawing, Rect, String
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.platypus import KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.entities import JobPosting, JobSearchRun, ReportExport, SourceLog
from app.scoring.certifications import score_certifications, skill_statistics


PAGE_WIDTH, PAGE_HEIGHT = letter
MARGIN = 54
CONTENT_WIDTH = PAGE_WIDTH - 2 * MARGIN

INK = colors.HexColor("#10233f")
ACCENT = colors.HexColor("#0f766e")
GOLD = colors.HexColor("#b45309")
MUTED = colors.HexColor("#64748b")
BORDER = colors.HexColor("#cbd5e1")
PANEL = colors.HexColor("#f1f5f9")
TRACK = colors.HexColor("#e2e8f0")
AMBER_BG = colors.HexColor("#fef3c7")
AMBER_LINE = colors.HexColor("#b45309")
CATEGORY_PALETTE = [
    ACCENT,
    INK,
    GOLD,
    colors.HexColor("#2563eb"),
    colors.HexColor("#7c3aed"),
    colors.HexColor("#0891b2"),
    colors.HexColor("#be123c"),
    colors.HexColor("#64748b"),
    colors.HexColor("#15803d"),
    colors.HexColor("#c2410c"),
]

STATUS_LABELS = {
    "active": "Currently offered",
    "retiring": "Being retired",
    "retired": "No longer offered",
    "unknown": "Status unconfirmed",
}

DIFFICULTY_LABELS = {
    "foundational": "Beginner friendly",
    "associate": "Some experience needed",
    "intermediate": "Some experience needed",
    "professional": "Advanced",
    "unknown": "Level unconfirmed",
}

# Dense comparison tables use one-word versions so rows stay a single line.
STATUS_SHORT = {"active": "Offered", "retiring": "Retiring", "retired": "Retired", "unknown": "Unconfirmed"}
DIFFICULTY_SHORT = {"foundational": "Beginner", "associate": "Intermediate", "intermediate": "Intermediate", "professional": "Advanced", "unknown": "Unknown"}


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


# --------------------------------------------------------------------------
# Styles and small text helpers
# --------------------------------------------------------------------------


def build_styles() -> dict:
    base = getSampleStyleSheet()
    styles = {
        "cover_eyebrow": ParagraphStyle("cover_eyebrow", parent=base["Normal"], fontName="Helvetica-Bold", fontSize=9, leading=12, textColor=colors.HexColor("#5eead4"), spaceAfter=0),
        "cover_title": ParagraphStyle("cover_title", parent=base["Normal"], fontName="Helvetica-Bold", fontSize=23, leading=27, textColor=colors.white),
        "cover_sub": ParagraphStyle("cover_sub", parent=base["Normal"], fontName="Helvetica", fontSize=10.5, leading=15, textColor=colors.HexColor("#cbd5e1")),
        "h1": ParagraphStyle("h1", parent=base["Normal"], fontName="Helvetica-Bold", fontSize=17, leading=21, textColor=INK, spaceBefore=2, spaceAfter=6),
        "h2": ParagraphStyle("h2", parent=base["Normal"], fontName="Helvetica-Bold", fontSize=12.5, leading=16, textColor=INK, spaceBefore=12, spaceAfter=4),
        "body": ParagraphStyle("body", parent=base["Normal"], fontName="Helvetica", fontSize=9.8, leading=14, textColor=colors.HexColor("#1e293b"), spaceAfter=6),
        "lead": ParagraphStyle("lead", parent=base["Normal"], fontName="Helvetica", fontSize=11, leading=16, textColor=colors.HexColor("#1e293b"), spaceAfter=8),
        "caption": ParagraphStyle("caption", parent=base["Normal"], fontName="Helvetica-Oblique", fontSize=8.6, leading=12, textColor=MUTED, spaceBefore=4, spaceAfter=10),
        "tile_label": ParagraphStyle("tile_label", parent=base["Normal"], fontName="Helvetica", fontSize=8, leading=10, textColor=MUTED),
        "tile_value": ParagraphStyle("tile_value", parent=base["Normal"], fontName="Helvetica-Bold", fontSize=17, leading=20, textColor=INK),
        "card_rank": ParagraphStyle("card_rank", parent=base["Normal"], fontName="Helvetica-Bold", fontSize=11.5, leading=15, textColor=INK),
        "card_score": ParagraphStyle("card_score", parent=base["Normal"], fontName="Helvetica-Bold", fontSize=17, leading=19, textColor=ACCENT, alignment=2),
        "card_score_label": ParagraphStyle("card_score_label", parent=base["Normal"], fontName="Helvetica", fontSize=7, leading=9, textColor=MUTED, alignment=2),
        "meta": ParagraphStyle("meta", parent=base["Normal"], fontName="Helvetica", fontSize=8.4, leading=12, textColor=MUTED),
        "small": ParagraphStyle("small", parent=base["Normal"], fontName="Helvetica", fontSize=8.4, leading=12, textColor=colors.HexColor("#1e293b")),
        "th": ParagraphStyle("th", parent=base["Normal"], fontName="Helvetica-Bold", fontSize=8.4, leading=11, textColor=colors.white),
        "td": ParagraphStyle("td", parent=base["Normal"], fontName="Helvetica", fontSize=8.4, leading=11.5, textColor=colors.HexColor("#1e293b")),
        "td_bold": ParagraphStyle("td_bold", parent=base["Normal"], fontName="Helvetica-Bold", fontSize=8.4, leading=11.5, textColor=INK),
        "bullet": ParagraphStyle("bullet", parent=base["Normal"], fontName="Helvetica", fontSize=9.8, leading=14, textColor=colors.HexColor("#1e293b"), leftIndent=14, firstLineIndent=-14, spaceAfter=5),
        "quote": ParagraphStyle("quote", parent=base["Normal"], fontName="Helvetica-Oblique", fontSize=8.6, leading=12.5, textColor=colors.HexColor("#334155"), leftIndent=10),
    }
    return styles


def para(text: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(escape(str(text or "")), style)


def fit_text(text: str, max_width: float, font: str = "Helvetica", size: float = 7.6) -> str:
    text = text or ""
    if stringWidth(text, font, size) <= max_width:
        return text
    while text and stringWidth(text + "...", font, size) > max_width:
        text = text[:-1]
    return text + "..."


def friendly_status(status: str) -> str:
    return STATUS_LABELS.get((status or "").lower(), status or "Unknown")


def friendly_difficulty(difficulty: str) -> str:
    return DIFFICULTY_LABELS.get((difficulty or "").lower(), difficulty or "Unknown")


def short_status(status: str) -> str:
    return STATUS_SHORT.get((status or "").lower(), status or "Unknown")


def short_difficulty(difficulty: str) -> str:
    return DIFFICULTY_SHORT.get((difficulty or "").lower(), difficulty or "Unknown")


def summarize_list(values: list[str], limit: int = 6, empty: str = "None") -> str:
    """Cap a comma list so table rows stay short and scannable."""
    if not values:
        return empty
    if len(values) <= limit:
        return ", ".join(values)
    return ", ".join(values[:limit]) + f", +{len(values) - limit} more"


def clean_snippet(text: str, limit: int = 240) -> str:
    """Trim a stored excerpt to whole words so the quote reads cleanly."""
    text = " ".join(str(text or "").split())
    if not text:
        return ""
    lead = ""
    if not text[0].isupper() and " " in text:
        text = text.split(" ", 1)[1]
        lead = "... "
    if len(text) > limit:
        return lead + text[:limit].rsplit(" ", 1)[0] + " ..."
    if not text.endswith((".", "!", "?", ";")):
        text = text.rsplit(" ", 1)[0] + " ..."
    return lead + text


def friendly_cost(cost) -> str:
    if cost is None:
        return "Price not published"
    return f"${cost:,.0f} exam fee"


def count_by(items: list, key) -> list[tuple[str, int]]:
    """Return stable, largest-first counts for categorical report charts."""
    counts: dict[str, int] = {}
    for item in items:
        label = str(key(item) or "Unknown")
        counts[label] = counts.get(label, 0) + 1
    return sorted(counts.items(), key=lambda item: (-item[1], item[0].lower()))


# --------------------------------------------------------------------------
# Drawing helpers
# --------------------------------------------------------------------------


def hbar_chart(rows: list[tuple[str, float, str]], label_width: float = 150, value_width: float = 46, row_height: float = 17, highlight_first: bool = False) -> Drawing:
    """Horizontal bars with the name on the left and the value on the right.

    `rows` is (label, value 0-100, display text).
    """
    rows = rows or [("No data", 0, "0%")]
    bar_width = CONTENT_WIDTH - label_width - value_width
    height = row_height * len(rows) + 6
    drawing = Drawing(CONTENT_WIDTH, height)
    for index, (label, value, display) in enumerate(rows):
        top = height - 3 - index * row_height
        bar_y = top - row_height + 4
        fill = ACCENT if (highlight_first and index == 0) else INK
        drawing.add(String(label_width - 8, bar_y + 2.5, fit_text(str(label), label_width - 12), fontName="Helvetica", fontSize=7.6, fillColor=INK, textAnchor="end"))
        drawing.add(Rect(label_width, bar_y, bar_width, 9.5, fillColor=TRACK, strokeColor=None))
        filled = max(0.0, min(1.0, (value or 0) / 100)) * bar_width
        if filled > 0:
            drawing.add(Rect(label_width, bar_y, filled, 9.5, fillColor=fill, strokeColor=None))
        drawing.add(String(label_width + bar_width + 6, bar_y + 2.5, display, fontName="Helvetica-Bold", fontSize=7.6, fillColor=INK, textAnchor="start"))
    return drawing


def stacked_bar_chart(rows: list[tuple[str, list[tuple[float, colors.Color]], str]], max_total: float, label_width: float = 150, value_width: float = 46, row_height: float = 17) -> Drawing:
    """Segmented bars, used for the required / preferred / unlabelled split."""
    rows = rows or [("No data", [], "0")]
    bar_width = CONTENT_WIDTH - label_width - value_width
    height = row_height * len(rows) + 6
    scale = bar_width / max(max_total, 1)
    drawing = Drawing(CONTENT_WIDTH, height)
    for index, (label, segments, display) in enumerate(rows):
        top = height - 3 - index * row_height
        bar_y = top - row_height + 4
        drawing.add(String(label_width - 8, bar_y + 2.5, fit_text(str(label), label_width - 12), fontName="Helvetica", fontSize=7.6, fillColor=INK, textAnchor="end"))
        drawing.add(Rect(label_width, bar_y, bar_width, 9.5, fillColor=TRACK, strokeColor=None))
        offset = label_width
        for value, color in segments:
            span = (value or 0) * scale
            if span > 0:
                drawing.add(Rect(offset, bar_y, span, 9.5, fillColor=color, strokeColor=None))
                offset += span
        drawing.add(String(label_width + bar_width + 6, bar_y + 2.5, display, fontName="Helvetica-Bold", fontSize=7.6, fillColor=INK, textAnchor="start"))
    return drawing


def swatch_legend(items: list[tuple[str, colors.Color]]) -> Drawing:
    drawing = Drawing(CONTENT_WIDTH, 14)
    x = 0.0
    for label, color in items:
        drawing.add(Rect(x, 3, 9, 9, fillColor=color, strokeColor=None))
        drawing.add(String(x + 13, 5.5, label, fontName="Helvetica", fontSize=7.8, fillColor=MUTED))
        x += 13 + stringWidth(label, "Helvetica", 7.8) + 20
    return drawing


def pie_chart(items: list[tuple[str, int]]) -> Drawing:
    items = items or [("No data", 1)]
    drawing = Drawing(CONTENT_WIDTH, 190)
    pie = Pie()
    pie.x = 30
    pie.y = 15
    pie.width = 160
    pie.height = 160
    pie.data = [value for _, value in items]
    pie.labels = None
    pie.slices.strokeColor = colors.white
    pie.slices.strokeWidth = 1
    for index in range(len(items)):
        pie.slices[index].fillColor = CATEGORY_PALETTE[index % len(CATEGORY_PALETTE)]
    drawing.add(pie)

    total = sum(value for _, value in items) or 1
    legend = Legend()
    legend.x = 235
    legend.y = 172
    legend.alignment = "right"
    legend.fontName = "Helvetica"
    legend.fontSize = 8.2
    legend.dxTextSpace = 6
    legend.deltay = 13
    legend.columnMaximum = 12
    legend.colorNamePairs = [
        (CATEGORY_PALETTE[index % len(CATEGORY_PALETTE)], f"{name} - {value} skills ({value / total:.0%})")
        for index, (name, value) in enumerate(items)
    ]
    drawing.add(legend)
    return drawing


def score_meter(value: float, width: float = 74) -> Drawing:
    drawing = Drawing(width, 9)
    drawing.add(Rect(0, 0, width, 7, fillColor=TRACK, strokeColor=None))
    filled = max(0.0, min(1.0, (value or 0) / 100)) * width
    if filled > 0:
        drawing.add(Rect(0, 0, filled, 7, fillColor=ACCENT, strokeColor=None))
    return drawing


# --------------------------------------------------------------------------
# Layout helpers
# --------------------------------------------------------------------------


def stat_tiles(items: list[tuple[str, str]], styles: dict) -> Table:
    cells = [[para(value, styles["tile_value"]) for _, value in items], [para(label, styles["tile_label"]) for label, _ in items]]
    width = CONTENT_WIDTH / len(items)
    table = Table(cells, colWidths=[width] * len(items))
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), PANEL),
                ("BOX", (0, 0), (-1, -1), 0.5, BORDER),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.white),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                ("TOPPADDING", (0, 0), (-1, 0), 12),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 0),
                ("TOPPADDING", (0, 1), (-1, 1), 0),
                ("BOTTOMPADDING", (0, 1), (-1, 1), 12),
            ]
        )
    )
    return table


def callout(text: str, styles: dict, tone: str = "amber") -> Table:
    background, line = (AMBER_BG, AMBER_LINE) if tone == "amber" else (PANEL, ACCENT)
    table = Table([[para(text, styles["small"])]], colWidths=[CONTENT_WIDTH])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), background),
                ("LINEBEFORE", (0, 0), (0, -1), 3, line),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                ("TOPPADDING", (0, 0), (-1, -1), 9),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
            ]
        )
    )
    return table


def data_table(headers: list[str], rows: list[list], col_widths: list[float], styles: dict, align_right: list[int] | None = None, padding: float = 5) -> Table:
    align_right = align_right or []
    head = [para(header, styles["th"]) for header in headers]
    body = rows or [[para("No data available for this run.", styles["td"])] + [para("", styles["td"]) for _ in headers[1:]]]
    table = Table([head] + body, colWidths=col_widths, repeatRows=1)
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), INK),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.4, BORDER),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), padding),
        ("BOTTOMPADDING", (0, 0), (-1, -1), padding),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, PANEL]),
    ]
    for column in align_right:
        style.append(("ALIGN", (column, 0), (column, -1), "RIGHT"))
    table.setStyle(TableStyle(style))
    return table


def page_footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(BORDER)
    canvas.setLineWidth(0.5)
    canvas.line(MARGIN, 44, PAGE_WIDTH - MARGIN, 44)
    canvas.setFont("Helvetica", 7.6)
    canvas.setFillColor(MUTED)
    canvas.drawString(MARGIN, 32, "Certeverin - Certification Funding Recommendation")
    canvas.drawRightString(PAGE_WIDTH - MARGIN, 32, f"Page {canvas.getPageNumber()}")
    canvas.restoreState()


# --------------------------------------------------------------------------
# Report sections
# --------------------------------------------------------------------------


def build_report(db: Session, run: JobSearchRun, target: Path | str | IO[bytes]) -> None:
    styles = build_styles()
    jobs = db.query(JobPosting).filter_by(run_id=run.id).all()
    logs = db.query(SourceLog).filter_by(run_id=run.id).all()
    skills = skill_statistics(db, run.id)
    certs = score_certifications(db, run.id)
    summary = run.summary or {}

    doc = SimpleDocTemplate(
        str(target) if isinstance(target, (Path, str)) else target,
        pagesize=letter,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=MARGIN,
        bottomMargin=64,
        title="Certeverin Funding Recommendation",
        author="Certeverin",
        subject=f"Certification funding recommendation for {run.target_title}",
    )

    story: list = []
    story += cover_section(run, jobs, skills, certs, summary, styles)
    story.append(PageBreak())
    story += recommendation_section(certs, summary, styles)
    story.append(PageBreak())
    story += demand_section(skills, jobs, styles)
    story.append(PageBreak())
    story += ranking_section(certs, styles)
    story.append(PageBreak())
    story += coverage_section(certs, styles)
    story.append(PageBreak())
    story += evidence_section(skills, jobs, styles)
    story.append(PageBreak())
    story += methodology_section(run, jobs, logs, summary, certs, styles)

    doc.build(story, onFirstPage=page_footer, onLaterPages=page_footer)


def cover_section(run: JobSearchRun, jobs: list, skills: list[dict], certs: list[dict], summary: dict, styles: dict) -> list:
    generated = (run.completed_at or run.created_at or datetime.utcnow()).strftime("%B %d, %Y")
    sources_used = sorted({job.source for job in jobs}) or list(run.sources or [])
    subtitle = f"Target role: {run.target_title}<br/>{run.location or 'United States'} &nbsp;|&nbsp; Seniority: {run.seniority or 'all'} &nbsp;|&nbsp; Prepared {generated}"

    header = Table(
        [[Paragraph("CERTEVERIN", styles["cover_eyebrow"])], [Paragraph("Certification Funding Recommendation", styles["cover_title"])], [Paragraph(subtitle, styles["cover_sub"])]],
        colWidths=[CONTENT_WIDTH],
    )
    header.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), INK),
                ("LEFTPADDING", (0, 0), (-1, -1), 22),
                ("RIGHTPADDING", (0, 0), (-1, -1), 22),
                ("TOPPADDING", (0, 0), (0, 0), 22),
                ("BOTTOMPADDING", (0, 0), (0, 0), 2),
                ("TOPPADDING", (0, 1), (0, 1), 2),
                ("BOTTOMPADDING", (0, 1), (0, 1), 6),
                ("TOPPADDING", (0, 2), (0, 2), 0),
                ("BOTTOMPADDING", (0, 2), (0, 2), 22),
            ]
        )
    )

    story = [header, Spacer(1, 14)]
    story.append(para("What this report answers", styles["h1"]))
    story.append(
        para(
            "Which certifications should the club spend its budget on? Certeverin read real job postings for this "
            "role, counted the skills employers ask for, then checked which certifications teach those same skills.",
            styles["lead"],
        )
    )
    story.append(
        stat_tiles(
            [
                ("Job postings read", f"{len(jobs):,}"),
                ("Skills detected", f"{len(skills):,}"),
                ("Certifications compared", f"{len(certs):,}"),
                ("Job sources used", f"{len(sources_used) or 0}"),
            ],
            styles,
        )
    )
    story.append(Spacer(1, 14))

    top = certs[0] if certs else None
    if top:
        story.append(para("The recommendation in one line", styles["h2"]))
        covered = ", ".join(top["covered_skills"][:6]) or "few of the top skills in this sample"
        card = Table(
            [
                [para("FUND THIS FIRST", styles["cover_eyebrow"]), para(percent(top["score"]), styles["card_score"])],
                [para(top["certification_name"], styles["card_rank"]), para("recommendation strength", styles["card_score_label"])],
                [para(f"{top['provider']} - {friendly_status(top['status'])} - {friendly_cost(top.get('cost'))} - {friendly_difficulty(top.get('difficulty'))}", styles["meta"]), ""],
                [para(f"It covers the demanded skills: {covered}.", styles["small"]), ""],
            ],
            colWidths=[CONTENT_WIDTH - 120, 120],
        )
        card.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), PANEL),
                    ("BOX", (0, 0), (-1, -1), 0.8, ACCENT),
                    ("SPAN", (0, 2), (1, 2)),
                    ("SPAN", (0, 3), (1, 3)),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 16),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 16),
                    ("TOPPADDING", (0, 0), (-1, 0), 14),
                    ("BOTTOMPADDING", (0, -1), (-1, -1), 14),
                    ("TOPPADDING", (0, 1), (-1, -1), 1),
                    ("BOTTOMPADDING", (0, 0), (-1, -2), 1),
                ]
            )
        )
        story.append(card)
        story.append(Spacer(1, 10))

    warning = summary.get("collection_warning")
    if warning:
        story.append(callout(f"Data note: {warning}", styles))
        story.append(Spacer(1, 8))
    if summary.get("demo_labeled"):
        story.append(callout(f"Demo data notice: {summary.get('demo_reason') or 'This run includes labeled demo postings.'} Treat the numbers as an illustration rather than live market evidence.", styles))
        story.append(Spacer(1, 8))

    story.append(para("How to read the pages that follow", styles["h2"]))
    guide = data_table(
        ["Section", "What it gives you"],
        [
            [para("Ranked recommendations", styles["td_bold"]), para("The shortlist to fund, with a strength score for each", styles["td"])],
            [para("What employers ask for", styles["td_bold"]), para("The skills postings request most, so you can see what the money buys", styles["td"])],
            [para("Full certification ranking", styles["td_bold"]), para("Every alternative that was considered, compared side by side", styles["td"])],
            [para("Skill coverage", styles["td_bold"]), para("What each certification covers and what it leaves untouched", styles["td"])],
            [para("Evidence", styles["td_bold"]), para("Real wording quoted from postings so the claims can be checked", styles["td"])],
            [para("Method and limits", styles["td_bold"]), para("How the score is built and what it cannot prove", styles["td"])],
        ],
        [155, CONTENT_WIDTH - 155],
        styles,
        padding=3.5,
    )
    story.append(KeepTogether([guide]))
    return story


def recommendation_section(certs: list[dict], summary: dict, styles: dict) -> list:
    story = [para("Ranked recommendations", styles["h1"])]
    story.append(
        para(
            summary.get("recommendation")
            or "No certification recommendation is available yet because no certifications were scored for this run.",
            styles["lead"],
        )
    )
    story.append(Spacer(1, 4))

    recommendations = [str(item).strip() for item in (summary.get("recommendations") or []) if str(item).strip()]
    if recommendations:
        story.append(para("The decision in plain language", styles["h2"]))
        for index, item in enumerate(recommendations, start=1):
            prefix, separator, remainder = item.partition(". ")
            if separator and prefix.isdigit():
                item = remainder
            story.append(Paragraph(f"<b>{index}.</b>&nbsp;&nbsp;{escape(item)}", styles["bullet"]))
        story.append(Spacer(1, 2))

    story.append(
        para(
            "Recommendation strength is a 0-100% blend of seven factors: a certification scores well only when it teaches "
            "in-demand skills and is affordable, current, and reachable for a student. The full breakdown is on the "
            "method page.",
            styles["caption"],
        )
    )
    story.append(Spacer(1, 4))

    if not certs:
        story.append(callout("No certifications were scored for this run, so there is nothing to rank yet.", styles))
        return story

    shortlist = certs[:5]
    for index, cert in enumerate(shortlist, start=1):
        story.append(recommendation_card(index, cert, styles))
        if index < len(shortlist):
            story.append(Spacer(1, 4))
    return story


def recommendation_card(index: int, cert: dict, styles: dict) -> KeepTogether:
    covered = summarize_list(cert["covered_skills"], 6, "None of the top skills in this sample")
    missing = summarize_list(cert["missing_top_skills"], 5)
    url = escape(cert.get("official_url") or "")
    name = escape(cert["certification_name"])
    title = f'{index}. <a href="{url}" color="#0f766e">{name}</a>' if url else f"{index}. {name}"

    rows = [
        [Paragraph(title, styles["card_rank"]), para(percent(cert["score"]), styles["card_score"])],
        [para(f"{cert['provider']} - {friendly_status(cert['status'])} - {friendly_cost(cert.get('cost'))} - {friendly_difficulty(cert.get('difficulty'))}", styles["meta"]), para("recommendation strength", styles["card_score_label"])],
        [score_meter(cert["score"], CONTENT_WIDTH - 152), ""],
        [para(f"Covers these in-demand skills: {covered}", styles["small"]), ""],
        [para(f"Does not cover: {missing}", styles["meta"]), ""],
    ]
    card = Table(rows, colWidths=[CONTENT_WIDTH - 120, 120])
    card.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.6, BORDER),
                ("BACKGROUND", (0, 0), (-1, -1), colors.white if index > 1 else PANEL),
                ("SPAN", (0, 2), (1, 2)),
                ("SPAN", (0, 3), (1, 3)),
                ("SPAN", (0, 4), (1, 4)),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 14),
                ("RIGHTPADDING", (0, 0), (-1, -1), 14),
                ("TOPPADDING", (0, 0), (-1, 0), 7),
                ("BOTTOMPADDING", (0, -1), (-1, -1), 7),
                ("TOPPADDING", (0, 1), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -2), 2),
                ("TOPPADDING", (0, 2), (-1, 2), 4),
                ("BOTTOMPADDING", (0, 2), (-1, 2), 4),
            ]
        )
    )
    return KeepTogether([card])


def demand_section(skills: list[dict], jobs: list, styles: dict) -> list:
    story = [para("What employers are asking for", styles["h1"])]
    story.append(
        para(
            f"Every skill below was found by reading {len(jobs):,} job postings for this role. The percentage is the "
            "share of those postings that mentioned the skill at least once, so 60% means three postings in five asked "
            "for it.",
            styles["lead"],
        )
    )

    top_skills = skills[:15]
    story.append(para("Most requested skills", styles["h2"]))
    story.append(
        hbar_chart(
            [(skill["skill"], skill["job_frequency"] * 100, f"{skill['job_frequency'] * 100:.0f}%") for skill in top_skills],
            highlight_first=True,
        )
    )
    story.append(para("Share of analyzed job postings that mention each skill. The top bar is the single most requested skill in this sample.", styles["caption"]))

    by_category: dict[str, int] = {}
    for skill in skills:
        by_category[skill["category"]] = by_category.get(skill["category"], 0) + 1
    category_items = sorted(by_category.items(), key=lambda item: item[1], reverse=True)[:10]
    if category_items:
        story.append(para("Which areas the demand falls into", styles["h2"]))
        story.append(pie_chart(category_items))
        story.append(para("Each slice is one skill area. A large slice means employers are asking for many different skills in that area, which is a signal that a certification covering the whole area is worth funding.", styles["caption"]))

    mention_rows = [skill for skill in skills[:12] if skill.get("total_mentions")]
    if mention_rows:
        story.append(PageBreak())
        story.append(para("Must-have versus nice-to-have", styles["h1"]))
        story.append(
            para(
                "Postings often split their wording into a required section and a preferred section. Where that split "
                "was detectable, the mentions are separated below. Grey means the posting never labelled the section, "
                "which is common and is not evidence either way.",
                styles["lead"],
            )
        )
        max_total = max(skill["total_mentions"] for skill in mention_rows)
        story.append(
            stacked_bar_chart(
                [
                    (
                        skill["skill"],
                        [
                            (skill["required_mentions"], INK),
                            (skill["preferred_mentions"], GOLD),
                            (skill.get("unlabeled_mentions", 0), colors.HexColor("#94a3b8")),
                        ],
                        str(skill["total_mentions"]),
                    )
                    for skill in mention_rows
                ],
                max_total=max_total,
            )
        )
        story.append(swatch_legend([("Required wording", INK), ("Preferred wording", GOLD), ("Section not labelled", colors.HexColor("#94a3b8"))]))
        story.append(para("Total number of times each skill was mentioned across all postings, split by the section it appeared in.", styles["caption"]))

    story.append(para("Every skill detected", styles["h2"]))
    story.append(
        data_table(
            ["Skill", "Area", "Postings", "Share", "Confidence"],
            [
                [
                    para(skill["skill"], styles["td_bold"]),
                    para(skill["category"], styles["td"]),
                    para(f"{skill['job_count']}", styles["td"]),
                    para(f"{skill['job_frequency']:.0%}", styles["td"]),
                    para(f"{skill['confidence']:.0%}", styles["td"]),
                ]
                for skill in skills
            ],
            [165, 150, 62, 55, CONTENT_WIDTH - 432],
            styles,
            align_right=[2, 3, 4],
            padding=4,
        )
    )
    story.append(para("Postings counts how many of the analyzed postings mentioned the skill. Confidence rises with that count, so a skill seen in only one posting is a weak signal.", styles["caption"]))
    return story


def ranking_section(certs: list[dict], styles: dict) -> list:
    story = [para("Full certification ranking", styles["h1"])]
    story.append(
        para(
            "Every certification in the catalog was scored against the same job-posting evidence, including the ones "
            "that did not make the shortlist. Showing the full list makes it clear what the recommendation was "
            "compared against.",
            styles["lead"],
        )
    )
    story.append(
        hbar_chart(
            [(cert["certification_name"], cert["score"], percent(cert["score"])) for cert in certs],
            label_width=215,
            row_height=15,
            highlight_first=True,
        )
    )
    story.append(para("Recommendation strength for each certification. The teal bar is the top pick.", styles["caption"]))

    providers = count_by(certs, lambda cert: cert.get("provider"))
    if providers:
        max_provider_count = max(count for _, count in providers)
        story.append(para("Certification providers reviewed", styles["h2"]))
        story.append(
            hbar_chart(
                [
                    (provider, count / max_provider_count * 100, f"{count} certification{'s' if count != 1 else ''}")
                    for provider, count in providers
                ],
                label_width=150,
                value_width=92,
                row_height=17,
            )
        )
        story.append(
            para(
                "This is a coverage check, not a quality score. It shows whether the comparison leaned too heavily on one provider.",
                styles["caption"],
            )
        )

    story.append(para("Side-by-side comparison", styles["h2"]))
    rows = []
    for index, cert in enumerate(certs, start=1):
        url = escape(cert.get("official_url") or "")
        name = escape(cert["certification_name"])
        linked = f'<a href="{url}" color="#0f766e">{name}</a>' if url else name
        rows.append(
            [
                para(str(index), styles["td"]),
                Paragraph(f"{linked}<br/><font size=7 color='#64748b'>{escape(cert['provider'])}</font>", styles["td_bold"]),
                para(short_status(cert["status"]), styles["td"]),
                para(friendly_cost(cert.get("cost")).replace(" exam fee", "").replace("Price not published", "Not published"), styles["td"]),
                para(short_difficulty(cert.get("difficulty")), styles["td"]),
                para(percent(cert["score"]), styles["td_bold"]),
            ]
        )
    story.append(
        data_table(
            ["#", "Certification", "Status", "Cost", "Level", "Strength"],
            rows,
            [24, 232, 62, 58, 68, CONTENT_WIDTH - 444],
            styles,
            align_right=[5],
            padding=3,
        )
    )
    story.append(para("Certification names link to the provider's official page. Offered means the exam is currently available. Costs are the published exam fee and exclude training material.", styles["caption"]))
    return story


def coverage_section(certs: list[dict], styles: dict) -> list:
    story = [para("What each certification covers, and what it misses", styles["h1"])]
    story.append(
        para(
            "A high score does not mean full coverage. This page names what each certification teaches and what it "
            "leaves untouched, so the club knows what a funded exam will not solve.",
            styles["lead"],
        )
    )
    story.append(
        data_table(
            ["Certification", "In-demand skills it covers", "High-demand skills it misses"],
            [
                [
                    Paragraph(f"{escape(cert['certification_name'])}<br/><font size=7 color='#64748b'>{escape(cert['provider'])}</font>", styles["td_bold"]),
                    para(summarize_list(cert["covered_skills"], 5, "None in the current top-skill set"), styles["td"]),
                    para(summarize_list(cert["missing_top_skills"], 5), styles["td"]),
                ]
                for cert in certs
            ],
            [150, 177, CONTENT_WIDTH - 327],
            styles,
            padding=3,
        )
    )
    story.append(para("Only the 15 most demanded skills in this run are used for coverage, so a certification may teach other useful material that does not appear here.", styles["caption"]))
    story.append(Spacer(1, 2))

    story.append(para("A suggested funding order", styles["h2"]))
    plan = [
        ("Start", "Fund a beginner-friendly AI or cloud certification first so members build vocabulary and confidence before an exam that costs more."),
        ("Then", "Fund the highest-ranked role-aligned certification on the shortlist for members who are actively applying for these roles."),
        ("Later", "Add a data or MLOps certification once postings in your region emphasise pipelines, containers, and model operations."),
    ]
    table = data_table(
        ["Step", "What to fund and why"],
        [[para(step, styles["td_bold"]), para(text, styles["td"])] for step, text in plan],
        [70, CONTENT_WIDTH - 70],
        styles,
        padding=3,
    )
    story.append(KeepTogether([table]))
    return story


def evidence_section(skills: list[dict], jobs: list, styles: dict) -> list:
    story = [para("Evidence from the job postings", styles["h1"])]
    story.append(
        para(
            "So the numbers can be checked rather than taken on trust, here is the actual wording that produced the "
            "top skill counts. Only short excerpts are quoted; full job descriptions are not republished.",
            styles["lead"],
        )
    )
    quoted = [skill for skill in skills[:10] if skill.get("snippets")]
    if not quoted:
        story.append(callout("No posting excerpts were captured for this run.", styles))
    else:
        for skill in quoted:
            block = [
                Paragraph(
                    f"{escape(skill['skill'])} <font size=8 color='#64748b'>- {skill['job_count']} postings ({skill['job_frequency']:.0%})</font>",
                    styles["h2"],
                )
            ]
            for snippet in skill["snippets"][:2]:
                text = clean_snippet(snippet)
                if not text:
                    continue
                block.append(Paragraph(f'"{escape(text)}"', styles["quote"]))
            story.append(KeepTogether(block))
            story.append(Spacer(1, 4))

    story.append(PageBreak())
    story.append(para("Postings behind the analysis", styles["h1"]))
    story.append(
        para(
            "These source records make the analysis auditable without copying full job descriptions. Open a role name "
            "to review the original posting when the source still has it available.",
            styles["lead"],
        )
    )
    posting_rows = []
    for job in jobs[:30]:
        url = escape(job.source_url or job.apply_url or "")
        title = escape(job.title or "Untitled role")
        linked_title = f'<a href="{url}" color="#0f766e">{title}</a>' if url else title
        posting_rows.append(
            [
                para(job.source, styles["td_bold"]),
                Paragraph(
                    f"{linked_title}<br/><font size=7 color='#64748b'>{escape(job.company or 'Company not listed')}</font>",
                    styles["td_bold"],
                ),
                para(job.location or "Not listed", styles["td"]),
                para(job.date_posted or "Not listed", styles["td"]),
            ]
        )
    story.append(
        data_table(
            ["Source", "Role and employer", "Location", "Posted"],
            posting_rows,
            [65, 215, 135, CONTENT_WIDTH - 415],
            styles,
            padding=3,
        )
    )
    if len(jobs) > len(posting_rows):
        story.append(
            para(
                f"Showing 30 of {len(jobs):,} analyzed postings to keep the report readable. Aggregate charts and scores use all {len(jobs):,} postings.",
                styles["caption"],
            )
        )
    else:
        story.append(para(f"All {len(jobs):,} analyzed postings are listed above.", styles["caption"]))
    return story


def methodology_section(run: JobSearchRun, jobs: list, logs: list, summary: dict, certs: list[dict], styles: dict) -> list:
    story = [para("How the score is built", styles["h1"])]
    story.append(
        para(
            "The recommendation strength is a weighted average of seven factors. The bars below show how much each "
            "factor can contribute to the final number.",
            styles["lead"],
        )
    )
    weights = [
        ("Job skill demand", 30, "How often the certification's skills appear in postings"),
        ("Required skill coverage", 20, "Whether those skills appear as must-haves"),
        ("Role alignment", 15, "Whether the certification targets this kind of role"),
        ("Employer recognition", 10, "How widely the provider is recognised"),
        ("Cost versus benefit", 10, "Exam price against what it validates"),
        ("Beginner accessibility", 10, "How reachable it is for a student"),
        ("Evidence confidence", 5, "Whether the certification is current and documented"),
    ]
    story.append(hbar_chart([(name, value * (100 / 30), f"{value}%") for name, value, _ in weights], label_width=160))
    story.append(para("Share of the final score contributed by each factor. Bar length is drawn relative to the largest factor.", styles["caption"]))
    story.append(
        data_table(
            ["Factor", "Weight", "What it measures"],
            [[para(name, styles["td_bold"]), para(f"{value}%", styles["td"]), para(text, styles["td"])] for name, value, text in weights],
            [150, 50, CONTENT_WIDTH - 200],
            styles,
            align_right=[1],
        )
    )

    if certs:
        top = certs[0]
        breakdown = top.get("score_breakdown") or {}
        labels = {
            "job_skill_demand_score": "Job skill demand",
            "required_skill_coverage_score": "Required skill coverage",
            "role_alignment_score": "Role alignment",
            "provider_signal_score": "Employer recognition",
            "cost_benefit_score": "Cost versus benefit",
            "beginner_accessibility_score": "Beginner accessibility",
            "evidence_confidence_score": "Evidence confidence",
        }
        rows = [(labels[key], float(breakdown.get(key, 0)) * 100, f"{float(breakdown.get(key, 0)) * 100:.0f}%") for key in labels if key in breakdown]
        if rows:
            story.append(para(f"Why {top['certification_name']} came first", styles["h2"]))
            story.append(hbar_chart(rows, label_width=160))
            story.append(para("How the top pick scored on each factor before weighting. A short bar shows where even the best option is weak.", styles["caption"]))

    story.append(PageBreak())
    story.append(para("Where the data came from", styles["h1"]))
    story.append(
        para(
            "Certeverin only uses job data from official APIs and permissioned company boards. It stores the source "
            "URL for every posting, analyses descriptions locally, and does not republish them.",
            styles["lead"],
        )
    )
    by_source: dict[str, int] = {}
    for job in jobs:
        by_source[job.source] = by_source.get(job.source, 0) + 1
    source_counts = sorted(by_source.items(), key=lambda item: (-item[1], item[0].lower()))
    if source_counts:
        max_source_count = max(count for _, count in source_counts)
        story.append(
            hbar_chart(
                [(source, count / max_source_count * 100, f"{count:,} postings") for source, count in source_counts],
                label_width=110,
                value_width=90,
                row_height=18,
            )
        )
        story.append(para("Posting count by source. Bar length is relative to the largest source in this run.", styles["caption"]))
    story.append(
        data_table(
            ["Source", "Postings", "Result", "Detail"],
            [
                [
                    para(log.source, styles["td_bold"]),
                    para(str(by_source.get(log.source, 0)), styles["td"]),
                    para(log.status, styles["td"]),
                    para(log.message, styles["td"]),
                ]
                for log in logs
            ]
            or [[para(source, styles["td_bold"]), para(str(count), styles["td"]), para("ok", styles["td"]), para("", styles["td"])] for source, count in by_source.items()],
            [82, 58, 62, CONTENT_WIDTH - 202],
            styles,
            align_right=[1],
        )
    )

    story.append(para("Run settings", styles["h2"]))
    story.append(
        data_table(
            ["Setting", "Value"],
            [
                [para("Target role", styles["td_bold"]), para(run.target_title, styles["td"])],
                [para("Related roles", styles["td_bold"]), para(run.related_titles or "None", styles["td"])],
                [para("Location", styles["td_bold"]), para(run.location or "United States", styles["td"])],
                [para("Seniority", styles["td_bold"]), para(run.seniority or "all", styles["td"])],
                [para("Date range", styles["td_bold"]), para(run.date_range or "last_30_days", styles["td"])],
                [para("Sources requested", styles["td_bold"]), para(", ".join(run.sources or []) or "None", styles["td"])],
                [para("Postings requested", styles["td_bold"]), para(f"{run.limit:,}", styles["td"])],
                [para("Postings analyzed", styles["td_bold"]), para(f"{len(jobs):,}", styles["td"])],
            ],
            [150, CONTENT_WIDTH - 150],
            styles,
        )
    )

    return story
