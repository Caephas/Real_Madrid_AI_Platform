"""Chatbot endpoints: POST /chat, POST /chat/stream (SSE), conversation history."""

import json
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.database import get_db
from app.chatbot.agent import run_agent, run_agent_stream
from app.chatbot.llm import create_provider
from app.models import ChatMessage

logger = logging.getLogger("app.chatbot")

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
    conversation_id: str | None = Field(
        None, max_length=100, description="Conversation to continue"
    )
    user_id: str | None = Field(None, max_length=100, description="Optional user identifier")


class ChatResponse(BaseModel):
    response: str
    conversation_id: str


class HistoryMessage(BaseModel):
    role: str
    content: str
    created_at: str | None = None


class HistoryResponse(BaseModel):
    conversation_id: str
    messages: list[HistoryMessage]


def _new_conversation_id() -> str:
    return str(uuid.uuid4())


def _load_history(
    db: Session,
    conversation_id: str,
    user_id: str | None = None,
    limit: int = 8,
) -> list[dict[str, str]]:
    """Recent messages for a conversation, oldest first."""
    query = (
        db.query(ChatMessage)
        .filter(ChatMessage.conversation_id == conversation_id)
        .order_by(desc(ChatMessage.created_at))
        .limit(limit)
    )
    if user_id:
        query = query.filter(ChatMessage.user_id == user_id)
    rows = query.all()
    return [{"role": r.role, "content": r.content} for r in reversed(rows)]


def _store_message(
    db: Session,
    conversation_id: str,
    role: str,
    content: str,
    user_id: str | None = None,
) -> None:
    db.add(
        ChatMessage(
            conversation_id=conversation_id,
            user_id=user_id,
            role=role,
            content=content,
        )
    )
    db.commit()


@router.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest, db: Session = Depends(get_db)):
    """Send a message to the agentic chatbot with conversation memory.

    Pass an existing `conversation_id` to continue a thread. The agent may
    call internal tools (prediction, commentary, news) before answering.
    """
    conversation_id = req.conversation_id or _new_conversation_id()
    history = _load_history(db, conversation_id, user_id=req.user_id) if req.conversation_id else []

    try:
        provider = _get_provider()
        result = run_agent(
            user_message=req.message,
            provider=provider,
            db=db,
            history=history,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))

    _store_message(db, conversation_id, "user", req.message, user_id=req.user_id)
    _store_message(db, conversation_id, "assistant", result, user_id=req.user_id)
    return ChatResponse(response=result, conversation_id=conversation_id)


def _sse(event: dict) -> str:
    return f"data: {json.dumps(event)}\n\n"


@router.post("/chat/stream")
def chat_stream(req: ChatRequest, db: Session = Depends(get_db)):
    """Stream the agent's answer over SSE.

    Events: {"type":"delta","content":...} | {"type":"tool","name":...}
            | {"type":"done","conversation_id":...} | {"type":"error","message":...}
    """
    conversation_id = req.conversation_id or _new_conversation_id()
    history = _load_history(db, conversation_id, user_id=req.user_id) if req.conversation_id else []

    def event_stream():
        collected: list[str] = []
        try:
            provider = _get_provider()
            for event in run_agent_stream(
                user_message=req.message,
                provider=provider,
                db=db,
                history=history,
            ):
                if event["type"] == "delta":
                    collected.append(event["content"])
                yield _sse(event)
            yield _sse({"type": "done", "conversation_id": conversation_id})

            # Persist once the stream completes
            _store_message(db, conversation_id, "user", req.message, user_id=req.user_id)
            _store_message(
                db, conversation_id, "assistant", "".join(collected), user_id=req.user_id
            )
        except RuntimeError as e:
            yield _sse({"type": "error", "message": str(e)})
        except Exception as e:  # never leave the client hanging
            logger.exception("Chat stream failed")
            yield _sse({"type": "error", "message": f"Internal error: {e}"})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@router.get("/conversations/{conversation_id}", response_model=HistoryResponse)
def conversation_history(conversation_id: str, db: Session = Depends(get_db)):
    """Return the message history for a conversation."""
    rows = (
        db.query(ChatMessage)
        .filter(ChatMessage.conversation_id == conversation_id)
        .order_by(ChatMessage.created_at)
        .all()
    )
    return HistoryResponse(
        conversation_id=conversation_id,
        messages=[
            HistoryMessage(
                role=r.role,
                content=r.content,
                created_at=r.created_at.isoformat() if r.created_at else None,
            )
            for r in rows
        ],
    )


class ConversationSummary(BaseModel):
    conversation_id: str
    last_message: str
    message_count: int
    updated_at: str | None = None


class ConversationsResponse(BaseModel):
    user_id: str | None
    conversations: list[ConversationSummary]


@router.get("/conversations", response_model=ConversationsResponse)
def list_conversations(
    user_id: str | None = Query(None, description="Scope to a user (device id)"),
    db: Session = Depends(get_db),
):
    """List conversations (optionally for one user), newest first."""
    from sqlalchemy import func

    query = (
        db.query(
            ChatMessage.conversation_id,
            func.max(ChatMessage.created_at).label("updated_at"),
            func.count(ChatMessage.id).label("message_count"),
        )
        .group_by(ChatMessage.conversation_id)
        .order_by(desc(func.max(ChatMessage.created_at)))
    )
    if user_id:
        query = query.filter(ChatMessage.user_id == user_id)

    summaries = []
    for conversation_id, updated_at, message_count in query.all():
        last = (
            db.query(ChatMessage.content)
            .filter(ChatMessage.conversation_id == conversation_id)
            .order_by(desc(ChatMessage.created_at))
            .first()
        )
        summaries.append(
            ConversationSummary(
                conversation_id=conversation_id,
                last_message=(last[0] if last else "")[:120],
                message_count=int(message_count),
                updated_at=updated_at.isoformat() if updated_at else None,
            )
        )

    return ConversationsResponse(user_id=user_id, conversations=summaries)
