# app/main.py
from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy.orm import Session
from fastapi import BackgroundTasks
from .providers.openrouter_openai import call_chat_completions, ProviderError, DEFAULT_MODEL

from . import crud, schemas
from .config import settings
from .db import get_db

app = FastAPI(title="LLM Workflow Copilot — MVP")


@app.get("/health")
def health():
    return {"status": "ok"}


# Projects
@app.post("/api/v1/projects", response_model=schemas.ProjectOut)
def create_project_endpoint(
    payload: schemas.ProjectCreate, db: Session = Depends(get_db)
):
    return crud.create_project(db, payload)


@app.get("/api/v1/projects", response_model=list[schemas.ProjectOut])
def list_projects_endpoint(
    limit: int = 50, offset: int = 0, db: Session = Depends(get_db)
):
    return crud.list_projects(db, limit=limit, offset=offset)


@app.get("/api/v1/projects/{project_id}", response_model=schemas.ProjectOut)
def get_project_endpoint(project_id: str, db: Session = Depends(get_db)):
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="project not found")
    return project


# Prompts
@app.post("/api/v1/prompts", response_model=schemas.PromptOut)
def create_prompt_endpoint(
    payload: schemas.PromptCreate, db: Session = Depends(get_db)
):
    return crud.create_prompt(db, payload)


@app.get("/api/v1/prompts", response_model=list[schemas.PromptOut])
def list_prompts_endpoint(
    project_id: str | None = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    return crud.list_prompts(db, project_id=project_id, limit=limit, offset=offset)


@app.get("/api/v1/prompts/{prompt_id}", response_model=schemas.PromptOut)
def get_prompt_endpoint(prompt_id: str, db: Session = Depends(get_db)):
    prompt = crud.get_prompt(db, prompt_id)
    if not prompt:
        raise HTTPException(status_code=404, detail="prompt not found")
    return prompt


# Sessions
@app.post("/api/v1/sessions", response_model=schemas.SessionOut)
def create_session_endpoint(
    payload: schemas.SessionCreate, db: Session = Depends(get_db)
):
    # Validate project exists
    project = crud.get_project(db, payload.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="project not found")
    session = crud.create_session(
        db, project_id=payload.project_id, title=payload.title
    )
    return session


@app.get("/api/v1/sessions/{session_id}", response_model=schemas.SessionOut)
def get_session_endpoint(session_id: str, db: Session = Depends(get_db)):
    s = crud.get_session(db, session_id)
    if not s:
        raise HTTPException(status_code=404, detail="session not found")
    return s


# Session messages (append)
@app.post(
    "/api/v1/sessions/{session_id}/messages", response_model=schemas.SessionMessageOut
)
def append_session_message(
    session_id: str,
    payload: schemas.SessionMessageCreate,
    db: Session = Depends(get_db),
):
    # ensure session exists
    session = crud.get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="session not found")
    msg = crud.create_session_message(
        db,
        session_id=session_id,
        role=payload.role,
        content=payload.content,
        prompt_id=payload.prompt_id,
        model=payload.model,
    )
    return msg


# LLM run stub (synchronous)
@app.post("/api/v1/llm/run")
def llm_run(payload: dict, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """
    payload keys:
      - session_id (optional)
      - messages (preferred) OR content (string)
      - model (optional)
    """
    session_id = payload.get("session_id")
    model = payload.get("model") or DEFAULT_MODEL

    # Prefer full `messages` (list) to allow system messages and structured blocks
    messages = payload.get("messages")
    if messages is None:
        # fall back to a single user text message
        content = payload.get("content", "")
        messages = [{"role": "user", "content": content}]

    # Validate session if provided
    if session_id:
        session = crud.get_session(db, session_id)
        if not session:
            raise HTTPException(status_code=404, detail="session not found")

    # Persist user's messages (optional; persist only the first text message for simplicity)
    # If messages is a list, persist each user-role message
    created_user_msg_ids = []
    for m in messages:
        try:
            if m.get("role") == "user":
                # flatten content if structured
                c = m.get("content")
                if isinstance(c, list):
                    # join text pieces for DB storage
                    text_parts = []
                    for block in c:
                        if isinstance(block, dict) and "text" in block:
                            text_parts.append(block["text"])
                        elif isinstance(block, str):
                            text_parts.append(block)
                    content_str = " ".join(text_parts)
                elif isinstance(c, str):
                    content_str = c
                else:
                    content_str = str(c)
                msg = crud.create_session_message(db, session_id=session_id, role="user", content=content_str)
                created_user_msg_ids.append(msg.id)
        except Exception:
            # continue; do not block run if persisting user message fails
            pass

    # call provider
    try:
        out = call_chat_completions(messages=messages, model=model)
    except ProviderError as e:
        raise HTTPException(status_code=502, detail=str(e))

    assistant_text = out["text"]
    usage = out.get("usage", {}) or {}
    latency_ms = out.get("latency_ms")

    # persist assistant message
    assistant_msg = crud.create_session_message(db, session_id=session_id, role="assistant", content=assistant_text, model=model)

    # log usage event (safe extraction)
    tokens_prompt = int(usage.get("prompt_tokens", 0) or usage.get("input_tokens", 0) or 0)
    tokens_response = int(usage.get("completion_tokens", 0) or usage.get("output_tokens", 0) or 0)
    cost_usd = 0.0  # compute later with price table
    crud.log_usage_event(db, None, None, assistant_msg.id, model, tokens_prompt, tokens_response, cost_usd, latency_ms)

    # Optional background task: compute embeddings / enqueue upsert
    # background_tasks.add_task(embeddings.enqueue_embedding, assistant_msg.id, assistant_text)

    return {"id": str(assistant_msg.id), "content": assistant_text, "usage": usage}