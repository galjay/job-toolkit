from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.errors import PublicError
from app.routers import documents, export, photo, workflow


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    docs_url="/docs",
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)

app.include_router(documents.router)
app.include_router(workflow.router)
app.include_router(export.router)
app.include_router(photo.router)


@app.exception_handler(PublicError)
async def public_error_handler(_request: Request, exc: PublicError):
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": exc.code, "message": exc.message},
    )


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "version": settings.VERSION}


@app.get("/api/config/status")
async def config_status():
    return {
        "text_ai": settings.text_ai_configured,
        "image_ai": settings.image_ai_configured,
    }
