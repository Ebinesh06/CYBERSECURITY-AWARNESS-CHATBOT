from rank_bm25 import BM25Okapi
from flashrank import Ranker, RerankRequest
import ollama
import chromadb
from fastapi import FastAPI, Depends, HTTPException, status, Header
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from batabase import SessionLocal, ChatMessage, User
from sqlalchemy.orm import Session
from sqlalchemy import func, distinct
from auth_utils import verify_password, create_access_token, get_password_hash, decode_access_token
from typing import Optional
from datetime import datetime

# Dependency to get the database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- Helper: Extract user from JWT ---
def get_current_user(authorization: Optional[str] = Header(None), db: Session = Depends(get_db)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = authorization.split(" ")[1]
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    username = payload.get("sub")
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user

# --- PHASE 3: CONVERSATIONAL MEMORY ---
chat_history = {}

# 1. Initialize FastAPI app
app = FastAPI()

# 2. Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3. ChromaDB
chroma_client = chromadb.PersistentClient(path="./chroma_db")
intelligence_collection = chroma_client.get_collection(name="cyber_intelligence")

# --- PHASE 2 STARTUP: KEYWORD INDEXING ---
all_data = intelligence_collection.get()
documents = all_data['documents']
metadatas = all_data['metadatas']

tokenized_corpus = [doc.lower().split(" ") for doc in documents]
bm25 = BM25Okapi(tokenized_corpus)

ranker = Ranker(model_name="ms-marco-TinyBERT-L-2-v2", cache_dir="./models")

print(f"SUCCESS: Indexed {len(documents)} vulnerabilities for Precision Search.")

# 4. Request models
class ChatRequest(BaseModel):
    message: str
    session_id: str = "default_user"

def hybrid_search(query, top_k=10):
    vector_results = intelligence_collection.query(query_texts=[query], n_results=top_k)
    tokenized_query = query.lower().split(" ")
    bm25_scores = bm25.get_scores(tokenized_query)
    
    fusion_results = {}
    if vector_results['documents'] and vector_results['documents'][0]:
        for i, doc in enumerate(vector_results['documents'][0]):
            fusion_results[doc] = 1 / (i + 60)

    top_n_bm25 = sorted(range(len(bm25_scores)), key=lambda i: bm25_scores[i], reverse=True)[:top_k]
    for i, idx in enumerate(top_n_bm25):
        doc = documents[idx]
        score = 1 / (i + 60)
        fusion_results[doc] = fusion_results.get(doc, 0) + score

    ranked_docs = sorted(fusion_results.items(), key=lambda x: x[1], reverse=True)
    return [doc for doc, score in ranked_docs[:top_k]]


# ============================================
# CHAT ENDPOINTS
# ============================================

@app.post("/chat")
async def chat_endpoint(request: ChatRequest, db: Session = Depends(get_db), authorization: Optional[str] = Header(None)):
    user_message = request.message
    sid = request.session_id

    # Get user from token
    user_id = 1
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1]
        payload = decode_access_token(token)
        if payload:
            username = payload.get("sub")
            user = db.query(User).filter(User.username == username).first()
            if user:
                user_id = user.id

    if sid not in chat_history:
        chat_history[sid] = []

    search_query = user_message
    if len(chat_history[sid]) > 0:
        last_context = chat_history[sid][-1]["content"]
        search_query = f"{last_context} {user_message}"
    
    hybrid_docs = hybrid_search(search_query)

    ranker_input = [{"id": i, "text": doc} for i, doc in enumerate(hybrid_docs)]
    rerank_request = RerankRequest(query=search_query, passages=ranker_input)
    reranked_results = ranker.rerank(rerank_request)

    final_context_list = [res['text'] for res in reranked_results[:3]]
    context = "\n\n".join(final_context_list)

    system_prompt = (
        "You are an Elite Cybersecurity Analyst. Your responses must be well-structured, professional, and easy to read. "
        "FORMATTING RULES: "
        "1) Use clear section headers with emoji prefixes (e.g., '🔍 Analysis', '🛡️ Recommendations', '⚠️ Risks'). "
        "2) Use emoji bullet points (🔹, 🔸, ✅, ❌, 📌) instead of plain asterisks or dashes. "
        "3) Use **bold** for key terms, CVE IDs, and important concepts. "
        "4) Use numbered lists (1., 2., 3.) for sequential steps. "
        "5) Keep paragraphs short — max 2-3 sentences each. "
        "6) End with a brief '📋 Summary' or '💡 Key Takeaway' when appropriate. "
        "STRICT RULE: Base your answers on the 'Retrieved Intelligence' and 'Chat History'. "
        "Be thorough but concise. Sound authoritative and professional."
    )

    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(chat_history[sid][-4:])
    messages.append({"role": "user", "content": user_message})

    async def event_generator():
        full_response = ""
        try:
            stream = ollama.chat(model='llama3', messages=messages, stream=True)
            for chunk in stream:
                content = chunk['message'].get('content', '')
                if content:
                    full_response += content
                    yield content
        except Exception as e:
            yield f"Error: {str(e)}"
        finally:
            chat_history[sid].append({"role": "user", "content": user_message})
            chat_history[sid].append({"role": "assistant", "content": full_response})
            try:
                db.add(ChatMessage(user_id=user_id, session_id=sid, role="user", content=user_message, created_at=datetime.utcnow()))
                db.add(ChatMessage(user_id=user_id, session_id=sid, role="assistant", content=full_response, created_at=datetime.utcnow()))
                db.commit()
            except Exception as e:
                print(f"DB save error: {e}")

    return StreamingResponse(event_generator(), media_type="text/plain")


