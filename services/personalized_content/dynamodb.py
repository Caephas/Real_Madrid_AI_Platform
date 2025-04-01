import os
import boto3
from boto3.dynamodb.conditions import Key
from decimal import Decimal
from typing import List, Dict

# Initialize DynamoDB client and resource
dynamodb = boto3.resource("dynamodb")

ARTICLE_TABLE = os.getenv("DYNAMODB_ARTICLE_TABLE", "articles")
USER_TABLE = os.getenv("DYNAMODB_USER_TABLE", "users")

article_table = dynamodb.Table(ARTICLE_TABLE)
user_table = dynamodb.Table(USER_TABLE)

def store_article(article_id: str, article_data: Dict):
    """Store a single article into the DynamoDB table."""
    article_data["article_id"] = article_id
    article_table.put_item(Item=article_data)

def get_user_preferences(user_id: str) -> List[str]:
    """Retrieve user preferences by user_id."""
    response = user_table.get_item(Key={"user_id": user_id})
    item = response.get("Item")
    return item.get("preferences", []) if item else []

def get_articles_by_category(category: str) -> List[Dict]:
    """Retrieve articles by category."""
    response = article_table.query(
        IndexName="category-index",
        KeyConditionExpression=Key("category").eq(category)
    )
    return response.get("Items", [])
