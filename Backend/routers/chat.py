import logging
import time
from typing import AsyncGenerator

try:
    from fastapi import APIRouter, Depends
    from fastapi.responses import StreamingResponse
except Exception:
    from _compat_fastapi import APIRouter, Depends, StreamingResponse
from sqlalchemy.orm import Session

from constants import ROLE_ASSISTANT, ROLE_SYSTEM, ROLE_USER
from database import User
from prompts.system_prompt import build_system_prompt
from services.auth_service import get_current_user
from services.database_service import delete_chat_session, get_db, list_chat_sessions, load_chat_history, save_chat
from services.ollama_service import stream_chat
from services.rag_service import retrieve_context
from vector_db import ChatRequest

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/chat")
async def chat(request: ChatRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> StreamingResponse:
    user_message = request.message
    session_id = request.session_id
    start = time.perf_counter()
    context, retrieved_results = retrieve_context(user_message)
    elapsed = time.perf_counter() - start
    logger.info("RAG metrics: retrieved_documents=%d retrieval_time_seconds=%.3f", len(retrieved_results), elapsed)

    db_history = []
    if session_id:
        db_history = [{"role": message.role, "content": message.content} for message in load_chat_history(session_id, current_user.id, db)]

    messages = [{"role": ROLE_SYSTEM, "content": build_system_prompt(context)}, *db_history, {"role": ROLE_USER, "content": user_message}]
    full_response = ""

    async def event_generator() -> AsyncGenerator[str, None]:
        nonlocal full_response
        try:
            for content in stream_chat(messages):
                full_response += content
                yield content
        except Exception as error:
            logger.exception("Chat streaming failed")
            yield f"Error: {error}"
        finally:
            if session_id:
                save_chat(session_id, current_user.id, ROLE_USER, user_message, db)
                save_chat(session_id, current_user.id, ROLE_ASSISTANT, full_response, db)

    return StreamingResponse(event_generator(), media_type="text/plain")


@router.get("/chat/sessions")
async def list_sessions(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> list[dict[str, object]]:
    return list_chat_sessions(current_user.id, db)


@router.get("/chat/sessions/{session_id}")
async def get_session_messages(session_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> list[dict[str, object]]:
    return [{"id": str(message.id), "role": message.role, "content": message.content, "created_at": message.created_at.isoformat() if message.created_at else None} for message in load_chat_history(session_id, current_user.id, db)]


@router.delete("/chat/sessions/{session_id}")
async def delete_session(session_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> dict[str, str]:
    delete_chat_session(session_id, current_user.id, db)
    return {"status": "deleted"}
