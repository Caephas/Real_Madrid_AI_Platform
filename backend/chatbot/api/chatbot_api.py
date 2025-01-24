from fastapi import FastAPI
from pydantic import BaseModel
from gradio_client import Client


# Initialize FastAPI
app = FastAPI()

# Hugging Face Space name
# TODO: unsloth/gemma-2b-bnb-4bit. The test model I trained, doesnt work well for this use case.
SPACE_NAME = "Caephas/real-madrid-fact"

# Initialize Gradio Client
client = Client(SPACE_NAME)

# Request schema
class ChatRequest(BaseModel):
    user_input: str

# Root endpoint
@app.get("/")
def root():
    return {"message": "Real Madrid Chatbot API is running!"}

# Chat endpoint
@app.post("/api/chatbot/chat")
def chat_with_user(request: ChatRequest):
    try:
        # Get user input
        user_input = request.user_input

        # Call the Hugging Face Space
        result = client.predict(
            message=user_input,
            history=[],  # TODO: Customize to maintain chat history
            api_name="/respond"
        )

        # Extract and return the response
        response = result[1][-1]["content"]  # Get the latest assistant's response
        return {"user_input": user_input, "response": response}

    except Exception as e:
        return {"error": str(e)}