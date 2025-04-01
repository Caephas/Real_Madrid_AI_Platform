from pydantic import BaseModel
import google.generativeai as genai
import logging
import os


logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Load Gemini API key from environment variable
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
genai.configure(api_key=GEMINI_API_KEY)

# Load Gemini model
model = genai.GenerativeModel("gemini-2.0-flash-lite")

class ChatRequest(BaseModel):
    user_input: str

def generate_response(user_input: str) -> str:
    try:
        prompt = f"""
You are an expert assistant that ONLY answers questions related to Real Madrid Football Club.
- If the question is not about Real Madrid, respond with: "I'm only able to answer Real Madrid-related questions."
- Answer clearly, concisely, and accurately.
- Do not make up facts.

Question:
{user_input}
        """
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        logger.error(f"Gemini API error: {str(e)}", exc_info=True)
        return "Sorry, I couldn't generate a response."
    