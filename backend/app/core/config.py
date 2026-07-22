from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_DIR = Path(__file__).resolve().parents[2]
PROJECT_DIR = BACKEND_DIR.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(PROJECT_DIR / ".env", BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    PROJECT_NAME: str = "求职工具箱 API"
    VERSION: str = "1.0.0"

    AI_API_KEY: str = ""
    AI_BASE_URL: str = "https://api.deepseek.com/v1"
    AI_MODEL: str = "deepseek-chat"

    # Backward-compatible migration from the WorkBuddy scaffold.
    DEEPSEEK_API_KEY: str = ""

    IMAGE_API_KEY: str = ""
    IMAGE_BASE_URL: str = ""
    IMAGE_MODEL: str = ""

    AI_TIMEOUT_SECONDS: float = 60.0
    AI_MAX_CONCURRENCY: int = 2
    MAX_UPLOAD_BYTES: int = 8 * 1024 * 1024
    MAX_PDF_PAGES: int = 20
    MAX_DOCUMENT_CHARS: int = 20_000
    MAX_ARCHIVE_BYTES: int = 32 * 1024 * 1024

    CORS_ORIGINS: list[str] = [
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "http://127.0.0.1:4173",
        "http://localhost:4173",
    ]

    @property
    def text_api_key(self) -> str:
        return self.AI_API_KEY or self.DEEPSEEK_API_KEY

    @property
    def text_ai_configured(self) -> bool:
        key = self.text_api_key.strip()
        return bool(key and not key.startswith(("your-", "sk-your")))

    @property
    def image_ai_configured(self) -> bool:
        key = self.IMAGE_API_KEY.strip()
        return bool(
            key
            and not key.startswith(("your-", "sk-your"))
            and self.IMAGE_BASE_URL.strip()
            and self.IMAGE_MODEL.strip()
        )


settings = Settings()
