import base64
import io
from urllib.parse import urlparse

import httpx
from PIL import Image

from app.core.config import settings
from app.core.errors import PublicError
from app.schemas.photo import PortraitPromptRequest, PortraitPromptResponse


PRESENTATIONS = {
    "neutral": "自然、专业、中性的职业气质",
    "masculine": "自然稳重的职业气质，保持原人物性别表达",
    "feminine": "自然干练的职业气质，保持原人物性别表达",
}
OUTFITS = {
    "dark_suit": "剪裁合体的深色商务西装与简洁衬衫",
    "light_suit": "剪裁合体的浅灰色商务西装与简洁衬衫",
    "shirt": "整洁合体的纯色商务衬衫",
}
BACKGROUNDS = {
    "white": "纯净均匀的白色背景",
    "light_gray": "干净克制的浅灰色背景",
    "business_blue": "均匀的商务蓝色背景",
}
RETOUCH = {
    "none": "不磨皮，只校正曝光和白平衡",
    "light": "轻度自然修饰皮肤与光线，保留毛孔、痣和真实纹理",
    "polished": "适度改善肤色和精神状态，但保持真实年龄与面部结构",
}

NEGATIVE_PROMPT = (
    "不要身份漂移，不要改变五官比例、脸型、年龄、肤色、族裔或性别表达；"
    "不要过度磨皮、塑料皮肤、浓妆、夸张瘦脸、大眼；不要畸形耳朵、牙齿、手或服装；"
    "不要首饰、帽子、杂乱头发、文字、Logo、水印、边框、插画感或虚假景深。"
)


class PhotoService:
    def prompt_resource(self, request: PortraitPromptRequest) -> PortraitPromptResponse:
        prompt = (
            "基于上传的正脸参考照片生成一张真实摄影风格的求职职业头像。"
            "保持参考照片中人物的面部身份特征、脸型、五官比例、真实年龄和自然神态；"
            f"呈现{PRESENTATIONS[request.presentation]}，穿着{OUTFITS[request.outfit]}；"
            f"使用{BACKGROUNDS[request.background]}；"
            "正面看向镜头，头部端正，肩部以上半身构图，证件照比例，柔和均匀棚拍光线，清晰对焦；"
            f"{RETOUCH[request.retouch]}。最终画面自然可信，适合简历、招聘网站和企业头像。"
        )
        return PortraitPromptResponse(
            prompt=prompt,
            negative_prompt=NEGATIVE_PROMPT,
            provider_enabled=settings.image_ai_configured,
            usage_note="AI 职业照适合求职头像，不保证符合身份证、护照等法定证件要求。",
        )

    async def generate(
        self,
        image: bytes,
        filename: str,
        content_type: str,
        prompt: str,
        consent: bool,
    ) -> dict:
        if not consent:
            raise PublicError(
                400,
                "photo_consent_required",
                "发送照片给第三方图片模型前必须明确同意",
            )
        normalized_image = _validate_and_normalize_image(image, content_type)
        if not settings.image_ai_configured:
            raise PublicError(
                503,
                "image_ai_not_configured",
                "图片模型尚未配置，请使用提示词资源模式",
            )
        if not prompt.strip() or len(prompt) > 4_000:
            raise PublicError(400, "invalid_photo_prompt", "职业照提示词长度无效")

        endpoint = _provider_endpoint(settings.IMAGE_BASE_URL)
        try:
            async with httpx.AsyncClient(timeout=settings.AI_TIMEOUT_SECONDS) as client:
                response = await client.post(
                    endpoint,
                    headers={"Authorization": f"Bearer {settings.IMAGE_API_KEY}"},
                    data={"model": settings.IMAGE_MODEL, "prompt": prompt, "size": "1024x1536"},
                    files={"image": ("reference.png", normalized_image, "image/png")},
                )
            if response.status_code in {401, 403}:
                raise PublicError(502, "image_ai_auth_error", "图片 API Key 无效或没有模型权限")
            if response.status_code in {402, 429}:
                raise PublicError(502, "image_ai_quota_error", "图片模型额度不足或请求过于频繁")
            response.raise_for_status()
            return _parse_provider_result(response.json())
        except PublicError:
            raise
        except httpx.TimeoutException as exc:
            raise PublicError(504, "image_ai_timeout", "图片生成超时，请使用提示词资源模式") from exc
        except httpx.HTTPError as exc:
            raise PublicError(502, "image_ai_unavailable", "图片模型暂时不可用，请使用提示词资源模式") from exc
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise PublicError(502, "image_ai_invalid_response", "图片模型返回格式不受支持") from exc


def _validate_and_normalize_image(content: bytes, content_type: str) -> bytes:
    if content_type not in {"image/jpeg", "image/png"} or len(content) > settings.MAX_UPLOAD_BYTES:
        raise PublicError(400, "invalid_photo", "仅支持 8 MB 以内的 JPG 或 PNG")
    if not (content.startswith(b"\x89PNG\r\n\x1a\n") or content.startswith(b"\xff\xd8\xff")):
        raise PublicError(400, "invalid_photo", "照片文件签名无效")
    try:
        source = Image.open(io.BytesIO(content))
        source.verify()
        source = Image.open(io.BytesIO(content))
        if source.width * source.height > 24_000_000:
            raise PublicError(400, "invalid_photo", "照片像素尺寸过大")
        source.thumbnail((2048, 2048))
        output = io.BytesIO()
        source.convert("RGB").save(output, format="PNG", optimize=True)
        return output.getvalue()
    except PublicError:
        raise
    except Exception as exc:
        raise PublicError(400, "invalid_photo", "照片无法读取") from exc


def _provider_endpoint(base_url: str) -> str:
    parsed = urlparse(base_url)
    is_local = parsed.hostname in {"localhost", "127.0.0.1", "::1"}
    if parsed.username or parsed.password or parsed.scheme not in ({"http", "https"} if is_local else {"https"}):
        raise PublicError(500, "image_ai_invalid_config", "图片接口地址配置不安全")
    return base_url.rstrip("/") + "/images/edits"


def _parse_provider_result(payload: dict) -> dict:
    item = payload["data"][0]
    if item.get("b64_json"):
        raw = base64.b64decode(item["b64_json"], validate=True)
        try:
            image = Image.open(io.BytesIO(raw))
            image.verify()
        except Exception as exc:
            raise ValueError("provider result is not a valid image") from exc
        media_types = {"PNG": "png", "JPEG": "jpeg", "WEBP": "webp"}
        media_type = media_types.get(image.format)
        if not media_type:
            raise ValueError("unsupported generated image")
        return {"image_data_url": f"data:image/{media_type};base64," + item["b64_json"]}
    if item.get("url"):
        parsed = urlparse(item["url"])
        if parsed.scheme != "https" or parsed.username or parsed.password:
            raise ValueError("unsafe image URL")
        return {"image_url": item["url"]}
    raise ValueError("missing image result")
