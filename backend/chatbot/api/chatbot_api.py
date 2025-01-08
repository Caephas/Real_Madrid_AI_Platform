from fastapi import FastAPI
from backend.chatbot.utils.chatbot_responses import get_chatbot_response

app = FastAPI()

@app.get("/")
def root():
    return {"message": "Real Madrid Chatbot is running!"}

@app.post("/chat")
def chat_with_fan(user_input: str):
    """
    Handle user input and return chatbot response.
    """
    response = get_chatbot_response(user_input)
    return {"user_input": user_input, "response": response}