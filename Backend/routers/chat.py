try:
    from fastapi import APIRouter, Depends, HTTPException
    from fastapi.responses import StreamingResponse
except Exception:
    from Backend._compat_fastapi import APIRouter, Depends, HTTPException, StreamingResponse

from typing import List
from sqlalchemy.orm import Session
import time

from Backend.database import User
from Backend.services.auth_service import get_current_user
from Backend.services.database_service import get_db, save_chat, load_chat_history, list_chat_sessions, delete_chat_session
from Backend.services.rag_service import retrieve_context
from Backend.services.ollama_service import stream_chat
from Backend.vector_db import ChatRequest

router = APIRouter()


@router.post("/chat")
async def chat(request: ChatRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    user_message = request.message
    session_id = request.session_id

    start = time.perf_counter()
    context, retrieved_results = retrieve_context(user_message)
    elapsed = time.perf_counter() - start

    print("\n========== RAG METRICS ==========")
    print(f"Retrieved Documents : {len(retrieved_results)}")
    print(f"Retrieval Time      : {elapsed:.3f} seconds")
    print("=================================\n")

    system_prompt = f'''=== RETRIEVED INTELLIGENCE ===
{context}
==============================

You are an Elite Cybersecurity Analyst. You are professional, concise, and helpful.

CRITICAL RULES YOU MUST FOLLOW:
1. NO ROBOT SPEAK: NEVER say "Based on the retrieved intelligence", "According to my knowledge", or "The provided information says". Just state the facts confidently as your own knowledge.
2. STRICT FORMATTING: You MUST use emojis (✅, 🔹, ⚠️, 🛡️) for ALL bullet points. Do not use plain asterisks (*).
3. SMALL TALK: If the user just says hello or introduces themselves, greet them warmly. DO NOT bring up malware unless they explicitly ask.
4. MEMORY PROTOCOL: You have access to the user's Chat History. If the user asks you to summarize a past answer or recall something you ALREADY discussed, you MUST use the Chat History to answer. Never claim you didn't discuss something if it is in your history.
'''

    db_history = []
    if session_id:
        messages = load_chat_history(session_id, current_user.id, db)
        for m in messages:
            db_history.append({"role": m.role, "content": m.content})

    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(db_history)
    messages.append({"role": "user", "content": user_message})

    full_response = ""

    async def event_generator():
        nonlocal full_response
        try:
            for content in stream_chat(messages):
                full_response += content
                yield content
        except Exception as e:
            yield f"Error: {e}"
        finally:
            if session_id:
                save_chat(session_id, current_user.id, "user", user_message, db)
                save_chat(session_id, current_user.id, "assistant", full_response, db)

    return StreamingResponse(event_generator(), media_type="text/plain")


@router.get("/chat/sessions")
async def list_sessions(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return list_chat_sessions(current_user.id, db)


@router.get("/chat/sessions/{session_id}")
async def get_session_messages(session_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    messages = load_chat_history(session_id, current_user.id, db)
    return [
        {
            "id": str(m.id),
            "role": m.role,
            "content": m.content,
            "created_at": m.created_at.isoformat() if m.created_at else None
        }
        for m in messages
    ]


@router.delete("/chat/sessions/{session_id}")
async def delete_session(session_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    delete_chat_session(session_id, current_user.id, db)
    return {"status": "deleted"}
