# Local Job Toolkit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the current WorkBuddy scaffold into a secure, stateless, GitHub-ready local tool that analyzes a resume against a JD, applies user-approved rewrites, exports real DOCX/PDF-ready resumes, and creates local or AI-assisted career photos.

**Architecture:** Keep Vue 3/Vite as a two-route local frontend and reduce FastAPI to a stateless API. Text AI uses an OpenAI Chat Completions-compatible adapter with DeepSeek defaults; image generation is optional and falls back to a provider-neutral prompt resource. Uploaded content is validated and processed in memory, and all user/auth/database surfaces are removed.

**Tech Stack:** Vue 3, Vite, Element Plus, Vitest, FastAPI, Pydantic 2, httpx, pdfplumber, python-docx, Pillow, pytest.

---

## File Map

### Backend files to create or replace

- `backend/app/core/config.py`: local-only configuration and secret-safe status.
- `backend/app/core/errors.py`: stable public API errors.
- `backend/app/schemas/resume.py`: structured resume and workflow response models.
- `backend/app/schemas/jd.py`: standalone JD analysis models.
- `backend/app/schemas/photo.py`: image-generation consent and response models.
- `backend/app/services/document_service.py`: secure signature validation and text extraction.
- `backend/app/services/ai_service.py`: OpenAI-compatible JSON calls, timeout, retry, concurrency.
- `backend/app/services/export_service.py`: three DOCX templates.
- `backend/app/services/photo_service.py`: prompt construction and optional image edit proxy.
- `backend/app/routers/documents.py`: PDF/DOCX parse endpoint.
- `backend/app/routers/workflow.py`: resume + JD and JD-only endpoints.
- `backend/app/routers/export.py`: DOCX download endpoint.
- `backend/app/routers/photo.py`: prompt resource and optional generation endpoints.
- `backend/app/main.py`: stateless app, local CORS, router registration, safe errors.
- `backend/prompts/workflow/system.txt`: fact-preserving resume/JD prompt.
- `backend/prompts/jd/system.txt`: standalone JD prompt.
- `backend/prompts/photo/*.txt`: career portrait prompt fragments.
- `backend/tests/*`: backend contract and security tests.

### Backend files to remove

- `backend/app/models/`
- `backend/app/routers/auth.py`
- `backend/app/routers/dependencies.py`
- `backend/app/routers/dev.py`
- `backend/app/schemas/user.py`
- `backend/app/core/security.py`
- old `backend/prompts/resume_generate/`, `resume_diagnose/`, and `jd_parser/`

### Frontend files to create or replace

- `frontend/src/App.vue`: compact two-item application shell.
- `frontend/src/router/index.js`: `/` and `/photo` only.
- `frontend/src/api/client.js`: no auth interceptor, typed public errors.
- `frontend/src/views/WorkspaceView.vue`: five-step resume/JD workflow.
- `frontend/src/views/PhotoStudio.vue`: local ID photo and AI career portrait modes.
- `frontend/src/components/DocumentInput.vue`: upload/paste input.
- `frontend/src/components/MatchReport.vue`: score, matches, gaps, risks.
- `frontend/src/components/SuggestionEditor.vue`: accept/reject/edit rewrites.
- `frontend/src/components/ResumeEditor.vue`: editable structured resume fields.
- `frontend/src/components/ResumePreview.vue`: three printable templates.
- `frontend/src/components/TemplateSelector.vue`: purpose-based template selection.
- `frontend/src/components/photo/LocalPhotoEditor.vue`: crop, scale, background, sizes.
- `frontend/src/components/photo/CareerPortraitPanel.vue`: prompt resource and optional API.
- `frontend/src/composables/useWorkflow.js`: transient workflow state.
- `frontend/src/assets/global.css`: restrained responsive visual system and print styles.
- `frontend/src/**/*.test.js`: Vitest component and workflow tests.

### Frontend files to remove

