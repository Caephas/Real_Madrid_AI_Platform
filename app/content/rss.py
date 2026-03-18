# File: app/content/rss.py
"""RSS feed fetcher and article categorizer.

Fetches from Managing Madrid RSS, categorizes via keyword matching (no spaCy),
and stores in PostgreSQL via SQLAlchemy.
"""

import hashlib
import logging
import re
from datetime import datetime, timezone
from html.parser import HTMLParser

import feedparser
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Article

logger = logging.getLogger("app.content")

RSS_URL = "https://www.managingmadrid.com/rss/current.xml"

# Keyword-based categorization — simple, fast, no ML dependency
_CATEGORY_RULES: list[tuple[str, list[str]]] = [
    ("Match Reports", ["match report", "match recap", "post-match", "full time", "final score",
                        "defeated", "victory", "beat", "drew", "lost to", "win over"]),
    ("Match Previews", ["preview", "match preview", "lineup", "predicted xi", "starting xi",
                        "team news", "pre-match", "ahead of"]),
    ("Transfers", ["transfer", "signing", "signs", "deal", "bid", "rumor", "target",
                   "contract", "extension", "renewal", "loan", "release clause", "fee"]),
    ("Tactical Analysis", ["tactical", "analysis", "formation", "pressing", "possession",
                           "build-up", "defensive", "attacking", "system", "how they play"]),
    ("Player News", ["injury", "injured", "doubtful", "sidelined", "return", "fitness",
                     "training", "academy", "debut", "milestone", "record", "goal scorer",
                     "captain", "coach", "manager", "praises", "reflects"]),
    ("Player Interviews", ["interview", "exclusive", "speaks", "talks", "told", "said",
                           "according to", "quotes", "managing madrid"]),
    ("Breaking News", ["breaking", "official", "confirmed", "announce", "just in",
                       "report", "latest"]),
]


def _categorize(title: str, content: str) -> str:
    """Classify article by keyword presence in title + content. O(categories * keywords)."""
    text = f"{title} {content}".lower()
    for category, keywords in _CATEGORY_RULES:
        if any(kw in text for kw in keywords):
            return category
    return "Uncategorized"


def _extract_image(html: str) -> str | None:
    """Pull the first <img src="..."> from RSS HTML content."""
    match = re.search(r'<img[^>]+src=["\']([^"\'>]+)["\']', html)
    return match.group(1) if match else None


class _HTMLStripper(HTMLParser):
    """Minimal HTML tag stripper."""
    def __init__(self):
        super().__init__()
        self._parts: list[str] = []
    def handle_data(self, data: str):
        self._parts.append(data)
    def get_text(self) -> str:
        return " ".join(self._parts).strip()


def _strip_html(html: str) -> str:
    """Remove HTML tags, return plain text."""
    s = _HTMLStripper()
    s.feed(html)
    return s.get_text()


def _make_article_id(title: str, link: str) -> str:
    """Deterministic article ID from title + link hash. Sanitized for DB storage."""
    raw = hashlib.sha256(f"{title}{link}".encode()).hexdigest()[:16]
    return re.sub(r"[^a-zA-Z0-9_-]", "_", raw)


def _parse_published(entry: dict) -> datetime | None:
    """Parse RSS published date. Returns None if unparseable."""
    published = entry.get("published_parsed")
    if published:
        try:
            from time import mktime
            return datetime.fromtimestamp(mktime(published), tz=timezone.utc)
        except (ValueError, OverflowError):
            pass
    return None


def fetch_and_store_articles(db: Session | None = None) -> int:
    """Fetch RSS feed, categorize articles, upsert into DB.

    Returns the number of new articles stored.

    If db is None, creates its own session (for APScheduler calls outside request context).
    """
    own_session = db is None
    if own_session:
        db = SessionLocal()

    try:
        feed = feedparser.parse(RSS_URL)
        logger.info("Fetched RSS: %d entries from %s", len(feed.entries), RSS_URL)

        stored = 0
        for entry in feed.entries:
            title = entry.get("title", "No Title")
            link = entry.get("link", "")
            article_id = entry.get("id") or _make_article_id(title, link)
            article_id = re.sub(r"[^a-zA-Z0-9_-]", "_", article_id)

            # Skip if already stored (upsert by checking existence)
            existing = db.get(Article, article_id)
            if existing:
                continue

            content_blocks = entry.get("content", [{}])
            raw_html = content_blocks[0].get("value", "") if content_blocks else ""
            # Fallback to summary if no content
            if not raw_html:
                raw_html = entry.get("summary", "")

            category = _categorize(title, raw_html)
            image_url = _extract_image(raw_html)
            clean_text = _strip_html(raw_html)

            article = Article(
                article_id=article_id,
                title=title,
                link=link,
                published=_parse_published(entry),
                content=clean_text,
                image_url=image_url,
                author=entry.get("author", "Managing Madrid"),
                category=category,
            )
            db.add(article)
            stored += 1

        db.commit()
        logger.info("Stored %d new articles", stored)
        return stored

    except Exception:
        db.rollback()
        logger.exception("Error fetching/storing RSS articles")
        return 0
    finally:
        if own_session:
            db.close()
