# File: app/models.py
"""SQLAlchemy ORM models for all database tables."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, Index, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _uuid() -> str:
    return str(uuid.uuid4())


class MatchEvent(Base):
    """Live match events fetched from API-Football."""

    __tablename__ = "match_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    team: Mapped[str] = mapped_column(String(100), index=True)
    type: Mapped[str] = mapped_column(String(50))
    player: Mapped[str] = mapped_column(String(100))
    minute: Mapped[int]
    raw_event: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class Article(Base):
    """News articles ingested from RSS feeds."""

    __tablename__ = "articles"
    __table_args__ = (
        Index("ix_articles_category", "category"),
        Index("ix_articles_published", "published"),
    )

    article_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    category: Mapped[str] = mapped_column(String(50), default="Uncategorized")
    title: Mapped[str] = mapped_column(String(500))
    link: Mapped[str] = mapped_column(String(1000))
    published: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    author: Mapped[str | None] = mapped_column(String(200), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class User(Base):
    """User profiles with preference data."""

    __tablename__ = "users"

    user_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    preferences: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class TeamStats(Base):
    """Rolling average stats per team, updated by the pipeline after each scrape."""

    __tablename__ = "team_stats"

    team_name: Mapped[str] = mapped_column(String(100), primary_key=True)
    gf_rolling: Mapped[float] = mapped_column(Float, default=0.0)
    ga_rolling: Mapped[float] = mapped_column(Float, default=0.0)
    sh_rolling: Mapped[float] = mapped_column(Float, default=0.0)
    sot_rolling: Mapped[float] = mapped_column(Float, default=0.0)
    dist_rolling: Mapped[float] = mapped_column(Float, default=0.0)
    fk_rolling: Mapped[float] = mapped_column(Float, default=0.0)
    pk_rolling: Mapped[float] = mapped_column(Float, default=0.0)
    pkatt_rolling: Mapped[float] = mapped_column(Float, default=0.0)
    xg_rolling: Mapped[float] = mapped_column(Float, default=0.0)
    xga_rolling: Mapped[float] = mapped_column(Float, default=0.0)
    poss_rolling: Mapped[float] = mapped_column(Float, default=0.0)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class ChatMessage(Base):
    """Persistent chatbot conversation history."""

    __tablename__ = "chat_messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    conversation_id: Mapped[str] = mapped_column(String(100), index=True)
    role: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
