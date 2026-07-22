import re
import subprocess
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]


def test_obsolete_auth_and_demo_surfaces_are_absent():
    obsolete = [
        "backend/app/routers/auth.py",
        "backend/app/routers/dev.py",
        "backend/app/routers/resume.py",
        "backend/app/routers/jd_parser.py",
        "frontend/src/views/LoginPage.vue",
        "frontend/src/views/RegisterPage.vue",
        "frontend/src/views/DevPanel.vue",
        "frontend/src/views/HomePage.vue",
        "frontend/src/stores/user.js",
    ]
    assert [path for path in obsolete if (ROOT / path).exists()] == []


def test_windows_launcher_has_no_broad_process_kill_or_data_delete():
    launcher = (ROOT / "start.bat").read_text(encoding="utf-8")
    normalized = launcher.lower().replace("/", "\\")
    assert "taskkill \\f \\im python.exe" not in normalized
    assert "del \"backend\\data" not in normalized
    assert "127.0.0.1" in launcher
    assert ' /D "%~dp0backend"' in launcher
    assert ' /D "%~dp0frontend"' in launcher


def test_repository_has_real_readme_and_safe_environment_sample():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    sample = (ROOT / ".env.example").read_text(encoding="utf-8")
    assert "简历与 JD" in readme
    assert "使用者自己的 API Key" in readme
    assert "AI_API_KEY=your-ai-api-key" in sample
    assert not re.search(r"sk-[A-Za-z0-9]{20,}", sample)


def test_local_secrets_and_generated_data_are_ignored():
    candidates = [
        ".env",
        "backend/.env",
        "backend/data/job_toolkit.db",
        "frontend/node_modules",
        "frontend/dist",
        "backend/.venv",
        ".workbuddy",
    ]
    for candidate in candidates:
        result = subprocess.run(
            ["git", "check-ignore", "-q", candidate],
            cwd=ROOT,
            check=False,
        )
        assert result.returncode == 0, candidate


def test_compose_is_local_only_and_has_no_placeholder_photo_service():
    compose = yaml.safe_load((ROOT / "docker-compose.yml").read_text(encoding="utf-8"))
    services = compose["services"]
    assert set(services) == {"backend", "frontend"}
    assert services["backend"]["ports"] == ["127.0.0.1:8000:8000"]
    assert services["frontend"]["ports"] == ["127.0.0.1:8080:80"]
