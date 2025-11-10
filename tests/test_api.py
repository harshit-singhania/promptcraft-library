# tests/test_api.py
import uuid
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def make_obj(**kwargs):
    return SimpleNamespace(**kwargs)


def gen_id(prefix: str = ""):
    return str(uuid.uuid4())


# full ISO datetime used in stubs
NOW = "2025-01-01T00:00:00Z"


@pytest.fixture(autouse=True)
def patch_crud(monkeypatch):
    """
    Replace crud functions with lightweight stubs returning SimpleNamespace
    so tests run fast and do not require a real database.
    """
    import app.crud as crud

    # Projects
    def fake_create_project(db, project_in):
        return make_obj(
            id=gen_id("proj"),
            name=project_in.name,
            description=project_in.description,
            created_at=NOW,
        )

    def fake_list_projects(db, limit=50, offset=0):
        return [make_obj(id=gen_id(), name="proj-1", description="d", created_at=NOW)]

    def fake_get_project(db, project_id):
        if project_id == "not-found":
            return None
        return make_obj(id=project_id, name="proj", description="d", created_at=NOW)

    # Prompts
    def fake_create_prompt(db, prompt_in):
        return make_obj(
            id=gen_id("prompt"),
            project_id=str(prompt_in.project_id),
            name=prompt_in.name,
            template=prompt_in.template,
            default_model=prompt_in.default_model,
            tags=prompt_in.tags or [],
            created_at=NOW,
        )

    def fake_list_prompts(db, project_id=None, limit=50, offset=0):
        return [
            make_obj(
                id=gen_id("prompt"),
                project_id=project_id or gen_id(),
                name="p",
                template="t",
                default_model="gpt",
                tags=["t"],
                created_at=NOW,
            )
        ]

    def fake_get_prompt(db, prompt_id):
        if prompt_id == "not-found":
            return None
        return make_obj(
            id=prompt_id,
            project_id=gen_id(),
            name="p",
            template="t",
            default_model="gpt",
            tags=[],
            created_at=NOW,
        )

    # Sessions / messages
    def fake_create_session(db, project_id, title=None, created_by=None):
        return make_obj(
            id=gen_id("sess"), project_id=project_id, title=title, created_at=NOW
        )

    def fake_get_session(db, session_id):
        if session_id == "not-found":
            return None
        return make_obj(id=session_id, project_id=gen_id(), title="s", created_at=NOW)

    def fake_create_session_message(
        db, session_id, role, content, prompt_id=None, model=None
    ):
        return make_obj(
            id=gen_id("msg"),
            session_id=session_id,
            role=role,
            content=content,
            model=model,
            created_at=NOW,
        )

    def fake_log_usage_event(db, *args, **kwargs):
        return make_obj(id=gen_id("usage"))

    # Patch all
    monkeypatch.setattr(crud, "create_project", fake_create_project)
    monkeypatch.setattr(crud, "list_projects", fake_list_projects)
    monkeypatch.setattr(crud, "get_project", fake_get_project)
    monkeypatch.setattr(crud, "create_prompt", fake_create_prompt)
    monkeypatch.setattr(crud, "list_prompts", fake_list_prompts)
    monkeypatch.setattr(crud, "get_prompt", fake_get_prompt)
    monkeypatch.setattr(crud, "create_session", fake_create_session)
    monkeypatch.setattr(crud, "get_session", fake_get_session)
    monkeypatch.setattr(crud, "create_session_message", fake_create_session_message)
    monkeypatch.setattr(crud, "log_usage_event", fake_log_usage_event)

    yield


def test_project_prompt_session_flow():
    # quick health check
    r = client.get("/health")
    assert r.status_code in (200, 204)

    # create project
    r = client.post(
        "/api/v1/projects", json={"name": "pytest project", "description": "desc"}
    )
    assert r.status_code == 200
    project = r.json()
    assert project["name"] == "pytest project"
    project_id = project["id"]

    # create prompt
    prompt_payload = {
        "project_id": project_id,
        "name": "test prompt",
        "template": "Do X: {{input}}",
        "default_model": "gpt-4o",
        "tags": ["test"],
    }
    r = client.post("/api/v1/prompts", json=prompt_payload)
    assert r.status_code == 200
    prompt = r.json()
    assert prompt["name"] == "test prompt"

    # create session
    r = client.post(
        "/api/v1/sessions", json={"project_id": project_id, "title": "session1"}
    )
    assert r.status_code == 200
    session = r.json()
    assert "id" in session
    session_id = session["id"]

    # append a message
    r = client.post(
        f"/api/v1/sessions/{session_id}/messages",
        json={"role": "user", "content": "Hello test"},
    )
    assert r.status_code == 200
    msg = r.json()
    assert msg["role"] == "user"
    assert "Hello test" in msg["content"]

    # run LLM stub (no session)
    r = client.post("/api/v1/llm/run", json={"content": "stub", "model": "gpt-4o"})
    assert r.status_code == 200
    out = r.json()
    assert "id" in out and "content" in out

    # run LLM stub (with session)
    r = client.post(
        "/api/v1/llm/run",
        json={"session_id": session_id, "content": "stub2", "model": "gpt-4o"},
    )
    assert r.status_code == 200
    out2 = r.json()
    # be tolerant: either the stub echoes the input or returns any non-empty string
    assert "content" in out2 and isinstance(out2["content"], str) and len(out2["content"]) > 0