- `frontend/src/views/HomePage.vue`
- `frontend/src/views/ResumeEditor.vue`
- `frontend/src/views/JDParser.vue`
- `frontend/src/views/PhotoTool.vue`
- `frontend/src/views/LoginPage.vue`
- `frontend/src/views/RegisterPage.vue`
- `frontend/src/views/DevPanel.vue`
- `frontend/src/stores/user.js`
- unused starter assets/components.

### Repository files

- Replace `README.md` with verified GitHub instructions.
- Replace `start.bat` with a non-destructive launcher.
- Replace `.gitignore`, `docker-compose.yml`, and `backend/.env.example`.
- Add `LICENSE`, `CONTRIBUTING.md`, and GitHub-ready screenshots after visual verification.

---

## Task 1: Stateless Backend and Configuration Safety

**Files:**
- Modify: `backend/app/core/config.py`
- Create: `backend/app/core/errors.py`
- Modify: `backend/app/main.py`
- Modify: `backend/requirements.txt`
- Create: `backend/requirements-dev.txt`
- Create: `backend/tests/conftest.py`
- Create: `backend/tests/test_config_and_app.py`
- Remove: auth, database, developer, and security files listed in the file map

- [ ] **Step 1: Write failing configuration and route-surface tests**

```python
def test_config_status_never_exposes_secret(client, settings):
    settings.AI_API_KEY = "sk-super-secret"
    response = client.get("/api/config/status")
    assert response.status_code == 200
    assert response.json() == {"text_ai": True, "image_ai": False}
    assert "secret" not in response.text


def test_removed_routes_are_not_registered(client):
    for path in ("/api/auth/login", "/api/dev/status"):
        assert client.get(path).status_code == 404
```

- [ ] **Step 2: Run tests and confirm the old application fails the new contract**

Run: `backend/.venv/Scripts/python -m pytest backend/tests/test_config_and_app.py -q`

Expected: FAIL because `/api/config/status` does not exist and old routes remain registered.

- [ ] **Step 3: Implement secret-safe settings and stateless app initialization**

Use `pydantic_settings.BaseSettings` fields `AI_API_KEY`, `AI_BASE_URL`, `AI_MODEL`, `IMAGE_API_KEY`, `IMAGE_BASE_URL`, `IMAGE_MODEL`, upload limits, concurrency, timeout, and local CORS origins. Expose only boolean configured states. Remove SQLAlchemy initialization and register only health/config plus the new routers as they are added.

- [ ] **Step 4: Remove auth/database/developer dependencies and complete requirements**

Production requirements must include exactly the used runtime libraries: FastAPI, Uvicorn, Pydantic settings, python-multipart, httpx, pdfplumber, python-docx, and Pillow. Test dependencies belong in `requirements-dev.txt`.

- [ ] **Step 5: Run the focused tests**

Run: `backend/.venv/Scripts/python -m pytest backend/tests/test_config_and_app.py -q`

Expected: PASS, with health and boolean-only configuration status.

---

## Task 2: Secure In-Memory Document Parsing

**Files:**
- Create: `backend/app/services/document_service.py`
- Create: `backend/app/routers/documents.py`
- Create: `backend/tests/test_documents.py`
- Remove: `backend/app/services/doc_parser.py`

- [ ] **Step 1: Write failing validation tests**

Cover valid PDF/DOCX, wrong magic bytes, mismatched extension/MIME, legacy `.doc`, files over 8 MB, DOCX zip bombs/path traversal, PDFs over the page limit, and empty/scanned documents.

```python
def test_rejects_fake_pdf(client):
    response = client.post(
        "/api/documents/parse",
        files={"file": ("resume.pdf", b"not-a-pdf", "application/pdf")},
    )
    assert response.status_code == 400
    assert response.json()["code"] == "invalid_file_signature"
```

- [ ] **Step 2: Run tests and verify the secure endpoint is absent**

Run: `backend/.venv/Scripts/python -m pytest backend/tests/test_documents.py -q`

Expected: FAIL with missing endpoint/service.

- [ ] **Step 3: Implement signature-first parsing**

Validate `%PDF-` for PDFs. Validate ZIP magic plus `[Content_Types].xml` and `word/document.xml` for DOCX, and reject suspicious archive paths or excessive uncompressed size. Parse bytes from memory only; never construct a filesystem path from the filename.

