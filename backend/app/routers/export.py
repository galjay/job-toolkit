from urllib.parse import quote

from fastapi import APIRouter
from fastapi.responses import Response

from app.schemas.resume import ResumeExportRequest
from app.services.export_service import export_resume_docx, safe_download_name


router = APIRouter(prefix="/api/resume", tags=["resume"])
DOCX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


@router.post("/export/docx")
async def export_docx(request: ResumeExportRequest):
    content = export_resume_docx(
        request.resume,
        request.template,
        request.photo_data_url,
    )
    filename = safe_download_name(request.resume.contact.name)
    disposition = f"attachment; filename=resume.docx; filename*=UTF-8''{quote(filename)}"
    return Response(
        content=content,
        media_type=DOCX_MEDIA_TYPE,
        headers={"Content-Disposition": disposition},
    )
