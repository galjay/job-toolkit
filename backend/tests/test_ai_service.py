import asyncio
from copy import deepcopy
import json

import pytest
from pydantic import ValidationError

from app.core.config import settings
from app.core.errors import PublicError
from app.schemas.jd import JDAnalysis
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
        self.user_messages = []

    async def _request_text(self, system_prompt, user_message):
        self.calls += 1
        self.user_messages.append(user_message)
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


def test_validation_retry_tells_model_which_field_failed():
    invalid_result = deepcopy(VALID_RESULT)
    invalid_result["strengths"][0]["evidence"] = ""
    service = StubAIService(
        [
            json.dumps(invalid_result, ensure_ascii=False),
            json.dumps(VALID_RESULT, ensure_ascii=False),
        ]
    )

    result = asyncio.run(service.call_json("system", "user", WorkflowAnalysis))

    assert result.match_score == 76
    assert "strengths.0.evidence" in service.user_messages[1]


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


def test_workflow_normalizes_blank_gap_evidence():
    result_data = deepcopy(VALID_RESULT)
    result_data["gaps"] = [
        {"name": "SQL", "evidence": "", "suggestion": "补充可核验的项目经历"}
    ]

    result = WorkflowAnalysis.model_validate(result_data)

    assert result.gaps[0].evidence == "简历中未找到直接证据"


def test_resume_normalizes_explicit_null_optional_fields():
    resume = ResumeDocument.model_validate(
        {
            "contact": {"name": "张三", "phone": None, "links": None},
            "education": None,
            "skills": None,
        }
    )

    assert resume.contact.phone == ""
    assert resume.contact.links == []
    assert resume.education == []
    assert resume.skills == []


def test_workflow_grounds_model_facts_against_original_resume():
    result_data = deepcopy(VALID_RESULT)
    result_data["strengths"] = [
        {"name": "问卷整理", "evidence": "负责整理问卷结果", "suggestion": ""},
        {"name": "SQL", "evidence": "精通 SQL", "suggestion": ""},
    ]
    result_data["suggestions"] = [
        {
            "id": "experience-1",
            "section": "experience",
            "original": "分析了 200 份问卷",
            "optimized": "分析了 200 份问卷并输出报告",
            "reason": "补充工作量",
            "keywords": ["数据分析"],
            "requires_user_input": True,
        }
    ]
    result_data["resume"] = {
        "contact": {
            "name": "张三",
            "email": "fake@example.com",
            "target_role": "产品实习生",
        },
        "summary": "精通 SQL 和 Python",
        "experience": [
            {
                "id": "experience-1",
                "source_quote": "负责整理问卷结果",
                "organization": "不存在公司",
                "role": "产品经理",
                "bullets": ["负责整理问卷结果", "分析了 200 份问卷"],
            },
            {
                "id": "experience-2",
                "source_quote": "负责整理问卷结果",
                "bullets": ["负责整理问卷结果"],
            },
        ],
        "skills": ["Excel", "SQL"],
    }
    service = StubAIService([json.dumps(result_data, ensure_ascii=False)])

    result = asyncio.run(
        service.analyze_workflow(
            "张三，参与校园问卷调研项目，负责整理问卷结果，熟悉 Excel。",
            "招聘产品实习生，要求用户研究、SQL 和数据分析能力。",
        )
    )

    assert [item.name for item in result.strengths] == ["问卷整理"]
    assert result.suggestions == []
    assert result.resume.contact.name == "张三"
    assert result.resume.contact.email == ""
    assert result.resume.contact.target_role == "产品实习生"
    assert result.resume.summary == ""
    assert len(result.resume.experience) == 1
    assert result.resume.experience[0].id == "experience-2"
    assert result.resume.experience[0].bullets == ["负责整理问卷结果"]
    assert result.resume.skills == ["Excel"]


