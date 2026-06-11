from pydantic import BaseModel, Field, field_validator


class SearchRunCreate(BaseModel):
    target_title: str = "AI Engineer"
    related_titles: list[str] = Field(default_factory=lambda: ["Machine Learning Engineer", "MLOps Engineer"])
    location: str = "United States"
    seniority: str = "all"
    limit: int = Field(default=25, ge=1, le=100000)
    source_limits: dict[str, int] = Field(default_factory=dict)
    date_range: str = "last_30_days"
    sources: list[str] = Field(default_factory=lambda: ["adzuna", "usajobs"])
    certification_sources: list[str] = Field(default_factory=lambda: ["seed_official"])
    output_format: str = "both"

    @field_validator("source_limits")
    @classmethod
    def validate_source_limits(cls, value: dict[str, int]) -> dict[str, int]:
        for source, limit in value.items():
            if limit < 1 or limit > 100000:
                raise ValueError(f"{source} source limit must be between 1 and 100000")
        return value


class SearchRunRead(BaseModel):
    id: int
    target_title: str
    location: str
    seniority: str
    limit: int
    sources: list[str]
    status: str
    summary: dict

    model_config = {"from_attributes": True}


class NormalizeSkillRequest(BaseModel):
    text: str
