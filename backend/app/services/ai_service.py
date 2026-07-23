import asyncio
from collections import Counter
import json
import re
import unicodedata
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


class RetryableAIResponseError(ValueError):
    pass


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
            try:
                raw = await self._request_text(system_prompt, current_message)
                return schema.model_validate(extract_json(raw))
            except (
                RetryableAIResponseError,
                ValueError,
                json.JSONDecodeError,
                ValidationError,
            ) as exc:
                if attempt == 1:
                    raise PublicError(
                        502,
                        "ai_invalid_response",
                        "AI 返回格式不完整，请稍后重试",
                    )
                current_message = (
                    user_message
                    + "\n\n上一次回答未通过结构校验，具体问题如下：\n"
                    + _validation_feedback(exc)
                    + "\n请修正这些字段，压缩不必要的表述，并重新返回完整的 JSON 对象。"
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
        if settings.AI_OUTPUT_TOKEN_PARAM != "none":
            payload[settings.AI_OUTPUT_TOKEN_PARAM] = settings.AI_MAX_OUTPUT_TOKENS
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
            choice = response.json()["choices"][0]
            if not isinstance(choice, dict):
                raise RetryableAIResponseError("AI response choice was invalid")
            message = choice["message"]
            if not isinstance(message, dict):
                raise RetryableAIResponseError("AI response message was invalid")
            finish_reason = choice.get("finish_reason")
            if finish_reason == "content_filter" or message.get("refusal"):
                raise PublicError(
                    502,
                    "ai_response_blocked",
                    "AI 未能处理这份内容，请检查材料后重试",
                )
            if finish_reason == "length":
                raise RetryableAIResponseError("AI response was truncated")
            content = message.get("content")
            if not isinstance(content, str) or not content.strip():
                raise RetryableAIResponseError("AI response content was empty")
            return content
        except (PublicError, RetryableAIResponseError):
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
        analysis = await self.call_json(prompt, message, WorkflowAnalysis)
        return _ground_workflow_analysis(analysis, resume_text, jd_text)

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


def _validation_feedback(exc: Exception) -> str:
    if isinstance(exc, ValidationError):
        issues = []
        for error in exc.errors(include_url=False, include_input=False)[:8]:
            path = ".".join(str(part) for part in error["loc"]) or "root"
            issues.append(f"- {path}: {error['msg']}")
        return "\n".join(issues)
    if isinstance(exc, json.JSONDecodeError):
        return "- root: JSON 语法不完整或括号未闭合"
    if isinstance(exc, RetryableAIResponseError):
        return "- root: AI 回答为空或因长度限制被截断"
    return "- root: 没有找到完整的 JSON 对象"


def _ground_workflow_analysis(
    analysis: WorkflowAnalysis,
    resume_text: str,
    jd_text: str,
) -> WorkflowAnalysis:
    resume_source = _normalize_for_match(resume_text)
    role_source = _normalize_for_match(resume_text + "\n" + jd_text)
    resume_segments = _source_segments(resume_text)

    analysis.strengths = [
        item
        for item in analysis.strengths
        if _is_informative_grounded(item.evidence, resume_source)
    ]
    analysis.suggestions = [
        item
        for item in analysis.suggestions
        if _is_grounded(item.original, resume_source)
        and _number_tokens(item.optimized) <= _number_tokens(item.original)
        and all(_is_grounded(keyword, resume_source) for keyword in item.keywords)
    ]

    if analysis.target_role and not _is_grounded(analysis.target_role, role_source):
        analysis.target_role = ""

    resume = analysis.resume
    for field_name in ("name", "phone", "email", "city"):
        _clear_ungrounded_field(resume.contact, field_name, resume_source)
    resume.contact.links = _grounded_values(resume.contact.links, resume_source)
    if resume.contact.target_role and not _is_grounded(
        resume.contact.target_role, role_source
    ):
        resume.contact.target_role = ""

    if resume.summary and not _is_grounded(resume.summary, resume_source):
        resume.summary = ""

    resume.education = _ground_education(resume.education, resume_segments)
    resume.experience = _ground_experience(resume.experience, resume_segments)
    resume.projects = _ground_projects(resume.projects, resume_segments)
    resume.campus = _grounded_values(resume.campus, resume_source)
    resume.skills = _grounded_values(resume.skills, resume_source)
    resume.certifications = _grounded_values(resume.certifications, resume_source)
    return analysis


def _ground_education(items, source_segments: list[str]):
    grounded = []
    for item in items:
        source = _item_source(item.source_quote, source_segments)
        if not source:
            continue
        if not _item_values_are_grounded(
            item,
            ("school", "degree", "major", "start_date", "end_date"),
            ("highlights",),
            source,
        ):
            continue
        if any(
            (
                item.school,
                item.degree,
                item.major,
                item.start_date,
                item.end_date,
                item.highlights,
            )
        ):
            grounded.append(item)
    return grounded


def _ground_experience(items, source_segments: list[str]):
    grounded = []
    for item in items:
        source = _item_source(item.source_quote, source_segments)
        if not source:
            continue
        if not _item_values_are_grounded(
            item,
            ("organization", "role", "location", "start_date", "end_date"),
            ("bullets",),
            source,
        ):
            continue
        if any(
            (
                item.organization,
                item.role,
                item.location,
                item.start_date,
                item.end_date,
                item.bullets,
            )
        ):
            grounded.append(item)
    return grounded


def _ground_projects(items, source_segments: list[str]):
    grounded = []
    for item in items:
        source = _item_source(item.source_quote, source_segments)
        if not source:
            continue
        if not _item_values_are_grounded(
            item,
            ("name", "role", "start_date", "end_date"),
            ("bullets",),
            source,
        ):
            continue
        if any((item.name, item.role, item.start_date, item.end_date, item.bullets)):
            grounded.append(item)
    return grounded


def _item_values_are_grounded(
    item,
    scalar_fields: tuple[str, ...],
    list_fields: tuple[str, ...],
    source: str,
) -> bool:
    scalar_values = (getattr(item, field_name) for field_name in scalar_fields)
    list_values = (
        value
        for field_name in list_fields
        for value in getattr(item, field_name)
    )
    scalars_grounded = all(
        not value or _is_grounded(value, source) for value in scalar_values
    )
    lists_grounded = all(_is_grounded(value, source) for value in list_values)
    layout_grounded = _item_quote_layout_is_valid(
        item,
        scalar_fields,
        list_fields,
    )
    return scalars_grounded and lists_grounded and layout_grounded


def _item_quote_layout_is_valid(
    item,
    scalar_fields: tuple[str, ...],
    list_fields: tuple[str, ...],
) -> bool:
    quote_lines = [
        normalized
        for line in item.source_quote.splitlines()
        if (normalized := _normalize_for_match(line))
    ]
    if not quote_lines:
        return False

    scalar_values = [
        _normalize_for_match(getattr(item, field_name))
        for field_name in scalar_fields
        if getattr(item, field_name)
    ]
    list_values = [
        _normalize_for_match(value)
        for field_name in list_fields
        for value in getattr(item, field_name)
        if value
    ]

    if scalar_values and not all(value in quote_lines[0] for value in scalar_values):
        return False
    if not all(any(value in line for line in quote_lines) for value in list_values):
        return False

    content_lines = quote_lines[1:] if scalar_values else quote_lines
    return all(any(value in line for value in list_values) for line in content_lines)


def _clear_ungrounded_field(item, field_name: str, source: str) -> None:
    value = getattr(item, field_name)
    if value and not _is_grounded(value, source):
        setattr(item, field_name, "")


def _grounded_values(values: list[str], source: str) -> list[str]:
    return [value for value in values if _is_grounded(value, source)]


def _is_grounded(value: str, normalized_source: str) -> bool:
    normalized_value = _normalize_for_match(value)
    return bool(normalized_value and normalized_value in normalized_source)


def _is_informative_grounded(value: str, normalized_source: str) -> bool:
    normalized_value = _normalize_for_match(value)
    informative_value = re.sub(r"[^\w\u4e00-\u9fff]", "", normalized_value)
    letter_count = sum(character.isalpha() for character in informative_value)
    return letter_count >= 4 and normalized_value in normalized_source


def _source_segments(value: str) -> list[str]:
    paragraphs = re.split(r"\r?\n\s*\r?\n+", value)
    return [
        normalized
        for paragraph in paragraphs
        if (normalized := _normalize_for_match(paragraph))
    ]


def _item_source(source_quote: str, source_segments: list[str]) -> str:
    normalized_quote = _normalize_for_match(source_quote)
    if not normalized_quote or len(normalized_quote) > 1_500:
        return ""
    if any(normalized_quote in segment for segment in source_segments):
        return normalized_quote
    return ""


def _normalize_for_match(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).casefold()
    return "".join(normalized.split())


def _number_tokens(value: str) -> Counter[str]:
    return Counter(re.findall(r"\d+(?:[.,]\d+)?%?", value))
