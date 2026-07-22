def test_config_status_never_exposes_secret(client, app_settings, monkeypatch):
    monkeypatch.setattr(app_settings, "AI_API_KEY", "sk-super-secret")

    response = client.get("/api/config/status")

    assert response.status_code == 200
    assert response.json() == {"text_ai": True, "image_ai": False}
    assert "secret" not in response.text


def test_removed_routes_are_not_registered(client):
    assert client.post(
        "/api/auth/login",
        json={"email": "nobody@example.com", "password": "password"},
    ).status_code == 404
    assert client.get("/api/dev/status").status_code == 404


def test_health_is_small_and_public(client):
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
