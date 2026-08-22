import json

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.entities import Certification, CertificationSkill, NormalizedSkill, SkillAlias, SkillCategory


def seed_skills(db: Session) -> None:
    path = get_settings().shared_dir / "skill_taxonomy" / "skills.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    for category in data["categories"]:
        if not db.query(SkillCategory).filter_by(name=category["name"]).first():
            db.add(SkillCategory(name=category["name"], description=category.get("description", "")))
    db.flush()
    for item in data["skills"]:
        skill = db.query(NormalizedSkill).filter_by(name=item["name"]).first()
        if not skill:
            skill = NormalizedSkill(name=item["name"], category=item["category"], aliases=item.get("aliases", []))
            db.add(skill)
            db.flush()
        for alias in item.get("aliases", []):
            if not db.query(SkillAlias).filter_by(alias=alias.lower()).first():
                db.add(SkillAlias(alias=alias.lower(), normalized_skill_id=skill.id))
    db.commit()


def seed_certifications(db: Session) -> None:
    path = get_settings().shared_dir / "certification_seed_data" / "certifications.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    for item in data:
        cert = db.query(Certification).filter_by(certification_name=item["certification_name"]).first()
        if not cert:
            cert = Certification(**item)
            db.add(cert)
            db.flush()
        for skill in item.get("skills_validated", []):
            exists = db.query(CertificationSkill).filter_by(certification_id=cert.id, skill=skill).first()
            if not exists:
                db.add(CertificationSkill(certification_id=cert.id, skill=skill, confidence=0.85))
    db.commit()


def is_seeded(db: Session) -> bool:
    return bool(db.query(NormalizedSkill.id).first() and db.query(Certification.id).first())


def seed_all(db: Session, force: bool = False) -> None:
    """Load the skill taxonomy and certification catalog if they are missing.

    Two probe queries on the warm path keeps serverless cold starts cheap. A
    concurrent cold start can race us to the same rows, which surfaces as a
    unique-constraint error and means the work is already done.
    """
    if not force and is_seeded(db):
        return
    try:
        seed_skills(db)
        seed_certifications(db)
    except IntegrityError:
        db.rollback()