def test_workflow_drops_cross_experience_recombination():
    resume_text = (
        "我在 A 公司 | 产品经理 | 2020\n负责用户研究\n"
        "B 公司 | 工程师 | 2024\n负责后端开发"
    )
    result_data = deepcopy(VALID_RESULT)
    result_data["strengths"] = [
        {"name": "SQL", "evidence": "我", "suggestion": ""},
        {"name": "SQL", "evidence": "2024", "suggestion": ""},
    ]
    result_data["resume"] = {
        "contact": {},
        "experience": [
            {
                "id": "experience-1",
                "source_quote": resume_text,
                "organization": "A 公司",
                "role": "工程师",
                "start_date": "2024",
                "bullets": ["负责用户研究"],
            }
        ],
    }
    service = StubAIService([json.dumps(result_data, ensure_ascii=False)])

    result = asyncio.run(
        service.analyze_workflow(resume_text, "招聘工程师，要求 SQL 能力。")
    )

    assert result.strengths == []
    assert result.resume.experience == []


def test_workflow_does_not_move_an_unrelated_resume_number_into_rewrite():
    result_data = deepcopy(VALID_RESULT)
    result_data["suggestions"] = [
        {
            "id": "experience-1",
            "section": "experience",
            "original": "负责整理问卷结果",
            "optimized": "负责整理 200 份问卷结果",
            "reason": "补充工作量",
            "keywords": ["Excel"],
            "requires_user_input": True,
        }
    ]
    service = StubAIService([json.dumps(result_data, ensure_ascii=False)])

    result = asyncio.run(
        service.analyze_workflow(
            "编号 200。负责整理问卷结果，熟悉 Excel。",
            "招聘产品实习生，要求数据分析能力。",
        )
    )

    assert result.suggestions == []


def test_workflow_does_not_duplicate_a_grounded_number():
    result_data = deepcopy(VALID_RESULT)
    result_data["suggestions"] = [
        {
            "id": "experience-1",
            "section": "experience",
            "original": "参与 1 个项目",
            "optimized": "参与 1 个项目并带领 1 人",
            "reason": "补充影响力",
            "keywords": ["Excel"],
            "requires_user_input": True,
        }
    ]
    service = StubAIService([json.dumps(result_data, ensure_ascii=False)])

    result = asyncio.run(
        service.analyze_workflow(
            "参与 1 个项目，熟悉 Excel。",
            "招聘产品实习生，要求数据分析能力。",
        )
    )

    assert result.suggestions == []


def test_jd_analysis_normalizes_explicit_null_optional_fields():
    result = JDAnalysis.model_validate(
        {
            "summary": "产品岗位",
            "responsibilities": None,
            "hard_skills": None,
            "soft_skills": None,
            "education": None,
            "experience": 3,
            "keywords": None,
            "preparation": None,
        }
    )

    assert result.responsibilities == []
    assert result.hard_skills == []
    assert result.soft_skills == []
    assert result.education == ""
    assert result.experience == "3"
    assert result.keywords == []
    assert result.preparation == []


def test_truncated_chat_response_retries_even_when_json_is_valid(monkeypatch):
    calls = _install_fake_chat_client(
        monkeypatch,
        [
            {
                "choices": [
                    {
                        "finish_reason": "length",
                        "message": {"content": '{"contact":{"name":"截断内容"}}'},
                    }
                ]
            },
            {
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {"content": '{"contact":{"name":"完整内容"}}'},
                    }
                ]
            },
        ],
    )

    result = asyncio.run(AIService().call_json("system", "user", ResumeDocument))

    assert result.contact.name == "完整内容"
    assert len(calls) == 2


def test_null_chat_content_retries_instead_of_raising_500(monkeypatch):
    calls = _install_fake_chat_client(
        monkeypatch,
        [
            {
                "choices": [
                    {"finish_reason": "stop", "message": {"content": None}}
                ]
            },
            {
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {"content": '{"contact":{"name":"有效内容"}}'},
                    }
                ]
            },
        ],
    )

    result = asyncio.run(AIService().call_json("system", "user", ResumeDocument))

    assert result.contact.name == "有效内容"
    assert len(calls) == 2


