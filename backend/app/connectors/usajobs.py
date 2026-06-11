from datetime import datetime

import httpx

from app.connectors.base import JobConnector, NormalizedJob
from app.core.config import get_settings


class USAJobsConnector(JobConnector):
    source_name = "usajobs"

    async def fetch(self, title: str, location: str, limit: int) -> list[NormalizedJob]:
        settings = get_settings()
        if not settings.usa_jobs_email or not settings.usa_jobs_api_key:
            return []
        headers = {"User-Agent": settings.usa_jobs_email, "Authorization-Key": settings.usa_jobs_api_key}
        per_page = min(limit, 500)
        jobs = []
        async with httpx.AsyncClient(timeout=20) as client:
            for page in range(1, (limit + per_page - 1) // per_page + 1):
                params = {"Keyword": title, "LocationName": location, "ResultsPerPage": per_page, "Page": page}
                response = await client.get("https://data.usajobs.gov/api/search", headers=headers, params=params)
                response.raise_for_status()
                results = response.json().get("SearchResult", {}).get("SearchResultItems", [])
                if not results:
                    break
                for item in results:
                    desc = item.get("MatchedObjectDescriptor", {})
                    details = desc.get("UserArea", {}).get("Details", {})
                    text = " ".join(str(details.get(k, "")) for k in ("JobSummary", "MajorDuties", "Requirements"))
                    jobs.append(
                        NormalizedJob(
                            source="usajobs",
                            source_url=desc.get("PositionURI", ""),
                            job_id=desc.get("PositionID", ""),
                            title=desc.get("PositionTitle", "Unknown title"),
                            company=desc.get("OrganizationName", "US Federal Government"),
                            location=", ".join(l.get("LocationName", "") for l in desc.get("PositionLocation", [])),
                            remote_status="unknown",
                            date_posted=desc.get("PublicationStartDate"),
                            salary_min=(desc.get("PositionRemuneration") or [{}])[0].get("MinimumRange"),
                            salary_max=(desc.get("PositionRemuneration") or [{}])[0].get("MaximumRange"),
                            employment_type=desc.get("PositionSchedule", [{}])[0].get("Name", "unknown"),
                            seniority=desc.get("JobGrade", [{}])[0].get("Code", "unknown"),
                            raw_description=text,
                            cleaned_description=text,
                            apply_url=desc.get("ApplyURI", [""])[0],
                            fetched_at=datetime.utcnow(),
                        )
                    )
                    if len(jobs) >= limit:
                        return jobs
        return jobs