@app.get("/chat/sessions")
async def list_sessions(db: Session = Depends(get_db), authorization: Optional[str] = Header(None)):
    """List all chat sessions for the current user."""
    user_id = 1
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1]
        payload = decode_access_token(token)
        if payload:
            username = payload.get("sub")
            user = db.query(User).filter(User.username == username).first()
            if user:
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
    user_id = 1
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1]
        payload = decode_access_token(token)
        if payload:
            username = payload.get("sub")
            user = db.query(User).filter(User.username == username).first()
            if user:
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
    user_id = 1
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1]
        payload = decode_access_token(token)
        if payload:
            username = payload.get("sub")
            user = db.query(User).filter(User.username == username).first()
            if user:
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


# ============================================
# AUTHENTICATION ENDPOINTS
# ============================================

@app.post("/auth/setup-admin")
async def setup_admin(db: Session = Depends(get_db)):
    admin_exists = db.query(User).filter(User.username == "admin").first()
    if admin_exists:
        return {"message": "Admin already exists"}
    new_admin = User(username="admin", password_hash=get_password_hash("admin123"), role="admin")
    db.add(new_admin)
    db.commit()
    return {"message": "Admin created! Username: admin, Password: admin123"}

class LoginRequest(BaseModel):
    username: str
    password: str

@app.post("/auth/login")
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == request.username).first()
    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")
    access_token = create_access_token(data={"sub": user.username, "role": user.role})
    return {"access_token": access_token, "role": user.role, "username": user.username}

class SignupRequest(BaseModel):
    username: str
    password: str

@app.post("/auth/signup")
async def signup(request: SignupRequest, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.username == request.username).first()
    if existing_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already exists")
    if len(request.password) < 6:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Password must be at least 6 characters")
    new_user = User(username=request.username, password_hash=get_password_hash(request.password), role="user")
    db.add(new_user)
    db.commit()
    access_token = create_access_token(data={"sub": new_user.username, "role": new_user.role})
    return {"access_token": access_token, "role": new_user.role, "username": new_user.username}

# ============================================
# ADMIN USER MANAGEMENT ENDPOINTS
# ============================================

def require_admin(authorization: Optional[str] = Header(None), db: Session = Depends(get_db)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = authorization.split(" ")[1]
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    if payload.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return payload

@app.get("/admin/users")
async def admin_list_users(db: Session = Depends(get_db), authorization: Optional[str] = Header(None)):
    require_admin(authorization, db)
    users = db.query(User).order_by(User.id.asc()).all()
    return [
        {
            "id": u.id,
            "username": u.username,
            "role": u.role,
        }
        for u in users
    ]

@app.delete("/admin/users/{user_id}")
async def admin_delete_user(user_id: int, db: Session = Depends(get_db), authorization: Optional[str] = Header(None)):
    payload = require_admin(authorization, db)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.role == "admin":
        raise HTTPException(status_code=403, detail="Cannot delete admin accounts")
    db.query(ChatMessage).filter(ChatMessage.user_id == user_id).delete()
    db.delete(user)
    db.commit()
    return {"status": "deleted"}

# ============================================
# SERVER STARTUP
# ============================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
