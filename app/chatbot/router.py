# File: app/chatbot/router.py
"""POST /chat — agentic chatbot endpoint."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.chatbot.agent import run_agent
from app.chatbot.llm import create_provider

router = APIRouter()

# Module-level provider — initialized once on first request
_provider = None


def _get_provider():
    global _provider
    if _provider is None:
        _provider = create_provider()
    return _provider


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000, description="User message")


class ChatResponse(BaseModel):
    response: str


@router.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest, db: Session = Depends(get_db)):
    """Send a message to the agentic chatbot.

    The agent may call internal tools (prediction, commentary, news)
    before composing a final response.
    """
    try:
        provider = _get_provider()
        result = run_agent(user_message=req.message, provider=provider, db=db)
        return ChatResponse(response=result)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
