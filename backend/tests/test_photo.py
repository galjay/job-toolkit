import io
import base64

from PIL import Image

from app.main import app
from app.routers.photo import get_photo_service
from app.services.photo_service import _parse_provider_result
from app.core.errors import PublicError


def make_png() -> bytes:
    output = io.BytesIO()
    Image.new("RGB", (200, 300), "white").save(output, format="PNG")
    return output.getvalue()


def test_prompt_resource_preserves_identity_and_marks_provider_status(client):
    response = client.post(
        "/api/photo/prompt",
        json={
            "presentation": "neutral",
            "outfit": "dark_suit",
            "background": "white",
            "retouch": "light",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert "保持参考照片中人物的面部身份特征" in body["prompt"]
    assert "深色商务西装" in body["prompt"]
    assert "身份漂移" in body["negative_prompt"]
    assert body["provider_enabled"] is False


def test_direct_generation_requires_explicit_consent(client):
    response = client.post(
        "/api/photo/generate",
        data={"prompt": "职业照", "consent": "false"},
        files={"file": ("face.png", make_png(), "image/png")},
    )
    assert response.status_code == 400
    assert response.json()["code"] == "photo_consent_required"


def test_direct_generation_rejects_fake_image(client):
    response = client.post(
        "/api/photo/generate",
        data={"prompt": "职业照", "consent": "true"},
        files={"file": ("face.png", b"not-an-image", "image/png")},
    )
    assert response.status_code == 400
    assert response.json()["code"] == "invalid_photo"


def test_direct_generation_without_provider_falls_back_cleanly(client):
    response = client.post(
        "/api/photo/generate",
        data={"prompt": "职业照", "consent": "true"},
        files={"file": ("face.png", make_png(), "image/png")},
    )
    assert response.status_code == 503
    assert response.json()["code"] == "image_ai_not_configured"


class StubPhotoService:
    async def generate(self, image, filename, content_type, prompt, consent):
        return {"image_data_url": "data:image/png;base64,ZmFrZQ=="}


def test_generation_endpoint_supports_dependency_override(client):
    app.dependency_overrides[get_photo_service] = lambda: StubPhotoService()
    try:
        response = client.post(
            "/api/photo/generate",
            data={"prompt": "职业照", "consent": "true"},
            files={"file": ("face.png", make_png(), "image/png")},
        )
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json()["image_data_url"].startswith("data:image/png")


def test_provider_cannot_label_arbitrary_bytes_as_png():
    payload = {"data": [{"b64_json": base64.b64encode(b"not an image").decode()}]}
    try:
        _parse_provider_result(payload)
    except ValueError:
        pass
    else:
        raise AssertionError("non-image provider output was accepted")
