from fastapi import APIRouter, Depends, File, Form, UploadFile

from app.core.config import settings
from app.schemas.photo import PortraitGenerationResponse, PortraitPromptRequest, PortraitPromptResponse
from app.services.photo_service import PhotoService


router = APIRouter(prefix="/api/photo", tags=["photo"])
_service = PhotoService()


def get_photo_service() -> PhotoService:
    return _service


@router.post("/prompt", response_model=PortraitPromptResponse)
async def build_portrait_prompt(
    request: PortraitPromptRequest,
    service: PhotoService = Depends(get_photo_service),
):
    return service.prompt_resource(request)


@router.post("/generate", response_model=PortraitGenerationResponse)
async def generate_portrait(
    file: UploadFile = File(...),
    prompt: str = Form(...),
    consent: bool = Form(False),
    service: PhotoService = Depends(get_photo_service),
):
    content = await file.read(settings.MAX_UPLOAD_BYTES + 1)
    return await service.generate(
        content,
        file.filename or "reference",
        file.content_type or "",
        prompt,
        consent,
    )
