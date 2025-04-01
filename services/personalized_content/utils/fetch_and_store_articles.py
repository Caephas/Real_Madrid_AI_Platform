from hashlib import sha256
import feedparser
import re
import spacy
import os
import boto3
from botocore.exceptions import ClientError

# Environment variable for table name
TABLE_NAME = os.environ.get("DYNAMODB_ARTICLE_TABLE", "articles")

# Initialize DynamoDB
dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(TABLE_NAME)

# Initialize spaCy model
nlp = spacy.load("en_core_web_sm")

def categorize_article(content):
    """Categorize an article based on its text content."""
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

def fetch_and_store_articles():
    rss_url = "https://www.managingmadrid.com/rss/current.xml"
    feed = feedparser.parse(rss_url)

    print(f"Feed title: {feed.feed.get('title', 'No Title')}")
    print(f"Number of entries: {len(feed.entries)}")

    for entry in feed.entries:
        # Generate article ID
        article_id = entry.get("id")
        if not article_id:
            article_id = sha256((entry.get("title", "") + entry.get("link", "")).encode()).hexdigest()
        article_id = re.sub(r"[^a-zA-Z0-9_-]", "_", article_id)

        print(f"Storing article with ID: {article_id}")

        content = entry.get("content", [{}])[0].get("value", "No Content")
        category = categorize_article(content)

        article_data = {
            "article_id": article_id,
            "title": entry.get("title", "No Title"),
            "link": entry.get("link", "No Link"),
            "published": entry.get("published", "No Date"),
            "content": content,
            "author": entry.get("author", "Unknown Author"),
            "category": category,
        }

        try:
            table.put_item(Item=article_data)
        except ClientError as e:
            print(f"Error storing article {article_id}: {e}")

    print(f"Fetched and stored {len(feed.entries)} articles.")


fetch_and_store_articles()