from app.main import app
from app.routers.workflow import get_ai_service
from app.schemas.jd import JDAnalysis
from app.schemas.resume import WorkflowAnalysis

from tests.test_ai_service import VALID_RESULT


class CaptureService:
    def __init__(self):
        self.resume_text = ""
        self.jd_text = ""

    async def analyze_workflow(self, resume_text, jd_text):
        self.resume_text = resume_text
        self.jd_text = jd_text
        return WorkflowAnalysis(**VALID_RESULT)

    async def analyze_jd(self, jd_text):
        self.jd_text = jd_text
        return JDAnalysis(
            summary="负责产品分析",
            responsibilities=["需求分析"],
            hard_skills=["数据分析"],
            soft_skills=["沟通"],
            education="本科",
            experience="不限",
            keywords=["产品"],
            preparation=["准备项目案例"],
        )


def test_combined_workflow_returns_structured_resume(client):
    service = CaptureService()
    app.dependency_overrides[get_ai_service] = lambda: service
    try:
        response = client.post(
            "/api/workflow/analyze",
            json={
                "resume_text": "我在校内项目中完成了十次用户访谈并整理反馈。",
                "jd_text": "负责用户研究、需求分析和产品方案设计，要求本科在读。",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["match_score"] == 76
    assert response.json()["resume"]["contact"]["name"] == "张三"
    assert service.resume_text.startswith("我在校内项目")


def test_jd_only_analysis(client):
    service = CaptureService()
    app.dependency_overrides[get_ai_service] = lambda: service
    try:
        response = client.post(
            "/api/jd/analyze",
            json={"jd_text": "负责用户研究、需求分析和产品方案设计，要求本科在读。"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["hard_skills"] == ["数据分析"]


def test_rejects_too_short_inputs(client):
    response = client.post(
        "/api/workflow/analyze",
        json={"resume_text": "太短", "jd_text": "也太短"},
    )
    assert response.status_code == 422


def test_prompt_declares_uploaded_text_untrusted():
    prompt = (
        __import__("pathlib").Path(__file__).parents[1]
        / "prompts"
        / "workflow"
        / "system.txt"
    ).read_text(encoding="utf-8")
    assert "不可信数据" in prompt
    assert "不得编造" in prompt
    assert "不得返回 null" in prompt
    assert "简历中未找到直接证据" in prompt
    assert "即使 requires_user_input 为 true" in prompt
    assert "evidence 必须逐字引用简历中的连续原文" in prompt
    assert "source_quote" in prompt
