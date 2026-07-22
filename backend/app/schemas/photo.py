from typing import Literal

from pydantic import BaseModel


class PortraitPromptRequest(BaseModel):
    presentation: Literal["neutral", "masculine", "feminine"] = "neutral"
    outfit: Literal["dark_suit", "light_suit", "shirt"] = "dark_suit"
    background: Literal["white", "light_gray", "business_blue"] = "white"
    retouch: Literal["none", "light", "polished"] = "light"


class PortraitPromptResponse(BaseModel):
    prompt: str
    negative_prompt: str
    provider_enabled: bool
    usage_note: str


class PortraitGenerationResponse(BaseModel):
    image_data_url: str | None = None
    image_url: str | None = None
