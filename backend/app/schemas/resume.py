from pydantic import BaseModel, Field


class ContactInfo(BaseModel):
    name: str = ""
    phone: str = ""
    email: str = ""
    city: str = ""
    target_role: str = ""
    links: list[str] = Field(default_factory=list)


class EducationItem(BaseModel):
    id: str = ""
    school: str = ""
    degree: str = ""
    major: str = ""
    start_date: str = ""
    end_date: str = ""
    highlights: list[str] = Field(default_factory=list)


class ExperienceItem(BaseModel):
    id: str = ""
    organization: str = ""
    role: str = ""
    location: str = ""
    start_date: str = ""
    end_date: str = ""
    bullets: list[str] = Field(default_factory=list)


class ProjectItem(BaseModel):
    id: str = ""
    name: str = ""
    role: str = ""
    start_date: str = ""
    end_date: str = ""
    bullets: list[str] = Field(default_factory=list)


class ResumeDocument(BaseModel):
    contact: ContactInfo = Field(default_factory=ContactInfo)
    summary: str = ""
    education: list[EducationItem] = Field(default_factory=list)
    experience: list[ExperienceItem] = Field(default_factory=list)
    projects: list[ProjectItem] = Field(default_factory=list)
    campus: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)


class MatchItem(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    evidence: str = Field(min_length=1, max_length=500)
    suggestion: str = Field(default="", max_length=500)


class RiskItem(BaseModel):
    section: str = Field(min_length=1, max_length=100)
    issue: str = Field(min_length=1, max_length=500)
    action: str = Field(min_length=1, max_length=500)


class RewriteSuggestion(BaseModel):
    id: str = Field(min_length=1, max_length=100)
    section: str = Field(min_length=1, max_length=100)
    original: str = Field(min_length=1, max_length=2_000)
    optimized: str = Field(min_length=1, max_length=2_000)
    reason: str = Field(min_length=1, max_length=500)
    keywords: list[str] = Field(default_factory=list, max_length=20)
    requires_user_input: bool = False


class WorkflowRequest(BaseModel):
    resume_text: str = Field(min_length=10, max_length=20_000)
    jd_text: str = Field(min_length=10, max_length=20_000)


class WorkflowAnalysis(BaseModel):
    match_score: int = Field(ge=0, le=100)
    target_role: str = Field(default="", max_length=200)
    strengths: list[MatchItem] = Field(default_factory=list, max_length=30)
    gaps: list[MatchItem] = Field(default_factory=list, max_length=30)
    risks: list[RiskItem] = Field(default_factory=list, max_length=30)
    suggestions: list[RewriteSuggestion] = Field(default_factory=list, max_length=50)
    resume: ResumeDocument


class ResumeExportRequest(BaseModel):
    template: str
    resume: ResumeDocument
    photo_data_url: str | None = None