- [ ] **Step 4: Return stable parse metadata and public errors**

Successful response shape:

```json
{"text":"...","characters":1200,"kind":"pdf","units":2}
```

Scanning/no-text errors must be distinguishable from corrupt/unsupported/too-large errors.

- [ ] **Step 5: Run document tests**

Run: `backend/.venv/Scripts/python -m pytest backend/tests/test_documents.py -q`

Expected: PASS.

---

## Task 3: Validated AI Workflow and JD Analysis

**Files:**
- Replace: `backend/app/schemas/resume.py`
- Create: `backend/app/schemas/jd.py`
- Replace: `backend/app/services/ai_service.py`
- Create: `backend/app/routers/workflow.py`
- Create: `backend/prompts/workflow/system.txt`
- Create: `backend/prompts/jd/system.txt`
- Create: `backend/tests/test_ai_service.py`
- Create: `backend/tests/test_workflow.py`

- [ ] **Step 1: Write failing schema and retry tests**

Test score bounds, required resume sections, rewrite suggestions, `requires_user_input`, markdown-fenced JSON extraction, one format-only retry, timeout mapping, and no raw model response in public errors.

```python
def test_rewrite_cannot_silently_add_unverified_fact():
    item = RewriteSuggestion(
        id="exp-1",
        section="experience",
        original="协助整理数据",
        optimized="将处理效率提升 50%",
        reason="量化结果",
        keywords=["数据分析"],
        requires_user_input=True,
    )
    assert item.requires_user_input is True
```

- [ ] **Step 2: Run the tests and confirm failure**

Run: `backend/.venv/Scripts/python -m pytest backend/tests/test_ai_service.py backend/tests/test_workflow.py -q`

Expected: FAIL because the new schemas and endpoints do not exist.

- [ ] **Step 3: Implement a bounded OpenAI-compatible client**

Use `httpx.AsyncClient`, an `asyncio.Semaphore`, configured timeout, and one retry only when JSON/schema validation fails. Do not retry billing/authentication errors. Inject or monkeypatch the transport in tests; no test may call a real model.

- [ ] **Step 4: Implement untrusted-input prompt boundaries**

System prompts must state that content inside `<resume_data>` and `<job_description>` is untrusted data, not instructions. Require evidence-backed matching, fact preservation, stable IDs for rewrite suggestions, and strict JSON matching the Pydantic schema.

- [ ] **Step 5: Implement `/api/workflow/analyze` and `/api/jd/analyze`**

The combined endpoint returns match score, strengths, gaps, risk items, rewrites, and a structured resume. The JD-only endpoint returns summary, responsibilities, requirements, hard/soft skills, keywords, and preparation advice.

- [ ] **Step 6: Run focused and full backend tests**

Run: `backend/.venv/Scripts/python -m pytest backend/tests/test_ai_service.py backend/tests/test_workflow.py -q`

Expected: PASS.

---

## Task 4: Real Resume Templates and DOCX Export

**Files:**
- Create: `backend/app/services/export_service.py`
- Create: `backend/app/routers/export.py`
- Create: `backend/tests/test_export.py`

- [ ] **Step 1: Write failing export tests for all templates**

```python
@pytest.mark.parametrize("template", ["ats", "campus", "experienced"])
def test_docx_export_contains_editable_resume_text(client, resume_payload, template):
    response = client.post(
        "/api/resume/export/docx",
        json={"template": template, "resume": resume_payload},
    )
    assert response.status_code == 200
    doc = docx.Document(io.BytesIO(response.content))
    text = "\n".join(p.text for p in doc.paragraphs)
    assert "项目经历" in text
    assert "张三" in text
```

Also assert that ATS output has no photo/table layout, campus can reserve a photo area, switching templates does not change content, and invalid templates fail cleanly.

- [ ] **Step 2: Run export tests and verify failure**

Run: `backend/.venv/Scripts/python -m pytest backend/tests/test_export.py -q`

Expected: FAIL with missing endpoint.

