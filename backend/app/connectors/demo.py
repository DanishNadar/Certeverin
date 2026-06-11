from datetime import datetime, timedelta

from app.connectors.base import JobConnector, NormalizedJob


DEMO_JOBS = [
    {
        "title": "AI Engineer",
        "company": "Lakefront Health Analytics",
        "location": "Chicago, IL",
        "description": "Required qualifications: Python, SQL, PyTorch, Hugging Face, RAG, vector databases, AWS, SageMaker, Docker, FastAPI. Preferred qualifications: MLflow, Kubernetes, model monitoring, prompt engineering.",
    },
    {
        "title": "Machine Learning Engineer",
        "company": "Midwest Robotics Lab",
        "location": "Remote - United States",
        "description": "Required: Python, TensorFlow, Scikit-learn, computer vision, OpenCV, Docker, Kubernetes, CI/CD, AWS S3. Preferred: Bedrock, model evaluation, data drift, PostgreSQL.",
    },
    {
        "title": "MLOps Engineer",
        "company": "Northstar AI Platform",
        "location": "United States",
        "description": "Responsibilities include model serving, MLflow, Airflow, feature stores, Docker, Kubernetes, GitHub Actions, AWS, Azure Machine Learning, monitoring, and FastAPI. Required: Python, SQL, Spark.",
    },
    {
        "title": "Cloud AI Engineer",
        "company": "Prairie Cloud Systems",
        "location": "Remote",
        "description": "Required skills: Azure OpenAI, Azure AI Search, Azure Machine Learning, Python, RAG, embeddings, semantic search, prompt engineering, security governance. Preferred: Kubernetes, Terraform, CI/CD.",
    },
    {
        "title": "Data Scientist",
        "company": "Civic Data Works",
        "location": "Washington, DC",
        "description": "Required: Python, R, SQL, Pandas, NumPy, Scikit-learn, statistics, model evaluation, data visualization. Preferred: Google Cloud, BigQuery, Vertex AI, dbt, Spark.",
    },
]


class DemoConnector(JobConnector):
    source_name = "demo"

    async def fetch(self, title: str, location: str, limit: int) -> list[NormalizedJob]:
        rows = DEMO_JOBS[:limit]
        jobs: list[NormalizedJob] = []
        for index, row in enumerate(rows, start=1):
            jobs.append(
                NormalizedJob(
                    source="demo",
                    source_url=f"https://example.edu/demo-jobs/{index}",
                    job_id=f"demo-{index}",
                    title=row["title"],
                    company=row["company"],
                    location=row["location"],
                    remote_status="remote" if "Remote" in row["location"] else "onsite_or_hybrid",
                    date_posted=(datetime.utcnow() - timedelta(days=index)).date().isoformat(),
                    salary_min=None,
                    salary_max=None,
                    employment_type="full-time",
                    seniority="entry_or_mid",
                    raw_description=row["description"],
                    cleaned_description=row["description"],
                    apply_url=f"https://example.edu/demo-jobs/{index}/apply",
                    fetched_at=datetime.utcnow(),
                )
            )
        return jobs

