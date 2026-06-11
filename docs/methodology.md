# Methodology

Certeverin asks a practical funding question: which certifications validate skills that appear most often in target job postings?

The MVP uses transparent extraction:

- Dictionary and alias matching against `shared/skill_taxonomy/skills.json`.
- Section-aware weighting for required and preferred qualifications.
- Source URLs and short snippets for evidence review.
- Certification coverage from curated seed data with official URLs and status notes.

The recommendation score is configurable in `shared/scoring_weights.yaml`. Retired certifications are penalized and unknown statuses are surfaced instead of hidden.

