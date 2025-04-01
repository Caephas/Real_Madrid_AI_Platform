from fastapi import FastAPI
from mangum import Mangum
from pydantic import BaseModel
from app.api import chatbot_api

app = FastAPI()

class ChatRequest(BaseModel):
    prompt: str

@app.get("/")
def read_root():
    return {"message": "Real Madrid Chatbot (Gemini) API is running!"}


@app.post("/chat")
def chat_with_fan(request: ChatRequest):
    response = chatbot_api.generate_response(request.prompt)
    return {"response": response}

handler = Mangum(app)