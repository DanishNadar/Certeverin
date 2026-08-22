import yaml
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.entities import Certification, JobCertificationMatch, JobSkillMention


def load_weights() -> dict:
    path = get_settings().shared_dir / "scoring_weights.yaml"
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def skill_statistics(db: Session, run_id: int) -> list[dict]:
    mentions = db.query(JobSkillMention).filter_by(run_id=run_id).all()
    job_ids = {m.job_id for m in mentions}
    by_skill: dict[str, dict] = {}
    for mention in mentions:
        row = by_skill.setdefault(
            mention.skill,
            {"skill": mention.skill, "category": mention.category, "jobs": set(), "required": 0, "preferred": 0, "total": 0, "snippets": []},
        )
        row["jobs"].add(mention.job_id)
        row["total"] += 1
        if mention.section == "required":
            row["required"] += 1
        if mention.section == "preferred":
            row["preferred"] += 1
        if len(row["snippets"]) < 3:
            row["snippets"].append(mention.snippet)
    total_jobs = max(len(job_ids), 1)
    results = []
    for row in by_skill.values():
        frequency = len(row["jobs"]) / total_jobs
        results.append(
            {
                "skill": row["skill"],
                "category": row["category"],
                "job_count": len(row["jobs"]),
                "job_frequency": round(frequency, 3),
                "required_mentions": row["required"],
                "preferred_mentions": row["preferred"],
                "total_mentions": row["total"],
                # Postings that never label a requirements section land here.
                "unlabeled_mentions": row["total"] - row["required"] - row["preferred"],
                "confidence": round(min(0.99, 0.65 + frequency * 0.3), 2),
                "snippets": row["snippets"],
            }
        )
    return sorted(results, key=lambda item: (item["job_frequency"], item["required_mentions"]), reverse=True)


def score_certifications(db: Session, run_id: int) -> list[dict]:
    weights = load_weights()["final_score"]
    stats = skill_statistics(db, run_id)
    demand = {row["skill"]: row for row in stats}
    top_skills = [row["skill"] for row in stats[:15]]
    certs = db.query(Certification).all()
    rows = []
    db.query(JobCertificationMatch).filter_by(run_id=run_id).delete()
    for cert in certs:
        cert_skills = set(cert.skills_validated or []) | set(cert.tools_validated or [])
        covered = [skill for skill in top_skills if skill in cert_skills]
        demand_score = sum(demand[s]["job_frequency"] for s in covered) / max(len(top_skills), 1)
        required_score = sum(demand[s]["required_mentions"] for s in covered) / max(sum(d["required_mentions"] for d in demand.values()), 1)
        role_alignment = 0.9 if any(term in cert.target_role.lower() for term in ["ai", "ml", "data", "cloud"]) else 0.5
        cost_benefit = 0.9 if cert.cost and cert.cost <= 150 else 0.75 if cert.cost and cert.cost <= 250 else 0.55
        beginner = {"foundational": 0.95, "associate": 0.75, "intermediate": 0.65, "professional": 0.45}.get(cert.difficulty.lower(), 0.55)
        confidence = 0.9 if cert.status in {"active", "retiring"} else 0.45
        final = (
            weights["job_skill_demand_score"] * demand_score
            + weights["required_skill_coverage_score"] * required_score
            + weights["role_alignment_score"] * role_alignment
            + weights["certification_provider_signal_score"] * cert.employer_signal_strength
            + weights["cost_benefit_score"] * cost_benefit
            + weights["beginner_accessibility_score"] * beginner
            + weights["evidence_confidence_score"] * confidence
        )
        if cert.status == "retired":
            final *= 0.35
        breakdown = {
            "job_skill_demand_score": round(demand_score, 3),
            "required_skill_coverage_score": round(required_score, 3),
            "role_alignment_score": role_alignment,
            "provider_signal_score": cert.employer_signal_strength,
            "cost_benefit_score": cost_benefit,
            "beginner_accessibility_score": beginner,
            "evidence_confidence_score": confidence,
        }
        match = JobCertificationMatch(
            run_id=run_id,
            certification_id=cert.id,
            score=round(final * 100, 1),
            score_breakdown=breakdown,
            covered_skills=covered,
            missing_top_skills=[skill for skill in top_skills if skill not in cert_skills][:8],
        )
        db.add(match)
        rows.append(
            {
                "certification_id": cert.id,
                "certification_name": cert.certification_name,
                "provider": cert.provider,
                "official_url": cert.official_url,
                "status": cert.status,
                "cost": cert.cost,
                "difficulty": cert.difficulty,
                "score": match.score,
                "score_breakdown": breakdown,
                "covered_skills": covered,
                "missing_top_skills": match.missing_top_skills,
                "notes": cert.notes,
            }
        )
    db.commit()
    return sorted(rows, key=lambda item: item["score"], reverse=True)

