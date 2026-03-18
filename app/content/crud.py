# File: app/content/crud.py
"""SQLAlchemy queries for articles and users."""

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.models import Article, User


def get_articles(
    db: Session,
    category: str | None = None,
    limit: int = 20,
) -> list[Article]:
    """Fetch articles, optionally filtered by category, sorted by publish date.

    O(n) scan with index on category + published.
    """
    query = db.query(Article)
    if category:
        query = query.filter(Article.category == category)
    return query.order_by(desc(Article.published)).limit(limit).all()


def get_user_preferences(db: Session, user_id: str) -> list[str]:
    """Get a user's preferred categories. Returns empty list if user not found."""
    user = db.get(User, user_id)
    if not user or not user.preferences:
        return []
    return user.preferences.get("categories", [])


def get_recommendations(
    db: Session,
    user_id: str,
    limit: int = 20,
) -> list[Article]:
    """Fetch articles matching a user's preferred categories, sorted by date.

    Falls back to all articles if user has no preferences.
    """
    prefs = get_user_preferences(db, user_id)
    if not prefs:
        return get_articles(db, limit=limit)

    return (
        db.query(Article)
        .filter(Article.category.in_(prefs))
        .order_by(desc(Article.published))
        .limit(limit)
        .all()
    )
