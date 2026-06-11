from app.nlp.skills import extract_skills, normalize_skill


def test_extracts_and_normalizes_aliases():
    text = "Required: Python, Azure ML, K8s, Postgres, RAG, and vector DB experience."
    skills = {item["normalized_skill"] for item in extract_skills(text)}
    assert "Python" in skills
    assert "Azure Machine Learning" in skills
    assert "Kubernetes" in skills
    assert "PostgreSQL" in skills
    assert "RAG" in skills
    assert "Vector Databases" in skills


def test_normalize_skill():
    result = normalize_skill("Amazon SageMaker")
    assert result["normalized"] == "AWS SageMaker"

