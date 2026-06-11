from dataclasses import dataclass
from datetime import datetime


@dataclass
class NormalizedJob:
    source: str
    source_url: str
    job_id: str
    title: str
    company: str
    location: str
    remote_status: str
    date_posted: str | None
    salary_min: float | None
    salary_max: float | None
    employment_type: str
    seniority: str
    raw_description: str
    cleaned_description: str
    apply_url: str
    fetched_at: datetime


class JobConnector:
    source_name = "base"

    async def fetch(self, title: str, location: str, limit: int) -> list[NormalizedJob]:
        raise NotImplementedError

