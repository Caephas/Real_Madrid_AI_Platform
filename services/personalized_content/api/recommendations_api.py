from fastapi import FastAPI
from dynamodb import get_user_preferences, get_articles_by_category

app = FastAPI()

@app.get("/")
def root():
    """ Root endpoint to confirm service is running """
    return {"message": "Personalized Content API is running!"}

@app.get("/recommendations/{user_id}")
def get_recommendations(user_id: str):
    """
    Fetch personalized recommendations for a user from DynamoDB.
    """
    preferences = get_user_preferences(user_id)

    if not preferences:
        return {"error": "User not found or has no preferences"}

    # Gather all articles for preferred categories
    filtered_articles = []
    for category in preferences:
        articles = get_articles_by_category(category)
        filtered_articles.extend(articles)

    # Sort by published date (if available)
    sorted_articles = sorted(
        filtered_articles,
        key=lambda x: x.get("published", ""),
        reverse=True
    )

    return {
        "user_id": user_id,
        "recommendations": sorted_articles
    }