- [ ] **Step 3: Implement shared document primitives**

Create reusable functions for A4 margins, fonts, headings, date/location rows, bullet lists, hyperlinks, and optional photo insertion. Keep all text editable. Do not render the resume as an image.

- [ ] **Step 4: Implement ATS, campus, and experienced layouts**

ATS is single-column black/white with no icons, photos, or tables. Campus prioritizes education/projects and allows an optional photo. Experienced prioritizes summary/skills/work and moves education later.

- [ ] **Step 5: Return a safe filename and correct media type**

Use a generated ASCII fallback filename plus RFC 5987 UTF-8 filename header. Never use unsanitized user text in a path.

- [ ] **Step 6: Run export tests and inspect generated samples**

Run: `backend/.venv/Scripts/python -m pytest backend/tests/test_export.py -q`

Expected: PASS and all three in-memory DOCX files reopen with `python-docx`.

---

## Task 5: Replace the Frontend with the Resume/JD Workbench

**Files:**
- Replace/create frontend shell, router, API client, workspace components, composable, and tests listed in the file map
- Remove old auth/dev/home/tool pages and user store
- Modify: `frontend/package.json`

- [ ] **Step 1: Add Vitest and write failing route/API tests**

Tests must prove there are only two product routes, no auth redirect/token storage, public errors are readable, and the default route renders the upload/paste workflow rather than a landing page.

- [ ] **Step 2: Run tests and confirm the old frontend fails**

Run: `npm test -- --run`

Expected: FAIL because old routes and auth behavior remain.

- [ ] **Step 3: Implement the compact application shell and workflow state**

Use a restrained work-tool layout with two navigation items. Store resume/JD/results only in Vue refs for the current tab session. Do not persist documents or keys in localStorage.

- [ ] **Step 4: Implement document input and combined analysis**

Support paste and PDF/DOCX upload, clear loading/error states, character counts, AI configuration status, and duplicate-submit prevention. Preserve user input after failures.

- [ ] **Step 5: Implement report, suggestion approval, and structured editing**

Show match score, evidence-backed strengths, missing skills, risks, and before/after suggestions. Each suggestion has accept/reject/edit controls. `requires_user_input` items remain visibly unresolved until edited or rejected.

- [ ] **Step 6: Implement normal resume preview and template switching**

Never display raw JSON as the final output. Render fields as a resume, support three templates, invoke DOCX export, and add a print-only A4 stylesheet for Save as PDF.

- [ ] **Step 7: Run frontend tests and build**

Run: `npm test -- --run`

Run: `npm run build`

Expected: tests PASS and production build exits 0.

---

## Task 6: Local ID Photo and AI Career Portrait Resource

**Files:**
- Create/replace photo frontend and backend files listed in the file map
- Create: `backend/tests/test_photo.py`
- Create: `frontend/src/components/photo/*.test.js`

- [ ] **Step 1: Write failing prompt, consent, and local-editor tests**

Backend tests cover prompt combinations, no-key fallback, explicit consent, image signatures, provider timeout, and secret-safe errors. Frontend tests cover mode labels, custom background, size selection, zoom bounds, resource download, and provider failure fallback.

- [ ] **Step 2: Run tests and verify failure**

Run: `backend/.venv/Scripts/python -m pytest backend/tests/test_photo.py -q`

Run: `npm test -- --run src/components/photo`

Expected: FAIL because the new contract is absent.

- [ ] **Step 3: Implement the local standard-photo editor**

Keep TensorFlow BodyPix lazy-loaded in the browser. Add drag position, bounded zoom, custom color, common pixel/mm sizes, lightweight brightness, reset, single PNG download, and six-inch print-sheet generation. State clearly when segmentation falls back to crop-only mode.

- [ ] **Step 4: Implement deterministic career-portrait prompt resources**

Compose prompts from approved fragments for suit/shirt style, white/gray/blue background, framing, light retouching, and strict identity preservation. Include negative instructions for face drift, changed age/ethnicity, plastic skin, malformed clothing, jewelry, text, and watermarks. Allow copy and UTF-8 `.txt` download.

