# app/crud.py
from typing import List, Optional
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.orm import Session

from . import models, schemas


# Users
def get_user_by_email(db: Session, email: str) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.email == email).first()


def create_user(
    db: Session, email: str, hashed_password: str, name: Optional[str] = None
) -> models.User:
    user = models.User(email=email, hashed_password=hashed_password, name=name)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


# Projects
def create_project(
    db: Session, project_in: schemas.ProjectCreate, owner_id: Optional[UUID] = None
) -> models.Project:
    proj = models.Project(
        team_id=None, name=project_in.name, description=project_in.description
    )
    db.add(proj)
    db.commit()
    db.refresh(proj)
    return proj


def list_projects(
    db: Session, limit: int = 50, offset: int = 0
) -> List[models.Project]:
    return (
        db.query(models.Project)
        .order_by(models.Project.created_at.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )


def get_project(db: Session, project_id: UUID) -> Optional[models.Project]:
    return db.query(models.Project).filter(models.Project.id == project_id).first()


# Prompts
def create_prompt(db: Session, prompt_in: schemas.PromptCreate) -> models.Prompt:
    prompt = models.Prompt(
        project_id=prompt_in.project_id,
        owner_id=None,
        name=prompt_in.name,
        template=prompt_in.template,
        default_model=prompt_in.default_model,
        tags=prompt_in.tags or [],
    )
    db.add(prompt)
    db.commit()
    db.refresh(prompt)
    # create initial version
    version = models.PromptVersion(
        prompt_id=prompt.id, version_number=1, template=prompt.template, created_by=None
    )
    db.add(version)
    db.commit()
    db.refresh(version)
    # update latest_version_id
    prompt.latest_version_id = version.id
    db.commit()
    db.refresh(prompt)
    return prompt


def list_prompts(
    db: Session, project_id: Optional[UUID] = None, limit: int = 50, offset: int = 0
) -> List[models.Prompt]:
    q = db.query(models.Prompt)
    if project_id:
        q = q.filter(models.Prompt.project_id == project_id)
    return q.order_by(models.Prompt.created_at.desc()).limit(limit).offset(offset).all()


def get_prompt(db: Session, prompt_id: UUID) -> Optional[models.Prompt]:
    return db.query(models.Prompt).filter(models.Prompt.id == prompt_id).first()


# Sessions and messages
def create_session(
    db: Session,
    project_id: UUID,
    title: Optional[str] = None,
    created_by: Optional[UUID] = None,
) -> models.Session:
    s = models.Session(project_id=project_id, created_by=created_by, title=title or "")
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


def get_session(db: Session, session_id: UUID) -> Optional[models.Session]:
    return db.query(models.Session).filter(models.Session.id == session_id).first()


def list_sessions(
    db: Session, project_id: Optional[UUID] = None, limit: int = 50, offset: int = 0
) -> List[models.Session]:
    q = db.query(models.Session)
    if project_id:
        q = q.filter(models.Session.project_id == project_id)
    return (
        q.order_by(models.Session.created_at.desc()).limit(limit).offset(offset).all()
    )


def create_session_message(
    db: Session,
    session_id: UUID,
    role: str,
    content: str,
    prompt_id: Optional[UUID] = None,
    model: Optional[str] = None,
) -> models.SessionMessage:
    msg = models.SessionMessage(
        session_id=session_id,
        role=role,
        prompt_id=prompt_id,
        content=content,
        model=model,
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return msg


# Usage events
def log_usage_event(
    db: Session,
    user_id: Optional[UUID],
    project_id: Optional[UUID],
    session_message_id: Optional[UUID],
    model: str,
    tokens_prompt: int = 0,
    tokens_response: int = 0,
    cost_usd: float = 0.0,
    latency_ms: Optional[int] = None,
):
    ev = models.UsageEvent(
        user_id=user_id,
        project_id=project_id,
        session_message_id=session_message_id,
        model=model,
        tokens_prompt=tokens_prompt,
        tokens_response=tokens_response,
        cost_usd=cost_usd,
        latency_ms=latency_ms,
    )
    db.add(ev)
    db.commit()
    db.refresh(ev)
    return ev
