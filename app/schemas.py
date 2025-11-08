# app/schemas.py
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel


# ---- Users ----
class UserCreate(BaseModel):
    email: str
    password: str
    name: Optional[str] = None


class UserOut(BaseModel):
    id: UUID
    email: str
    name: Optional[str] = None

    class Config:
        orm_mode = True


# ---- Projects ----
class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None


class ProjectOut(BaseModel):
    id: UUID
    name: str
    description: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        orm_mode = True


# ---- Prompts ----
class PromptCreate(BaseModel):
    project_id: UUID
    name: str
    template: str
    default_model: Optional[str] = None
    tags: Optional[List[str]] = None


class PromptOut(BaseModel):
    id: UUID
    project_id: UUID
    name: str
    template: str
    default_model: Optional[str] = None
    tags: Optional[List[str]] = None
    created_at: Optional[datetime] = None

    class Config:
        orm_mode = True


# ---- Sessions & Messages ----
class SessionCreate(BaseModel):
    project_id: UUID
    title: Optional[str] = None


class SessionOut(BaseModel):
    id: UUID
    project_id: UUID
    title: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        orm_mode = True


class SessionMessageCreate(BaseModel):
    role: str
    content: str
    prompt_id: Optional[UUID] = None
    model: Optional[str] = None


class SessionMessageOut(BaseModel):
    id: UUID
    session_id: UUID
    role: str
    content: str
    model: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        orm_mode = True
