from datetime import datetime

import httpx

from app.connectors.base import JobConnector, NormalizedJob
from app.connectors.source_lists import parse_source_items
from app.core.config import get_settings


class LeverConnector(JobConnector):
    source_name = "lever"

    async def fetch(self, title: str, location: str, limit: int) -> list[NormalizedJob]:
        settings = get_settings()
        companies = parse_source_items(settings.lever_company_names, settings.lever_company_names_file)
        if not companies:
            return []
        jobs: list[NormalizedJob] = []
        async with httpx.AsyncClient(timeout=20) as client:
            for company in companies:
                skip = 0
                page_size = min(limit, 100)
                while len(jobs) < limit:
                    response = await client.get(
                        f"https://api.lever.co/v0/postings/{company}",
                        params={"mode": "json", "limit": page_size, "skip": skip},
                    )
                    response.raise_for_status()
                    rows = response.json()
                    if not rows:
                        break
                    for item in rows:
                        categories = item.get("categories") or {}
                        job_location = categories.get("location") or location
                        text = " ".join(
                            str(value or "")
                            for value in [
                                item.get("text"),
                                item.get("descriptionPlain"),
                                categories.get("team"),
                                categories.get("department"),
                                job_location,
                            ]
                        )
                        if title.lower() not in text.lower() and not any(part.lower() in text.lower() for part in title.split()):
                            continue
                        if location.lower() not in job_location.lower() and location.lower() != "united states":
                            continue
                        jobs.append(
                            NormalizedJob(
                                source="lever",
                                source_url=item.get("hostedUrl", ""),
                                job_id=str(item.get("id")),
                                title=item.get("text", "Unknown title"),
                                company=company,
                                location=job_location,
                                remote_status="remote" if "remote" in job_location.lower() else "unknown",
                                date_posted=str(item.get("createdAt") or ""),
                                salary_min=None,
                                salary_max=None,
                                employment_type=categories.get("commitment") or "unknown",
                                seniority=categories.get("level") or "unknown",
                                raw_description=item.get("descriptionPlain") or "",
                                cleaned_description=item.get("descriptionPlain") or "",
                                apply_url=item.get("applyUrl") or item.get("hostedUrl", ""),
                                fetched_at=datetime.utcnow(),
                            )
                        )
                        if len(jobs) >= limit:
                            return jobs
                    skip += len(rows)
        return jobs
