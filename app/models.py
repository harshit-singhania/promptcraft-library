# app/models.py
import sqlalchemy as sa
from sqlalchemy import (JSON, TIMESTAMP, BigInteger, Boolean, Column, Integer,
                        Numeric, Text)
from sqlalchemy.dialects.postgresql import ARRAY, UUID

from .db import Base


def uuid_col(name=None, primary_key=False, nullable=False, default=True):
    if default:
        return Column(
            UUID(as_uuid=True),
            primary_key=primary_key,
            server_default=sa.text("gen_random_uuid()"),
            nullable=nullable,
        )
    return Column(UUID(as_uuid=True), primary_key=primary_key, nullable=nullable)


class User(Base):
    __tablename__ = "users"
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=sa.text("gen_random_uuid()"),
    )
    email = Column(Text, unique=True, nullable=False)
    name = Column(Text)
    hashed_password = Column(Text)
    auth_provider = Column(Text)
    created_at = Column(TIMESTAMP(timezone=True), server_default=sa.text("now()"))
    updated_at = Column(TIMESTAMP(timezone=True), server_default=sa.text("now()"))


class Team(Base):
    __tablename__ = "teams"
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=sa.text("gen_random_uuid()"),
    )
    name = Column(Text, nullable=False)
    owner_id = Column(UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=sa.text("now()"))


class Project(Base):
    __tablename__ = "projects"
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=sa.text("gen_random_uuid()"),
    )
    team_id = Column(UUID(as_uuid=True), sa.ForeignKey("teams.id"), nullable=True)
    name = Column(Text, nullable=False)
    description = Column(Text)
    created_at = Column(TIMESTAMP(timezone=True), server_default=sa.text("now()"))


class Prompt(Base):
    __tablename__ = "prompts"
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=sa.text("gen_random_uuid()"),
    )
    project_id = Column(UUID(as_uuid=True), sa.ForeignKey("projects.id"), nullable=True)
    owner_id = Column(UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True)
    name = Column(Text, nullable=False)
    template = Column(Text, nullable=False)
    default_model = Column(Text)
    tags = Column(ARRAY(Text), server_default="{}")
    latest_version_id = Column(UUID(as_uuid=True), nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=sa.text("now()"))
    updated_at = Column(TIMESTAMP(timezone=True), server_default=sa.text("now()"))


class PromptVersion(Base):
    __tablename__ = "prompt_versions"
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=sa.text("gen_random_uuid()"),
    )
    prompt_id = Column(UUID(as_uuid=True), sa.ForeignKey("prompts.id"), nullable=False)
    version_number = Column(Integer, nullable=False)
    template = Column(Text, nullable=False)
    diff = Column(Text)
    created_by = Column(UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=sa.text("now()"))


class Session(Base):
    __tablename__ = "sessions"
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=sa.text("gen_random_uuid()"),
    )
    project_id = Column(UUID(as_uuid=True), sa.ForeignKey("projects.id"), nullable=True)
    created_by = Column(UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True)
    title = Column(Text)
    tags = Column(ARRAY(Text), server_default="{}")
    # use a different Python attribute name to avoid collision with SQLAlchemy Base.metadata
    metadata_json = Column("metadata", JSON, server_default="{}")
    created_at = Column(TIMESTAMP(timezone=True), server_default=sa.text("now()"))
    updated_at = Column(TIMESTAMP(timezone=True), server_default=sa.text("now()"))


class SessionMessage(Base):
    __tablename__ = "session_messages"
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=sa.text("gen_random_uuid()"),
    )
    session_id = Column(
        UUID(as_uuid=True), sa.ForeignKey("sessions.id"), nullable=False
    )
    role = Column(Text, nullable=False)  # 'user' | 'assistant' | 'system'
    prompt_id = Column(UUID(as_uuid=True), sa.ForeignKey("prompts.id"), nullable=True)
    prompt_version_id = Column(
        UUID(as_uuid=True), sa.ForeignKey("prompt_versions.id"), nullable=True
    )
    content = Column(Text, nullable=False)
    model = Column(Text, nullable=True)
    tokens_prompt = Column(Integer, default=0)
    tokens_response = Column(Integer, default=0)
    cost_usd = Column(Numeric(12, 6), default=0)
    embed_indexed = Column(Boolean, default=False)
    s3_raw_path = Column(Text, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=sa.text("now()"))


class UsageEvent(Base):
    __tablename__ = "usage_events"
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=sa.text("gen_random_uuid()"),
    )
    user_id = Column(UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True)
    project_id = Column(UUID(as_uuid=True), sa.ForeignKey("projects.id"), nullable=True)
    session_message_id = Column(
        UUID(as_uuid=True), sa.ForeignKey("session_messages.id"), nullable=True
    )
    model = Column(Text, nullable=False)
    tokens_prompt = Column(Integer, default=0)
    tokens_response = Column(Integer, default=0)
    cost_usd = Column(Numeric(12, 6), default=0)
    latency_ms = Column(Integer, nullable=True)
    feedback = Column(Integer, nullable=True)  # -1/0/1
    created_at = Column(TIMESTAMP(timezone=True), server_default=sa.text("now()"))


class Embedding(Base):
    __tablename__ = "embeddings"
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=sa.text("gen_random_uuid()"),
    )
    session_message_id = Column(
        UUID(as_uuid=True), sa.ForeignKey("session_messages.id"), nullable=False
    )
    vector_id = Column(Text, nullable=True)
    text_snippet = Column(Text, nullable=True)
    namespace = Column(Text, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=sa.text("now()"))


class File(Base):
    __tablename__ = "files"
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=sa.text("gen_random_uuid()"),
    )
    project_id = Column(UUID(as_uuid=True), sa.ForeignKey("projects.id"), nullable=True)
    uploader_id = Column(UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True)
    s3_path = Column(Text, nullable=False)
    size_bytes = Column(BigInteger, nullable=True)
    mime_type = Column(Text, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=sa.text("now()"))


class UsageAggregate(Base):
    __tablename__ = "usage_aggregates"
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=sa.text("gen_random_uuid()"),
    )
    project_id = Column(UUID(as_uuid=True), sa.ForeignKey("projects.id"), nullable=True)
    date = Column(sa.Date, nullable=False)
    tokens_total = Column(BigInteger, default=0)
    cost_total = Column(Numeric(14, 6), default=0)
    created_at = Column(TIMESTAMP(timezone=True), server_default=sa.text("now()"))


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=sa.text("gen_random_uuid()"),
    )
    actor_id = Column(UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True)
    action = Column(Text, nullable=False)
    resource_type = Column(Text, nullable=True)
    resource_id = Column(UUID(as_uuid=True), nullable=True)
    payload = Column(JSON, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=sa.text("now()"))
