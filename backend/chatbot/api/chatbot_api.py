from fastapi import FastAPI
from pydantic import BaseModel

from backend.chatbot.utils.chatbot_responses import run_llama_query

app = FastAPI()

class ChatRequest(BaseModel):
    user_input: str

@app.get("/")
def root():
    return {"message": "Real Madrid Chatbot using Llama.cpp is running!"}

@app.post("/chat")
def chat_with_fan(request: ChatRequest):
    user_input = request.user_input
    response = run_llama_query(user_input)  # Call the updated function
    return {"user_input": user_input, "response": response}