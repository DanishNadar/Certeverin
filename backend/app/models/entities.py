from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class JobSearchRun(Base):
    __tablename__ = "job_search_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    target_title: Mapped[str] = mapped_column(String(200))
    related_titles: Mapped[str] = mapped_column(Text, default="")
    location: Mapped[str] = mapped_column(String(200), default="United States")
    seniority: Mapped[str] = mapped_column(String(80), default="all")
    limit: Mapped[int] = mapped_column(Integer, default=50)
    date_range: Mapped[str] = mapped_column(String(80), default="last_30_days")
    sources: Mapped[list] = mapped_column(JSON, default=list)
    output_format: Mapped[str] = mapped_column(String(40), default="both")
    status: Mapped[str] = mapped_column(String(40), default="queued")
    summary: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    jobs: Mapped[list["JobPosting"]] = relationship(back_populates="run", cascade="all, delete-orphan")


class JobPosting(Base):
    __tablename__ = "job_postings"
    __table_args__ = (UniqueConstraint("run_id", "source", "job_id", name="uq_run_source_job"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("job_search_runs.id"))
    source: Mapped[str] = mapped_column(String(80))
    source_url: Mapped[str] = mapped_column(Text)
    job_id: Mapped[str] = mapped_column(String(200))
    title: Mapped[str] = mapped_column(String(250))
    company: Mapped[str] = mapped_column(String(250))
    location: Mapped[str] = mapped_column(String(250))
    remote_status: Mapped[str] = mapped_column(String(80), default="unknown")
    date_posted: Mapped[str | None] = mapped_column(String(80), nullable=True)
    salary_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    salary_max: Mapped[float | None] = mapped_column(Float, nullable=True)
    employment_type: Mapped[str] = mapped_column(String(100), default="unknown")
    seniority: Mapped[str] = mapped_column(String(80), default="unknown")
    raw_description: Mapped[str] = mapped_column(Text)
    cleaned_description: Mapped[str] = mapped_column(Text)
    apply_url: Mapped[str] = mapped_column(Text)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    run: Mapped[JobSearchRun] = relationship(back_populates="jobs")
    mentions: Mapped[list["JobSkillMention"]] = relationship(back_populates="job", cascade="all, delete-orphan")


class SkillCategory(Base):
    __tablename__ = "skill_categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    description: Mapped[str] = mapped_column(Text, default="")


class NormalizedSkill(Base):
    __tablename__ = "normalized_skills"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160), unique=True)
    category: Mapped[str] = mapped_column(String(120))
    aliases: Mapped[list] = mapped_column(JSON, default=list)


class SkillAlias(Base):
    __tablename__ = "skill_aliases"

    id: Mapped[int] = mapped_column(primary_key=True)
    alias: Mapped[str] = mapped_column(String(160), unique=True)
    normalized_skill_id: Mapped[int] = mapped_column(ForeignKey("normalized_skills.id"))


class ExtractedSkill(Base):
    __tablename__ = "extracted_skills"

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("job_search_runs.id"))
    raw_text: Mapped[str] = mapped_column(String(200))
    normalized_skill: Mapped[str] = mapped_column(String(160))
    category: Mapped[str] = mapped_column(String(120))
    confidence: Mapped[float] = mapped_column(Float, default=0.8)


class JobSkillMention(Base):
    __tablename__ = "job_skill_mentions"

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("job_search_runs.id"))
    job_id: Mapped[int] = mapped_column(ForeignKey("job_postings.id"))
    skill: Mapped[str] = mapped_column(String(160))
    category: Mapped[str] = mapped_column(String(120))
    section: Mapped[str] = mapped_column(String(80), default="unknown")
    snippet: Mapped[str] = mapped_column(Text)
    confidence: Mapped[float] = mapped_column(Float, default=0.85)

    job: Mapped[JobPosting] = relationship(back_populates="mentions")


class Certification(Base):
    __tablename__ = "certifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    certification_name: Mapped[str] = mapped_column(String(250), unique=True)
    provider: Mapped[str] = mapped_column(String(120))
    official_url: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(40), default="unknown")
    exam_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    cost: Mapped[float | None] = mapped_column(Float, nullable=True)
    duration_estimate: Mapped[str] = mapped_column(String(120), default="unknown")
    difficulty: Mapped[str] = mapped_column(String(80), default="unknown")
    target_role: Mapped[str] = mapped_column(String(160), default="AI/ML")
    skills_validated: Mapped[list] = mapped_column(JSON, default=list)
    tools_validated: Mapped[list] = mapped_column(JSON, default=list)
    cloud_platform: Mapped[str] = mapped_column(String(80), default="General")
    hands_on_level: Mapped[str] = mapped_column(String(80), default="unknown")
    employer_signal_strength: Mapped[float] = mapped_column(Float, default=0.5)
    source_last_checked: Mapped[str] = mapped_column(String(40), default="2026-06-10")
    notes: Mapped[str] = mapped_column(Text, default="")


class CertificationSkill(Base):
    __tablename__ = "certification_skills"

    id: Mapped[int] = mapped_column(primary_key=True)
    certification_id: Mapped[int] = mapped_column(ForeignKey("certifications.id"))
    skill: Mapped[str] = mapped_column(String(160))
    confidence: Mapped[float] = mapped_column(Float, default=0.8)


class CertificationSource(Base):
    __tablename__ = "certification_sources"

    id: Mapped[int] = mapped_column(primary_key=True)
    certification_id: Mapped[int] = mapped_column(ForeignKey("certifications.id"))
    source_url: Mapped[str] = mapped_column(Text)
    source_type: Mapped[str] = mapped_column(String(80), default="official")
    checked_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class JobCertificationMatch(Base):
    __tablename__ = "job_certification_matches"

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("job_search_runs.id"))
    certification_id: Mapped[int] = mapped_column(ForeignKey("certifications.id"))
    score: Mapped[float] = mapped_column(Float)
    score_breakdown: Mapped[dict] = mapped_column(JSON, default=dict)
    covered_skills: Mapped[list] = mapped_column(JSON, default=list)
    missing_top_skills: Mapped[list] = mapped_column(JSON, default=list)


class ReportExport(Base):
    __tablename__ = "report_exports"

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("job_search_runs.id"))
    file_path: Mapped[str] = mapped_column(Text)
    format: Mapped[str] = mapped_column(String(20), default="pdf")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class SourceLog(Base):
    __tablename__ = "source_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int | None] = mapped_column(ForeignKey("job_search_runs.id"), nullable=True)
    source: Mapped[str] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(80))
    message: Mapped[str] = mapped_column(Text)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ModelRun(Base):
    __tablename__ = "model_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int | None] = mapped_column(ForeignKey("job_search_runs.id"), nullable=True)
    model_name: Mapped[str] = mapped_column(String(200))
    task: Mapped[str] = mapped_column(String(120))
    metrics: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

