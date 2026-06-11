from datetime import datetime

import httpx

from app.connectors.base import JobConnector, NormalizedJob
from app.core.config import get_settings


class AdzunaConnector(JobConnector):
    source_name = "adzuna"

    async def fetch(self, title: str, location: str, limit: int) -> list[NormalizedJob]:
        settings = get_settings()
        if not settings.adzuna_app_id or not settings.adzuna_app_key:
            return []
        per_page = 50
        jobs = []
        async with httpx.AsyncClient(timeout=20) as client:
            for page in range(1, (limit + per_page - 1) // per_page + 1):
                url = f"https://api.adzuna.com/v1/api/jobs/us/search/{page}"
                params = {
                    "app_id": settings.adzuna_app_id,
                    "app_key": settings.adzuna_app_key,
                    "what": title,
                    "where": location,
                    "results_per_page": min(per_page, limit - len(jobs)),
                    "content-type": "application/json",
                }
                response = await client.get(url, params=params)
                response.raise_for_status()
                results = response.json().get("results", [])
                if not results:
                    break
                for item in results:
                    description = item.get("description") or ""
                    jobs.append(
                        NormalizedJob(
                            source="adzuna",
                            source_url=item.get("redirect_url", ""),
                            job_id=str(item.get("id")),
                            title=item.get("title", "Unknown title"),
                            company=(item.get("company") or {}).get("display_name", "Unknown company"),
                            location=(item.get("location") or {}).get("display_name", location),
                            remote_status="remote" if "remote" in description.lower() else "unknown",
                            date_posted=item.get("created"),
                            salary_min=item.get("salary_min"),
                            salary_max=item.get("salary_max"),
                            employment_type=item.get("contract_time") or "unknown",
                            seniority="unknown",
                            raw_description=description,
                            cleaned_description=description,
                            apply_url=item.get("redirect_url", ""),
                            fetched_at=datetime.utcnow(),
                        )
                    )
                    if len(jobs) >= limit:
                        return jobs
        return jobs
