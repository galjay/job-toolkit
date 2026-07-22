from fastapi import APIRouter, File, UploadFile

from app.core.config import settings
from app.core.errors import PublicError
from app.services.document_service import parse_document


router = APIRouter(prefix="/api/documents", tags=["documents"])


@router.post("/parse")
async def parse_uploaded_document(file: UploadFile = File(...)):
    if not file.filename:
        raise PublicError(400, "missing_filename", "请选择要上传的文件")

    content = await file.read(settings.MAX_UPLOAD_BYTES + 1)
    return parse_document(file.filename, file.content_type or "", content)
