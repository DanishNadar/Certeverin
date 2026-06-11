from datetime import datetime

import httpx

from app.connectors.base import JobConnector, NormalizedJob
from app.connectors.source_lists import parse_source_items
from app.core.config import get_settings


class GreenhouseConnector(JobConnector):
    source_name = "greenhouse"

    async def fetch(self, title: str, location: str, limit: int) -> list[NormalizedJob]:
        settings = get_settings()
        slugs = parse_source_items(settings.greenhouse_board_slugs, settings.greenhouse_board_slugs_file)
        if not slugs:
            return []
        jobs: list[NormalizedJob] = []
        async with httpx.AsyncClient(timeout=20) as client:
            for slug in slugs:
                response = await client.get(f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs", params={"content": "true"})
                response.raise_for_status()
                for item in response.json().get("jobs", []):
                    text = " ".join(str(item.get(key) or "") for key in ("title", "content", "location"))
                    if title.lower() not in text.lower() and not any(part.lower() in text.lower() for part in title.split()):
                        continue
                    job_location = (item.get("location") or {}).get("name", location)
                    if location.lower() not in job_location.lower() and location.lower() != "united states":
                        continue
                    jobs.append(
                        NormalizedJob(
                            source="greenhouse",
                            source_url=item.get("absolute_url", ""),
                            job_id=str(item.get("id")),
                            title=item.get("title", "Unknown title"),
                            company=slug,
                            location=job_location,
                            remote_status="remote" if "remote" in job_location.lower() else "unknown",
                            date_posted=item.get("updated_at"),
                            salary_min=None,
                            salary_max=None,
                            employment_type="unknown",
                            seniority="unknown",
                            raw_description=item.get("content") or "",
                            cleaned_description=item.get("content") or "",
                            apply_url=item.get("absolute_url", ""),
                            fetched_at=datetime.utcnow(),
                        )
                    )
                    if len(jobs) >= limit:
                        return jobs
        return jobs