def test_null_chat_message_retries_instead_of_raising_500(monkeypatch):
    calls = _install_fake_chat_client(
        monkeypatch,
        [
            {"choices": [{"finish_reason": "stop", "message": None}]},
            {
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {"content": '{"contact":{"name":"有效内容"}}'},
                    }
                ]
            },
        ],
    )

    result = asyncio.run(AIService().call_json("system", "user", ResumeDocument))

    assert result.contact.name == "有效内容"
    assert len(calls) == 2


def test_content_filter_returns_specific_public_error(monkeypatch):
    _install_fake_chat_client(
        monkeypatch,
        [
            {
                "choices": [
                    {
                        "finish_reason": "content_filter",
                        "message": {"content": ""},
                    }
                ]
            }
        ],
    )

    with pytest.raises(PublicError) as error:
        asyncio.run(AIService().call_json("system", "user", ResumeDocument))

    assert error.value.code == "ai_response_blocked"


def test_chat_request_reserves_enough_output_tokens(monkeypatch):
    captured = {}

    class FakeResponse:
        status_code = 200

        def raise_for_status(self):
            return None

        def json(self):
            return {"choices": [{"message": {"content": "{}"}}]}

    class FakeClient:
        def __init__(self, **_kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def post(self, _endpoint, **kwargs):
            captured.update(kwargs)
            return FakeResponse()

    monkeypatch.setattr("app.services.ai_service.httpx.AsyncClient", FakeClient)
    monkeypatch.setattr("app.services.ai_service.settings.AI_API_KEY", "test-key")
    monkeypatch.setattr("app.services.ai_service.settings.AI_BASE_URL", "https://example.com/v1")

    asyncio.run(AIService()._request_text("system", "user"))

    assert captured["json"]["max_tokens"] == 8192


def test_chat_request_supports_max_completion_tokens(monkeypatch):
    captured = {}

    class FakeResponse:
        status_code = 200

        def raise_for_status(self):
            return None

        def json(self):
            return {"choices": [{"message": {"content": "{}"}}]}

    class FakeClient:
        def __init__(self, **_kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def post(self, _endpoint, **kwargs):
            captured.update(kwargs)
            return FakeResponse()

    monkeypatch.setattr("app.services.ai_service.httpx.AsyncClient", FakeClient)
    monkeypatch.setattr(settings, "AI_API_KEY", "test-key")
    monkeypatch.setattr(settings, "AI_BASE_URL", "https://example.com/v1")
    monkeypatch.setattr(
        settings,
        "AI_OUTPUT_TOKEN_PARAM",
        "max_completion_tokens",
        raising=False,
    )

    asyncio.run(AIService()._request_text("system", "user"))

    assert "max_tokens" not in captured["json"]
    assert captured["json"]["max_completion_tokens"] == 8192


def test_remote_text_provider_requires_https():
    with pytest.raises(PublicError) as error:
        _chat_endpoint("http://example.com/v1")
    assert error.value.code == "ai_invalid_config"
    assert _chat_endpoint("https://example.com/v1") == "https://example.com/v1/chat/completions"
    assert _chat_endpoint("http://127.0.0.1:11434/v1").startswith("http://127.0.0.1")


def _install_fake_chat_client(monkeypatch, response_payloads):
    payloads = list(response_payloads)
    calls = []

    class FakeResponse:
        status_code = 200

        def __init__(self, payload):
            self.payload = payload

        def raise_for_status(self):
            return None

        def json(self):
            return self.payload

    class FakeClient:
        def __init__(self, **_kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def post(self, _endpoint, **kwargs):
            calls.append(kwargs)
            return FakeResponse(payloads.pop(0))

    monkeypatch.setattr("app.services.ai_service.httpx.AsyncClient", FakeClient)
    monkeypatch.setattr(settings, "AI_API_KEY", "test-key")
    monkeypatch.setattr(settings, "AI_BASE_URL", "https://example.com/v1")
    return calls