- [ ] **Step 5: Implement optional image edit proxy with consent**

Accept only a validated JPG/PNG, require `consent=true`, require image-provider configuration, and send one multipart OpenAI Image Edit-compatible request. Do not log image bytes or prompts. Return generated bytes/URL only after validating provider response. On unsupported/unavailable providers return a stable fallback response that keeps the prompt resource usable.

- [ ] **Step 6: Run backend/frontend photo tests**

Expected: PASS without making real network calls.

---

## Task 7: Safe Launch, Docker, README, and Repository Hygiene

**Files:**
- Replace: `start.bat`
- Replace: `docker-compose.yml`
- Replace: `.gitignore`
- Replace: `backend/.env.example`
- Create: root `.env.example`
- Create: `README.md`
- Create: `LICENSE`
- Create: `CONTRIBUTING.md`
- Remove misleading README template and obsolete generated scaffold files after their useful content is incorporated

- [ ] **Step 1: Write a repository-hygiene check**

Create a test/script that fails when tracked files contain likely real API keys, `.env`, database files, uploaded resumes/photos, build caches, or old auth/dev routes. Allow only placeholder keys matching documented sample values.

- [ ] **Step 2: Run the hygiene check and capture current failures**

Expected: FAIL on obsolete routes/docs or dependency/config mismatches.

- [ ] **Step 3: Replace the Windows launcher safely**

The launcher checks `python`, `node`, backend venv, and frontend dependencies; prints exact setup commands when missing; starts only this project's backend/frontend; opens no privileged ports; never calls broad `taskkill`; never deletes files.

- [ ] **Step 4: Align Docker and environment configuration**

Docker Compose uses the root `.env`, builds the production frontend and backend, binds local ports by default, and removes the unused Hivision service. Samples explain that each user supplies their own text/image key.

- [ ] **Step 5: Write a truthful GitHub README**

Include actual features, two-mode photo behavior, screenshots, architecture, manual/Windows/Docker setup, BYOK cost ownership, privacy boundaries, legal-ID limitation, testing commands, roadmap, and license. Do not mark unimplemented features complete.

- [ ] **Step 6: Run the hygiene check until clean**

Expected: PASS with no secret or personal-data candidates in tracked content.

---

## Task 8: Full Security, Functional, and Visual Verification

**Files:**
- Create verified screenshots under `docs/screenshots/`
- Update `README.md` only if verification reveals a factual mismatch

- [ ] **Step 1: Run the entire backend suite**

Run: `backend/.venv/Scripts/python -m pytest backend/tests -q`

Expected: all tests PASS, no network access.

- [ ] **Step 2: Run frontend tests and production build**

Run: `npm test -- --run`

Run: `npm run build`

Expected: all tests PASS and build exits 0.

- [ ] **Step 3: Start the local application and run smoke checks**

Verify health/config, PDF/DOCX parsing, mocked workflow rendering, suggestion approval, all three previews, DOCX download/reopen, print view, standard photo output, prompt resource, and image-provider fallback.

- [ ] **Step 4: Perform desktop and mobile visual QA**

Use browser screenshots at approximately 1440x900, 1024x768, and 390x844. Confirm no overlap, clipped text, horizontal overflow, nested-card clutter, or layout shifts. Confirm the photo canvas is nonblank via pixel inspection after an image is loaded.

- [ ] **Step 5: Run a focused security review**

Re-check secrets, upload parsing, prompt injection boundaries, SSRF/provider URL handling, error leakage, CORS, local bind behavior, logging, dependency surface, and safe launch scripts. Add regression tests for every validated issue fixed during review.

- [ ] **Step 6: Inspect the final Git diff and tracked file list**

Confirm only intended source, tests, docs, safe examples, and screenshots are tracked. Ensure `.env`, local databases, resumes, photos, virtualenvs, node_modules, and generated caches are absent.

- [ ] **Step 7: Create the final GitHub-ready commit**

Stage the final verified repository and commit with a message describing the local job-toolkit release. Do not push or create a remote unless the user separately requests it.
