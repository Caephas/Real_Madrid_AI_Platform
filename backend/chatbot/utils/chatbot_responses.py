import requests

def get_chatbot_response(user_input: str) -> str:
    """
    Generate a chatbot response based on user input.
    """
    user_input = user_input.lower()

    # 1. General Info
    if "captain" in user_input:
        return "Real Madrid's captain is Sergio Ramos."  # Example, update with dynamic logic
    elif "trophies" in user_input:
        return "Real Madrid has won 35 La Liga titles and 14 UEFA Champions League trophies."

    # 2. Match Info
    elif "next match" in user_input:
        # Replace with real-time match info logic
        return "Real Madrid's next match is against Barcelona on Sunday at 8 PM."
    elif "last match" in user_input:
        # Replace with last match result logic
        return "Real Madrid's last match ended in a 2-1 victory over Atletico Madrid."

    # 3. Match Prediction
    elif "prediction" in user_input:
        # Example of match prediction
        prediction = {"outcome": "Win"}  # Replace with actual prediction logic
        return f"The predicted outcome for the next match is: {prediction['outcome']}."

    # 4. Content Recommendations
    elif "news" in user_input or "articles" in user_input:
        # Replace with content personalization logic
        articles = ["Real Madrid signs new player!", "Match preview: Real Madrid vs. Barcelona"]
        return f"Here are the latest news articles about Real Madrid: {', '.join(articles)}"

    # Default response
    else:
        return "I'm sorry, I didn't understand that. Can you try rephrasing?"