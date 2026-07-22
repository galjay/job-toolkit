from pydantic import BaseModel, Field


class JDRequest(BaseModel):
    jd_text: str = Field(min_length=10, max_length=20_000)


class JDAnalysis(BaseModel):
    summary: str = Field(min_length=1, max_length=2_000)
    responsibilities: list[str] = Field(default_factory=list, max_length=30)
    hard_skills: list[str] = Field(default_factory=list, max_length=30)
    soft_skills: list[str] = Field(default_factory=list, max_length=30)
    education: str = Field(default="", max_length=500)
    experience: str = Field(default="", max_length=500)
    keywords: list[str] = Field(default_factory=list, max_length=50)
    preparation: list[str] = Field(default_factory=list, max_length=30)
