from pathlib import Path

from app.core.config import ROOT_DIR


def parse_source_items(inline_items: str | None, file_path: str | None) -> list[str]:
    values: list[str] = []
    values.extend(split_items(inline_items or ""))
    if file_path:
        path = Path(file_path)
        if not path.is_absolute():
            path = ROOT_DIR / path
        if path.exists():
            values.extend(split_items(path.read_text(encoding="utf-8")))
    seen = set()
    unique = []
    for value in values:
        normalized = normalize_item(value)
        if normalized and normalized not in seen:
            seen.add(normalized)
            unique.append(normalized)
    return unique


def split_items(text: str) -> list[str]:
    rows = []
    for line in text.splitlines():
        clean = line.split("#", 1)[0]
        rows.extend(part.strip() for part in clean.split(","))
    return rows


def normalize_item(value: str) -> str:
    value = value.strip()
    if not value:
        return ""
    if value.startswith("https://"):
        value = value.rstrip("/").split("/")[-1]
    return value
