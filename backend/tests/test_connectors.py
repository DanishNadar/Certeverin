import asyncio

from app.connectors.demo import DemoConnector


def test_demo_connector_returns_normalized_jobs():
    jobs = asyncio.run(DemoConnector().fetch("AI Engineer", "United States", 2))
    assert len(jobs) == 2
    assert jobs[0].source == "demo"
    assert jobs[0].raw_description
    assert jobs[0].source_url.startswith("https://")
