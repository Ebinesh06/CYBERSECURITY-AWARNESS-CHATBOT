# ============================================
# CHAT ENDPOINTS
# ============================================
from fastapi.responses import StreamingResponse

from fastapi.responses import StreamingResponse

from Backend.database import SessionLocal
from Backend.main import get_current_user
from services.rag_service import retrieve_context
from services.ollama_service import stream_chat
import time
from vector_db import ChatRequest
@app.post("/chat")
async def chat(request: ChatRequest):

    user_message = request.message

    # Measure retrieval performance
    start = time.perf_counter()
    context, retrieved_results = retrieve_context(user_message)
    elapsed = time.perf_counter() - start

    print("\n========== RAG METRICS ==========")
    print(f"Retrieved Documents : {len(retrieved_results)}")
    print(f"Retrieval Time      : {elapsed:.3f} seconds")
    print("=================================\n")

    system_prompt = f"""=== RETRIEVED INTELLIGENCE ===
{context}
==============================

You are an Elite Cybersecurity Analyst. You are professional, concise, and helpful.

CRITICAL RULES YOU MUST FOLLOW:
1. NO ROBOT SPEAK: NEVER say "Based on the retrieved intelligence", "According to my knowledge", or "The provided information says". Just state the facts confidently as your own knowledge.
2. STRICT FORMATTING: You MUST use emojis (✅, 🔹, ⚠️, 🛡️) for ALL bullet points. Do not use plain asterisks (*). 
3. SMALL TALK: If the user just says hello or introduces themselves, greet them warmly. DO NOT bring up malware unless they explicitly ask.
4. MEMORY PROTOCOL: You have access to the user's Chat History. If the user asks you to summarize a past answer or recall something you ALREADY discussed, you MUST use the Chat History to answer. Never claim you didn't discuss something if it is in your history.
"""

    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(db_history)
    messages.append({"role": "user", "content": user_message})

    async def event_generator():

        full_response = ""

    try:
 
        for content in stream_chat(messages):

            full_response += content

            yield content

    except Exception as e:

        yield f"Error: {e}"

    finally:

        # Save the user message and assistant response to the database
        db = SessionLocal()
        try:
            user = get_current_user(authorization=f"Bearer {request.session_id}", db=db)
        finally:
            db.close()
    return StreamingResponse(event_generator(), media_type="text/plain")
@app.get("/chat/sessions")
async def list_sessions(db: Session = Depends(get_db), authorization: Optional[str] = Header(None)):
    """List all chat sessions for the current user."""
    # Secure Token Extraction
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authentication required to use the chat.")
    
    token = authorization.split(" ")[1]
    payload = decode_access_token(token)
    
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token.")
        
    username = payload.get("sub")
    user = db.query(User).filter(User.username == username).first()
    
    if not user:
        raise HTTPException(status_code=401, detail="User not found.")
        
    user_id = user.id

    # Get distinct session_ids with their first user message as title and latest timestamp
    sessions_raw = (
        db.query(
            ChatMessage.session_id,
            func.min(ChatMessage.id).label("first_id"),
            func.max(ChatMessage.created_at).label("last_active"),
            func.count(ChatMessage.id).label("msg_count")
        )
        .filter(ChatMessage.user_id == user_id, ChatMessage.session_id.isnot(None))
        .group_by(ChatMessage.session_id)
        .order_by(func.max(ChatMessage.created_at).desc())
        .all()
    )

    sessions = []
    for s in sessions_raw:
        # Get the first user message as title
        first_msg = (
            db.query(ChatMessage)
            .filter(ChatMessage.session_id == s.session_id, ChatMessage.role == "user")
            .order_by(ChatMessage.id.asc())
            .first()
        )
        title = first_msg.content[:60] if first_msg else "New Chat"
        sessions.append({
            "id": s.session_id,
            "title": title,
            "last_active": s.last_active.isoformat() if s.last_active else None,
            "message_count": s.msg_count
        })

    return sessions


@app.get("/chat/sessions/{session_id}")
async def get_session_messages(session_id: str, db: Session = Depends(get_db), authorization: Optional[str] = Header(None)):
    """Get all messages for a specific session."""
    # Secure Token Extraction
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authentication required to use the chat.")
    
    token = authorization.split(" ")[1]
    payload = decode_access_token(token)
    
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token.")
        
    username = payload.get("sub")
    user = db.query(User).filter(User.username == username).first()
    
    if not user:
        raise HTTPException(status_code=401, detail="User not found.")
        
    user_id = user.id

    messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session_id, ChatMessage.user_id == user_id)
        .order_by(ChatMessage.id.asc())
        .all()
    )

    return [
        {
            "id": str(m.id),
            "role": m.role,
            "content": m.content,
            "created_at": m.created_at.isoformat() if m.created_at else None
        }
        for m in messages
    ]


@app.delete("/chat/sessions/{session_id}")
async def delete_session(session_id: str, db: Session = Depends(get_db), authorization: Optional[str] = Header(None)):
    """Delete a chat session."""
    # Secure Token Extraction
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authentication required to use the chat.")
    
    token = authorization.split(" ")[1]
    payload = decode_access_token(token)
    
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token.")
        
    username = payload.get("sub")
    user = db.query(User).filter(User.username == username).first()
    
    if not user:
        raise HTTPException(status_code=401, detail="User not found.")
        
    user_id = user.id

    db.query(ChatMessage).filter(
        ChatMessage.session_id == session_id,
        ChatMessage.user_id == user_id
    ).delete()
    db.commit()

    # Also clear in-memory history
    if session_id in chat_history:
        del chat_history[session_id]

    return {"status": "deleted"}

