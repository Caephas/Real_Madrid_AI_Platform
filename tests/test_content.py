# File: tests/test_content.py
"""Unit tests for the content module."""

import pytest

from app.content.rss import _categorize, _make_article_id
from app.content.crud import get_articles, get_user_preferences, get_recommendations
from app.models import Article, User


# --- Categorization tests ---


def test_categorize_transfer():
    assert _categorize("Transfer News", "Madrid signing a new player") == "Transfers"


def test_categorize_match_preview():
    assert _categorize("Match Preview", "The predicted lineup for the match") == "Match Previews"


def test_categorize_interview():
    assert _categorize("Player Feature", "Exclusive interview with Vini Jr") == "Player Interviews"


def test_categorize_breaking():
    assert _categorize("Official announcement", "breaking confirmed") == "Breaking News"


def test_categorize_fallback():
    assert _categorize("Random Title", "Some generic content") == "Uncategorized"


# --- Article ID tests ---


def test_make_article_id_deterministic():
    id1 = _make_article_id("Title A", "https://example.com/1")
    id2 = _make_article_id("Title A", "https://example.com/1")
    assert id1 == id2


def test_make_article_id_different_inputs():
    id1 = _make_article_id("Title A", "https://example.com/1")
    id2 = _make_article_id("Title B", "https://example.com/2")
    assert id1 != id2


# --- CRUD tests ---


@pytest.fixture
def seed_articles(db_session):
    """Seed DB with test articles."""
    articles = [
        Article(article_id="a1", title="Transfer News", category="Transfers", link="https://example.com/1", content="text"),
        Article(article_id="a2", title="Match Preview", category="Match Previews", link="https://example.com/2", content="text"),
        Article(article_id="a3", title="Breaking", category="Breaking News", link="https://example.com/3", content="text"),
    ]
    for a in articles:
        db_session.add(a)
    db_session.commit()
    return articles


def test_get_articles_all(db_session, seed_articles):
    articles = get_articles(db_session)
    assert len(articles) == 3


def test_get_articles_filtered(db_session, seed_articles):
    articles = get_articles(db_session, category="Transfers")
    assert len(articles) == 1
    assert articles[0].article_id == "a1"


def test_get_articles_limit(db_session, seed_articles):
    articles = get_articles(db_session, limit=2)
    assert len(articles) == 2


def test_get_user_preferences_missing_user(db_session):
    prefs = get_user_preferences(db_session, "nonexistent")
    assert prefs == []


def test_get_user_preferences_valid(db_session):
    user = User(user_id="u1", preferences={"categories": ["Transfers", "Breaking News"]})
    db_session.add(user)
    db_session.commit()

    prefs = get_user_preferences(db_session, "u1")
    assert prefs == ["Transfers", "Breaking News"]


def test_get_recommendations_with_prefs(db_session, seed_articles):
    user = User(user_id="u2", preferences={"categories": ["Transfers"]})
    db_session.add(user)
    db_session.commit()

    recs = get_recommendations(db_session, "u2")
    assert len(recs) == 1
    assert recs[0].category == "Transfers"


def test_get_recommendations_no_prefs(db_session, seed_articles):
    """Users without preferences get all articles."""
    recs = get_recommendations(db_session, "unknown_user")
    assert len(recs) == 3
