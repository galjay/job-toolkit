import asyncio
import json

import pytest
from pydantic import ValidationError

from app.core.errors import PublicError
from app.schemas.resume import MatchItem, ResumeDocument, WorkflowAnalysis
from app.services.ai_service import AIService, _chat_endpoint, extract_json


VALID_RESULT = {
    "match_score": 76,
    "target_role": "产品实习生",
    "strengths": [
        {"name": "用户研究", "evidence": "完成访谈", "suggestion": "保留"}
    ],
    "gaps": [],
    "risks": [],
    "suggestions": [
        {
            "id": "experience-1",
            "section": "experience",
            "original": "整理访谈",
            "optimized": "整理并归纳用户访谈反馈",
            "reason": "说明动作和对象",
            "keywords": ["用户研究"],
            "requires_user_input": False,
        }
    ],
    "resume": {"contact": {"name": "张三"}, "skills": ["用户研究"]},
}


class StubAIService(AIService):
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = 0

    async def _request_text(self, system_prompt, user_message):
        self.calls += 1
        return self.responses.pop(0)


def test_extracts_json_from_markdown_fence():
    assert extract_json('```json\n{"score": 80}\n```') == {"score": 80}


def test_schema_rejects_score_outside_range():
    with pytest.raises(ValidationError):
        WorkflowAnalysis(**{**VALID_RESULT, "match_score": 101})


def test_match_item_requires_evidence():
    with pytest.raises(ValidationError):
        MatchItem(name="Python", evidence="", suggestion="保留")


def test_invalid_model_format_retries_once_then_succeeds():
    service = StubAIService(["not json", json.dumps(VALID_RESULT, ensure_ascii=False)])

    result = asyncio.run(service.call_json("system", "user", WorkflowAnalysis))

    assert result.match_score == 76
    assert service.calls == 2


def test_invalid_model_format_never_leaks_raw_response():
    service = StubAIService(["PRIVATE RAW MODEL OUTPUT", "still invalid"])

    with pytest.raises(PublicError) as error:
        asyncio.run(service.call_json("system", "user", WorkflowAnalysis))

    assert error.value.code == "ai_invalid_response"
    assert "PRIVATE" not in error.value.message


def test_resume_document_has_safe_empty_collections():
    resume = ResumeDocument(contact={"name": "张三"})
    assert resume.education == []
    assert resume.experience == []
    assert resume.projects == []


def test_remote_text_provider_requires_https():
    with pytest.raises(PublicError) as error:
        _chat_endpoint("http://example.com/v1")
    assert error.value.code == "ai_invalid_config"
    assert _chat_endpoint("https://example.com/v1") == "https://example.com/v1/chat/completions"
    assert _chat_endpoint("http://127.0.0.1:11434/v1").startswith("http://127.0.0.1")
