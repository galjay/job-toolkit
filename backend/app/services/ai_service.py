import asyncio
import json
from pathlib import Path
from typing import TypeVar
from urllib.parse import urlparse

import httpx
from pydantic import BaseModel, ValidationError

from app.core.config import settings
from app.core.errors import PublicError
from app.schemas.jd import JDAnalysis
from app.schemas.resume import WorkflowAnalysis


PROMPTS_DIR = Path(__file__).resolve().parents[2] / "prompts"
SchemaT = TypeVar("SchemaT", bound=BaseModel)


def extract_json(text: str) -> dict:
    candidate = text.strip()
    if candidate.startswith("```"):
        lines = candidate.splitlines()
        lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        candidate = "\n".join(lines).strip()
    start = candidate.find("{")
    end = candidate.rfind("}")
    if start < 0 or end < start:
        raise ValueError("JSON object not found")
    value = json.loads(candidate[start : end + 1])
    if not isinstance(value, dict):
        raise ValueError("JSON root must be an object")
    return value


class AIService:
    def __init__(self):
        self._semaphore = asyncio.Semaphore(max(1, settings.AI_MAX_CONCURRENCY))

    async def call_json(
        self,
        system_prompt: str,
        user_message: str,
        schema: type[SchemaT],
    ) -> SchemaT:
        current_message = user_message
        for attempt in range(2):
            raw = await self._request_text(system_prompt, current_message)
            try:
                return schema.model_validate(extract_json(raw))
            except (ValueError, json.JSONDecodeError, ValidationError):
                if attempt == 1:
                    raise PublicError(
                        502,
                        "ai_invalid_response",
                        "AI 返回格式不完整，请稍后重试",
                    )
                current_message = (
                    user_message
                    + "\n\n上一次回答格式不符合要求。请只返回符合系统约定的 JSON 对象。"
                )
        raise AssertionError("unreachable")

    async def _request_text(self, system_prompt: str, user_message: str) -> str:
        if not settings.text_ai_configured:
            raise PublicError(
                503,
                "ai_not_configured",
                "请先在 backend/.env 中配置 AI_API_KEY",
            )

        endpoint = _chat_endpoint(settings.AI_BASE_URL)
        payload = {
            "model": settings.AI_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
        }
        try:
            async with self._semaphore:
                async with httpx.AsyncClient(timeout=settings.AI_TIMEOUT_SECONDS) as client:
                    response = await client.post(
                        endpoint,
                        headers={"Authorization": f"Bearer {settings.text_api_key}"},
                        json=payload,
                    )
            if response.status_code in {401, 403}:
                raise PublicError(502, "ai_auth_error", "AI API Key 无效或无权使用该模型")
            if response.status_code in {402, 429}:
                raise PublicError(502, "ai_quota_error", "AI 额度不足或请求过于频繁")
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
        except PublicError:
            raise
        except httpx.TimeoutException as exc:
            raise PublicError(504, "ai_timeout", "AI 响应超时，请稍后重试") from exc
        except httpx.HTTPError as exc:
            raise PublicError(502, "ai_unavailable", "AI 服务暂时不可用") from exc
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise PublicError(502, "ai_invalid_response", "AI 返回格式不完整") from exc

    async def analyze_workflow(self, resume_text: str, jd_text: str) -> WorkflowAnalysis:
        prompt = _load_prompt("workflow")
        message = (
            "<resume_data>\n"
            + resume_text
            + "\n</resume_data>\n\n<job_description>\n"
            + jd_text
            + "\n</job_description>"
        )
        return await self.call_json(prompt, message, WorkflowAnalysis)

    async def analyze_jd(self, jd_text: str) -> JDAnalysis:
        prompt = _load_prompt("jd")
        message = "<job_description>\n" + jd_text + "\n</job_description>"
        return await self.call_json(prompt, message, JDAnalysis)


def _load_prompt(name: str) -> str:
    path = PROMPTS_DIR / name / "system.txt"
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        raise PublicError(500, "prompt_missing", "AI 提示词文件缺失") from exc


def _chat_endpoint(base_url: str) -> str:
    parsed = urlparse(base_url)
    is_local = parsed.hostname in {"localhost", "127.0.0.1", "::1"}
    allowed_schemes = {"http", "https"} if is_local else {"https"}
    if (
        parsed.scheme not in allowed_schemes
        or not parsed.hostname
        or parsed.username
        or parsed.password
    ):
        raise PublicError(500, "ai_invalid_config", "文本 AI 接口地址配置不安全")
    return base_url.rstrip("/") + "/chat/completions"
