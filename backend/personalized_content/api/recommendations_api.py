import feedparser
from fastapi import FastAPI
from backend.shared.firestore import get_firestore

app = FastAPI()

db = get_firestore()

@app.get("/")
def root():
    """ Root endpoint to confirm service is running """
    return {"message": "Personalized Content API is running!"}

@app.get("/recommendations/{user_id}")
def get_recommendations(user_id: str):
    """
    Fetch personalized recommendations for a user.
    Currently, retrieves user preferences stored in Firestore.
    """
    # Fetch user preferences from Firestore
    user_doc = db.collection("USERS").document(user_id).get()
    if not user_doc.exists:
        return {"error": "User not found"}

    user_data = user_doc.to_dict()
    preferences: list[str] = user_data.get("preferences", [])

    # Fetch articles matching the user's preferences
    articles_ref = db.collection("ARTICLES")
    filtered_articles = []

    for category in preferences:
        query = articles_ref.where("category", "==", category).stream()
        for article in query:
            article_data = article.to_dict()
            filtered_articles.append(article_data)

        # Sort articles by published date (descending)
    sorted_articles = sorted(
        filtered_articles,
        key=lambda x: x.get("published", ""),
        reverse=True
    )

    # Return sorted articles
    return {
        "user_id": user_id,
        "recommendations": sorted_articles
    }