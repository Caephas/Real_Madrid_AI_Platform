# File: app/content/router.py
"""Content endpoints: articles listing, manual fetch trigger, and recommendations."""

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.content.crud import get_articles, get_recommendations
from app.content.rss import fetch_and_store_articles

router = APIRouter()


class ArticleResponse(BaseModel):
    article_id: str
    title: str
    category: str
    link: str
    published: str | None
    content: str | None
    image_url: str | None
    author: str | None

    model_config = {"from_attributes": True}


class RecommendationResponse(BaseModel):
    user_id: str
    recommendations: list[ArticleResponse]


@router.get("/articles", response_model=list[ArticleResponse])
def list_articles(
    category: str | None = Query(None, description="Filter by category"),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """List articles, optionally filtered by category."""
    articles = get_articles(db, category=category, limit=limit)
    return [
        ArticleResponse(
            article_id=a.article_id,
            title=a.title,
            category=a.category,
            link=a.link,
            published=a.published.isoformat() if a.published else None,
            content=a.content,
            image_url=a.image_url,
            author=a.author,
        )
        for a in articles
    ]


@router.post("/articles/fetch")
def trigger_fetch(db: Session = Depends(get_db)):
    """Manually trigger RSS fetch. Also called by APScheduler every 6 hours."""
    count = fetch_and_store_articles(db)
    return {"fetched": count}


@router.get("/recommendations/{user_id}", response_model=RecommendationResponse)
def user_recommendations(
    user_id: str,
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Get personalized article recommendations based on user preferences."""
    articles = get_recommendations(db, user_id=user_id, limit=limit)
    return RecommendationResponse(
        user_id=user_id,
        recommendations=[
            ArticleResponse(
                article_id=a.article_id,
                title=a.title,
                category=a.category,
                link=a.link,
                published=a.published.isoformat() if a.published else None,
                content=a.content,
                image_url=a.image_url,
                author=a.author,
            )
            for a in articles
        ],
    )
