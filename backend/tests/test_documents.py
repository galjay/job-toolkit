import io
import zipfile

import docx
import pytest
from reportlab.pdfgen import canvas


def make_pdf(text: str = "Resume text", pages: int = 1) -> bytes:
    output = io.BytesIO()
    pdf = canvas.Canvas(output)
    for index in range(pages):
        if text:
            pdf.drawString(72, 720, f"{text} {index + 1}")
        pdf.showPage()
    pdf.save()
    return output.getvalue()


def make_docx(text: str = "Project experience") -> bytes:
    output = io.BytesIO()
    document = docx.Document()
    document.add_paragraph(text)
    document.save(output)
    return output.getvalue()


def test_parses_pdf_in_memory(client):
    response = client.post(
        "/api/documents/parse",
        files={"file": ("resume.pdf", make_pdf(), "application/pdf")},
    )

    assert response.status_code == 200
    assert response.json()["kind"] == "pdf"
    assert "Resume text" in response.json()["text"]


def test_parses_docx_in_memory(client):
    response = client.post(
        "/api/documents/parse",
        files={
            "file": (
                "resume.docx",
                make_docx(),
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
    )

    assert response.status_code == 200
    assert response.json()["kind"] == "docx"
    assert response.json()["text"] == "Project experience"


@pytest.mark.parametrize(
    ("name", "body", "content_type", "code"),
    [
        ("resume.pdf", b"not-a-pdf", "application/pdf", "invalid_file_signature"),
        ("resume.doc", b"legacy", "application/msword", "unsupported_file_type"),
        ("resume.txt", b"plain", "text/plain", "unsupported_file_type"),
    ],
)
def test_rejects_unsafe_or_unsupported_files(client, name, body, content_type, code):
    response = client.post(
        "/api/documents/parse",
        files={"file": (name, body, content_type)},
    )

    assert response.status_code == 400
    assert response.json()["code"] == code


def test_rejects_oversized_upload_before_parsing(client, app_settings, monkeypatch):
    monkeypatch.setattr(app_settings, "MAX_UPLOAD_BYTES", 16)

    response = client.post(
        "/api/documents/parse",
        files={"file": ("resume.pdf", b"%PDF-" + b"x" * 20, "application/pdf")},
    )

    assert response.status_code == 413
    assert response.json()["code"] == "file_too_large"


def test_rejects_pdf_over_page_limit(client, app_settings, monkeypatch):
    monkeypatch.setattr(app_settings, "MAX_PDF_PAGES", 1)

    response = client.post(
        "/api/documents/parse",
        files={"file": ("resume.pdf", make_pdf(pages=2), "application/pdf")},
    )

    assert response.status_code == 400
    assert response.json()["code"] == "too_many_pages"


def test_rejects_scanned_or_empty_pdf(client):
    response = client.post(
        "/api/documents/parse",
        files={"file": ("resume.pdf", make_pdf(text=""), "application/pdf")},
    )

    assert response.status_code == 422
    assert response.json()["code"] == "no_extractable_text"


def test_rejects_suspicious_docx_archive(client):
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        archive.writestr("[Content_Types].xml", "content")
        archive.writestr("word/document.xml", "document")
        archive.writestr("../outside.txt", "unsafe")

    response = client.post(
        "/api/documents/parse",
        files={
            "file": (
                "resume.docx",
                output.getvalue(),
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
    )

    assert response.status_code == 400
    assert response.json()["code"] == "unsafe_archive"
