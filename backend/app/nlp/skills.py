import json
import re
from functools import lru_cache

from app.core.config import get_settings


SECTION_PATTERNS = {
    "required": re.compile(r"(required|requirements|required qualifications)[:\s]", re.I),
    "preferred": re.compile(r"(preferred|nice to have|preferred qualifications)[:\s]", re.I),
    "responsibilities": re.compile(r"(responsibilities|what you will do)[:\s]", re.I),
}


@lru_cache
def load_taxonomy() -> dict:
    path = get_settings().shared_dir / "skill_taxonomy" / "skills.json"
    return json.loads(path.read_text(encoding="utf-8"))


def normalize_skill(text: str) -> dict:
    needle = text.strip().lower()
    for skill in load_taxonomy()["skills"]:
        names = [skill["name"], *skill.get("aliases", [])]
        if needle in {name.lower() for name in names}:
            return {"input": text, "normalized": skill["name"], "category": skill["category"], "confidence": 0.95}
    return {"input": text, "normalized": text.strip(), "category": "Unknown", "confidence": 0.2}


def clean_text(text: str) -> str:
    cleaned = re.sub(r"<[^>]+>", " ", text or "")
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def detect_section(text: str, start: int) -> str:
    prefix = text[max(0, start - 180) : start]
    for section, pattern in SECTION_PATTERNS.items():
        if pattern.search(prefix):
            return section
    return "unknown"


def snippet_for(text: str, start: int, end: int) -> str:
    left = max(0, start - 90)
    right = min(len(text), end + 90)
    return text[left:right].strip()


def extract_skills(text: str) -> list[dict]:
    cleaned = clean_text(text)
    found: dict[str, dict] = {}
    for skill in load_taxonomy()["skills"]:
        terms = sorted([skill["name"], *skill.get("aliases", [])], key=len, reverse=True)
        for term in terms:
            pattern = re.compile(rf"(?<![A-Za-z0-9+#.]){re.escape(term)}(?![A-Za-z0-9+#.])", re.I)
            for match in pattern.finditer(cleaned):
                key = skill["name"].lower()
                section = detect_section(cleaned, match.start())
                confidence = 0.9 if section in {"required", "preferred"} else 0.8
                found[key] = {
                    "raw_text": match.group(0),
                    "normalized_skill": skill["name"],
                    "category": skill["category"],
                    "section": section,
                    "snippet": snippet_for(cleaned, match.start(), match.end()),
                    "confidence": confidence,
                }
    return list(found.values())

