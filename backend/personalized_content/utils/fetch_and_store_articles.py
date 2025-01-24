from hashlib import sha256
import feedparser
from backend.shared.firestore import get_firestore
import re
import spacy


# Firestore instance
db = get_firestore()

# Initialize spaCy model
nlp = spacy.load("en_core_web_sm")

def categorize_article(content):
    """
    Categorize an article based on its text content.
    """
    doc = nlp(content.lower())
    if "match" in doc.text or "preview" in doc.text:
        return "Match Previews"
    elif "transfer" in doc.text or "signing" in doc.text:
        return "Transfers"
    elif "interview" in doc.text:
        return "Player Interviews"
    elif "breaking" in doc.text or "news" in doc.text:
        return "Breaking News"
    else:
        return "Uncategorized"

#TODO: Implement multiple news sources like Google News API or any other Real Madrid news source
#TODO: implement cron jobs for automating news fetching, set up user interaction tracking and advanced recommendations
def fetch_and_store_articles():
    rss_url = "https://www.managingmadrid.com/rss/current.xml"
    feed = feedparser.parse(rss_url)

    print(f"Feed title: {feed.feed.get('title', 'No Title')}")
    print(f"Number of entries: {len(feed.entries)}")

    articles_collection = db.collection("ARTICLES")

    for entry in feed.entries:
        # Generate or sanitize article ID
        article_id = entry.get("id", None)
        if not article_id:
            article_id = sha256((entry.get("title", "") + entry.get("link", "")).encode()).hexdigest()
        article_id = re.sub(r"[^a-zA-Z0-9_-]", "_", article_id)

        print(f"Storing article with ID: {article_id}")
        # Extract content and categorize it
        content = entry.get("content", [{}])[0].get("value", "No Content")
        category = categorize_article(content)

        # Prepare article data
        article_data = {
            "title": entry.get("title", "No Title"),
            "link": entry.get("link", "No Link"),
            "published": entry.get("published", "No Date"),
            "content": entry.get("content", [{}])[0].get("value", "No Content"),
            "author": entry.get("author", "Unknown Author"),
            'category': category,
        }

        # Store in Firestore
        articles_collection.document(article_id).set(article_data)

    print(f"Fetched and stored {len(feed.entries)} articles.")


fetch_and_store_articles()