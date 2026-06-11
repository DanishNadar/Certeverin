from fastapi.testclient import TestClient

from app.main import app


def test_api_end_to_end():
    client = TestClient(app)
    response = client.post("/api/search-runs", json={"target_title": "AI Engineer", "limit": 5, "sources": ["demo"]})
    assert response.status_code == 200
    run_id = response.json()["id"]
    assert client.get(f"/api/search-runs/{run_id}/skills").json()
    certs = client.get(f"/api/search-runs/{run_id}/certifications").json()
    assert certs

