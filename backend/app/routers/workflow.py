from fastapi import APIRouter, Depends

from app.schemas.jd import JDAnalysis, JDRequest
from app.schemas.resume import WorkflowAnalysis, WorkflowRequest
from app.services.ai_service import AIService


router = APIRouter(prefix="/api", tags=["workflow"])
_service = AIService()


def get_ai_service() -> AIService:
    return _service


@router.post("/workflow/analyze", response_model=WorkflowAnalysis)
async def analyze_resume_for_job(
    request: WorkflowRequest,
    service: AIService = Depends(get_ai_service),
):
    return await service.analyze_workflow(request.resume_text, request.jd_text)


@router.post("/jd/analyze", response_model=JDAnalysis)
async def analyze_job_description(
    request: JDRequest,
    service: AIService = Depends(get_ai_service),
):
    return await service.analyze_jd(request.jd_text)
