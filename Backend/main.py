from rank_bm25 import BM25Okapi
from flashrank import Ranker, RerankRequest
import ollama
import chromadb
from fastapi import FastAPI, Depends, HTTPException, status, Header
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from database import SessionLocal, ChatMessage, User, AuditLog, LoginSession, TrustedDevice, PasswordHistory
from sqlalchemy.orm import Session
from sqlalchemy import func, distinct
from auth_utils import (
    verify_password, create_access_token, get_password_hash, decode_access_token,
    generate_mfa_secret, verify_totp, validate_password_strength, 
    is_suspicious_login, RateLimiter, generate_device_fingerprint
)
from typing import Optional, List
from datetime import datetime, timedelta
import pyotp
import qrcode
import io
import base64
import json
import hashlib
import secrets

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

# 3. Initialize Rate Limiter for enterprise security
rate_limiter = RateLimiter()

# 4. Request models for enterprise authentication
class AdminLoginRequest(BaseModel):
    username: str
    password: str
    device_fingerprint: str
    ip_address: str = "auto-detect"

class VerifyMfaRequest(BaseModel):
    mfa_token: str
    mfa_code: str
    trust_device: bool = False
    device_name: str = "Default Device"

class SetupMfaRequest(BaseModel):
    username: str

class ConfirmMfaSetupRequest(BaseModel):
    username: str
    mfa_code: str

class RefreshTokenRequest(BaseModel):
    refresh_token: str

# 5. ChromaDB - Initialize with fallback
try:
    chroma_client = chromadb.PersistentClient(path="./chroma_db")
    intelligence_collection = chroma_client.get_collection(name="cyber_intelligence")
    
    # --- PHASE 2 STARTUP: KEYWORD INDEXING ---
    all_data = intelligence_collection.get()
    documents = all_data['documents']
    metadatas = all_data['metadatas']
    
    tokenized_corpus = [doc.lower().split(" ") for doc in documents]
    bm25 = BM25Okapi(tokenized_corpus)
except Exception as e:
    print(f"Warning: ChromaDB initialization failed: {e}")
    print("Proceeding with authentication endpoints only")
    chroma_client = None
    intelligence_collection = None
    all_data = {'documents': [], 'metadatas': []}
    documents = []
    metadatas = []
    tokenized_corpus = []
    bm25 = None

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

# --- ENTERPRISE USER LOGIN REQUEST MODELS ---
class UserLoginRequest(BaseModel):
    username: str
    password: str
    device_fingerprint: str
    ip_address: str = "auto-detect"

class UserSignupRequest(BaseModel):
    username: str
    password: str
    device_fingerprint: str
    ip_address: str = "auto-detect"

# --- ENTERPRISE USER LOGIN ENDPOINTS ---
@app.post("/auth/login")
async def login(request: UserLoginRequest, db: Session = Depends(get_db)):
    """
    Enterprise user login with rate limiting, device fingerprinting, and suspicious activity detection
    """
    
    client_ip = get_client_ip(request.ip_address)
    rate_limit_key_user = f"user_login:{request.username}"
    rate_limit_key_ip = f"user_login_ip:{client_ip}"
    
    # Check rate limiting by username
    if rate_limiter.is_rate_limited(rate_limit_key_user, max_attempts=5, window_seconds=300):
        audit_log = AuditLog(
            user_id=None,
            event_type="user_login",
            event_status="failure_rate_limited",
            ip_address=client_ip,
            device_fingerprint=request.device_fingerprint,
            details=json.dumps({"username": request.username, "reason": "rate_limit_exceeded"})
        )
        db.add(audit_log)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Please try again later."
        )
    
    # Check rate limiting by IP
    if rate_limiter.is_rate_limited(rate_limit_key_ip, max_attempts=20, window_seconds=3600):
        audit_log = AuditLog(
            user_id=None,
            event_type="user_login",
            event_status="failure_rate_limited_ip",
            ip_address=client_ip,
            device_fingerprint=request.device_fingerprint,
            details=json.dumps({"ip": client_ip, "reason": "ip_rate_limit_exceeded"})
        )
        db.add(audit_log)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts from this IP. Please try again later."
        )
    
    # Find user
    user = db.query(User).filter(User.username == request.username).first()
    
    # Record attempt for rate limiting
    rate_limiter.record_attempt(rate_limit_key_user)
    rate_limiter.record_attempt(rate_limit_key_ip)
    
    # Verify password
    if not user or not verify_password(request.password, user.password_hash):
        audit_log = AuditLog(
            user_id=user.id if user else None,
            event_type="user_login",
            event_status="failure_invalid_credentials",
            ip_address=client_ip,
            device_fingerprint=request.device_fingerprint,
            details=json.dumps({"username": request.username})
        )
        db.add(audit_log)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )
    
    # Check account locked status
    if user.account_locked:
        if user.locked_until and user.locked_until > datetime.utcnow():
            remaining_seconds = int((user.locked_until - datetime.utcnow()).total_seconds())
            audit_log = AuditLog(
                user_id=user.id,
                event_type="user_login",
                event_status="failure_account_locked",
                ip_address=client_ip,
                device_fingerprint=request.device_fingerprint,
                details=json.dumps({"reason": f"locked_for_{remaining_seconds}s"})
            )
            db.add(audit_log)
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail=f"Account locked. Try again in {remaining_seconds} seconds."
            )
        else:
            user.account_locked = False
            user.locked_until = None
            user.failed_login_attempts = 0
    
    # Check password expiry
    if user.password_expiry and user.password_expiry < datetime.utcnow():
        user.force_mfa = True  # Force MFA on expired password
    
    # Check suspicious activity
    previous_logins = db.query(LoginSession).filter(
        LoginSession.user_id == user.id,
        LoginSession.is_active == True
    ).all()
    
    is_suspicious, reason = is_suspicious_login(
        user.id, client_ip, request.device_fingerprint, previous_logins
    )
    
    if is_suspicious:
        user.force_mfa = True
        db.commit()
    
    # Create audit log
    audit_log = AuditLog(
        user_id=user.id,
        event_type="user_login",
        event_status="success_credentials_valid",
        ip_address=client_ip,
        device_fingerprint=request.device_fingerprint,
        details=json.dumps({
            "suspicious": is_suspicious,
            "reason": reason if is_suspicious else "normal"
        })
    )
    
    # If MFA is required, return MFA token
    if user.mfa_enabled or user.force_mfa:
        mfa_token = create_access_token(
            data={"sub": user.username, "type": "mfa", "session": secrets.token_hex(16)},
            expires_delta=timedelta(minutes=5)
        )
        audit_log.event_status = "success_mfa_pending"
        db.add(audit_log)
        db.commit()
        return {
            "mfa_required": True,
            "mfa_token": mfa_token,
            "message": "MFA code required",
            "force_mfa": user.force_mfa,
            "suspicious_reason": reason if is_suspicious else None
        }
    
    # No MFA, return tokens
    access_token = create_access_token(data={"sub": user.username, "role": user.role})
    refresh_token = create_access_token(
        data={"sub": user.username, "type": "refresh"},
        expires_delta=timedelta(days=7)
    )
    
    # Create login session
    login_session = LoginSession(
        user_id=user.id,
        access_token=access_token,
        refresh_token=refresh_token,
        device_fingerprint=request.device_fingerprint,
        ip_address=client_ip,
        user_agent="web",
        created_at=datetime.utcnow(),
        expires_at=datetime.utcnow() + timedelta(minutes=15),
        refresh_expires_at=datetime.utcnow() + timedelta(days=7),
        is_active=True
    )
    db.add(login_session)
    
    # Reset failed login attempts
    user.failed_login_attempts = 0
    user.last_login = datetime.utcnow()
    
    audit_log.event_status = "success"
    db.add(audit_log)
    db.commit()
    
    # Clear rate limiting after successful login
    rate_limiter.reset(rate_limit_key_user)
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "role": user.role,
        "username": user.username,
        "mfa_required": False
    }

@app.post("/auth/signup")
async def signup(request: UserSignupRequest, db: Session = Depends(get_db)):
    """
    Enterprise user signup with password strength validation and optional MFA
    """
    
    client_ip = get_client_ip(request.ip_address)
    
    # Check if user already exists
    existing_user = db.query(User).filter(User.username == request.username).first()
    if existing_user:
        audit_log = AuditLog(
            user_id=None,
            event_type="user_signup",
            event_status="failure_user_exists",
            ip_address=client_ip,
            device_fingerprint=request.device_fingerprint,
            details=json.dumps({"username": request.username})
        )
        db.add(audit_log)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists"
        )
    
    # Validate password strength
    is_strong, strength_reason = validate_password_strength(request.password)
    if not is_strong:
        audit_log = AuditLog(
            user_id=None,
            event_type="user_signup",
            event_status="failure_weak_password",
            ip_address=client_ip,
            device_fingerprint=request.device_fingerprint,
            details=json.dumps({"reason": strength_reason})
        )
        db.add(audit_log)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Password strength requirement failed: {strength_reason}"
        )
    
    # Create new user
    password_hash = get_password_hash(request.password)
    new_user = User(
        username=request.username,
        password_hash=password_hash,
        role="user",
        mfa_enabled=False,
        account_locked=False,
        failed_login_attempts=0,
        password_changed_at=datetime.utcnow(),
        password_expiry=datetime.utcnow() + timedelta(days=90),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(new_user)
    db.flush()  # Get user ID
    
    # Create password history entry
    password_history = PasswordHistory(
        user_id=new_user.id,
        password_hash=password_hash,
        changed_at=datetime.utcnow()
    )
    db.add(password_history)
    
    # Create login session
    access_token = create_access_token(data={"sub": new_user.username, "role": new_user.role})
    refresh_token = create_access_token(
        data={"sub": new_user.username, "type": "refresh"},
        expires_delta=timedelta(days=7)
    )
    
    login_session = LoginSession(
        user_id=new_user.id,
        access_token=access_token,
        refresh_token=refresh_token,
        device_fingerprint=request.device_fingerprint,
        ip_address=client_ip,
        user_agent="web",
        created_at=datetime.utcnow(),
        expires_at=datetime.utcnow() + timedelta(minutes=15),
        refresh_expires_at=datetime.utcnow() + timedelta(days=7),
        is_active=True
    )
    db.add(login_session)
    
    # Create audit log
    audit_log = AuditLog(
        user_id=new_user.id,
        event_type="user_signup",
        event_status="success",
        ip_address=client_ip,
        device_fingerprint=request.device_fingerprint,
        details=json.dumps({"username": new_user.username})
    )
    db.add(audit_log)
    db.commit()
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "role": new_user.role,
        "username": new_user.username,
        "message": "Account created successfully. You can setup MFA in settings."
    }

# ============================================
# ENTERPRISE SECURITY: ADMIN LOGIN WITH MFA
# ============================================

def get_client_ip(request_ip: str = "127.0.0.1") -> str:
    """Extract client IP (simplified version)"""
    return request_ip if request_ip else "127.0.0.1"

@app.post("/auth/admin-login")
async def admin_login(request: AdminLoginRequest, db: Session = Depends(get_db)):
    """
    Enterprise admin login with MFA support
    
    Returns:
    - If MFA enabled: mfa_token + mfa_required: true
    - If MFA disabled: access_token + refresh_token
    """
    
    # Rate limiting check (per IP)
    client_ip = get_client_ip(request.ip_address)
    if not rate_limiter.is_allowed(client_ip):
        raise HTTPException(status_code=429, detail="Too many login attempts. Please try again later.")
    
    # Get user
    user = db.query(User).filter(User.username == request.username).first()
    
    # Log attempt (success or failure)
    audit_log = AuditLog(
        user_id=user.id if user else None,
        event_type="login",
        ip_address=client_ip,
        user_agent="web",
        device_fingerprint=request.device_fingerprint
    )
    
    # Check account lockout
    if user and user.account_locked:
        if user.locked_until and datetime.utcnow() < user.locked_until:
            audit_log.event_status = "failure"
            audit_log.details = json.dumps({"reason": "account_locked"})
            db.add(audit_log)
            db.commit()
            raise HTTPException(status_code=423, detail=f"Account locked. Try again at {user.locked_until}")
        else:
            # Unlock if time has passed
            user.account_locked = False
            user.locked_until = None
            user.failed_login_attempts = 0
            db.commit()
    
    # Validate credentials
    if not user or not verify_password(request.password, user.password_hash):
        if user:
            user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
            if user.failed_login_attempts >= 5:
                user.account_locked = True
                user.locked_until = datetime.utcnow() + timedelta(seconds=300)
            db.commit()
        
        audit_log.event_status = "failure"
        audit_log.details = json.dumps({"reason": "invalid_credentials"})
        db.add(audit_log)
        db.commit()
        raise HTTPException(status_code=401, detail="Invalid username or password")
    
    # Check for suspicious activity
    previous_logins = db.query(LoginSession).filter(
        LoginSession.user_id == user.id,
        LoginSession.is_active == True
    ).all()
    
    previous_ips = [login.ip_address for login in previous_logins]
    previous_fingerprints = [login.device_fingerprint for login in previous_logins]
    
    is_suspicious, suspicious_reason = is_suspicious_login(
        user.id, client_ip, request.device_fingerprint, 
        [(login.ip_address, login.device_fingerprint, login.created_at) for login in previous_logins]
    )
    
    # Reset failed attempts on successful credential verification
    user.failed_login_attempts = 0
    user.last_login = datetime.utcnow()
    
    if is_suspicious:
        audit_log.event_status = "suspicious"
        audit_log.details = json.dumps({"reason": suspicious_reason})
        db.add(audit_log)
        db.commit()
        # Force MFA for suspicious logins
        user.force_mfa = True
    
    db.commit()
    
    # If MFA enabled, return mfa_token instead of access_token
    if user.mfa_enabled or user.force_mfa:
        mfa_token = create_access_token(
            data={"sub": user.username, "type": "mfa", "session": secrets.token_hex(16)},
            expires_delta=timedelta(minutes=5)
        )
        audit_log.event_status = "success_mfa_pending"
        db.add(audit_log)
        db.commit()
        return {
            "mfa_required": True,
            "mfa_token": mfa_token,
            "message": "MFA code required"
        }
    
    # No MFA, return tokens
    access_token = create_access_token(data={"sub": user.username, "role": user.role})
    refresh_token = create_access_token(
        data={"sub": user.username, "type": "refresh"},
        expires_delta=timedelta(days=7)
    )
    
    # Create login session
    login_session = LoginSession(
        user_id=user.id,
        access_token=access_token,
        refresh_token=refresh_token,
        device_fingerprint=request.device_fingerprint,
        ip_address=client_ip,
        user_agent="web",
        created_at=datetime.utcnow(),
        expires_at=datetime.utcnow() + timedelta(minutes=15),
        refresh_expires_at=datetime.utcnow() + timedelta(days=7),
        is_active=True
    )
    db.add(login_session)
    
    audit_log.event_status = "success"
    audit_log.details = json.dumps({"device": request.device_fingerprint})
    db.add(audit_log)
    db.commit()
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "role": user.role,
        "username": user.username,
        "mfa_required": False
    }

@app.post("/auth/verify-mfa")
async def verify_mfa(request: VerifyMfaRequest, db: Session = Depends(get_db)):
    """
    Verify TOTP code and issue session tokens
    """
    
    # Decode mfa_token
    payload = decode_access_token(request.mfa_token)
    if not payload or payload.get("type") != "mfa":
        raise HTTPException(status_code=401, detail="Invalid MFA token")
    
    username = payload.get("sub")
    user = db.query(User).filter(User.username == username).first()
    
    if not user or not user.mfa_secret:
        audit_log = AuditLog(
            user_id=user.id if user else None,
            event_type="mfa_verification",
            event_status="failure",
            details=json.dumps({"reason": "mfa_secret_missing"})
        )
        db.add(audit_log)
        db.commit()
        raise HTTPException(status_code=401, detail="MFA not configured")
    
    # Verify TOTP code
    if not verify_totp(user.mfa_secret, request.mfa_code):
        audit_log = AuditLog(
            user_id=user.id,
            event_type="mfa_verification",
            event_status="failure",
            details=json.dumps({"reason": "invalid_mfa_code"})
        )
        db.add(audit_log)
        db.commit()
        raise HTTPException(status_code=401, detail="Invalid MFA code")
    
    # Create tokens
    access_token = create_access_token(data={"sub": user.username, "role": user.role})
    refresh_token = create_access_token(
        data={"sub": user.username, "type": "refresh"},
        expires_delta=timedelta(days=7)
    )
    
    # Create login session
    login_session = LoginSession(
        user_id=user.id,
        access_token=access_token,
        refresh_token=refresh_token,
        device_fingerprint=request.mfa_token[:32],  # Simplified device tracking
        ip_address="web",
        user_agent="web",
        created_at=datetime.utcnow(),
        expires_at=datetime.utcnow() + timedelta(minutes=15),
        refresh_expires_at=datetime.utcnow() + timedelta(days=7),
        is_active=True
    )
    db.add(login_session)
    
    # If trust device is enabled, create trusted device
    if request.trust_device:
        device_fingerprint = request.mfa_token[:32]
        existing_device = db.query(TrustedDevice).filter(
            TrustedDevice.user_id == user.id,
            TrustedDevice.device_fingerprint == device_fingerprint
        ).first()
        
        if not existing_device:
            trusted_device = TrustedDevice(
                user_id=user.id,
                device_fingerprint=device_fingerprint,
                device_name=request.device_name,
                last_used=datetime.utcnow(),
                is_active=True,
                created_at=datetime.utcnow()
            )
            db.add(trusted_device)
    
    # Clear force_mfa flag
    user.force_mfa = False
    
    audit_log = AuditLog(
        user_id=user.id,
        event_type="mfa_verification",
        event_status="success",
        details=json.dumps({"trusted_device": request.trust_device})
    )
    db.add(audit_log)
    db.commit()
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "role": user.role,
        "username": user.username
    }

@app.post("/auth/setup-mfa")
async def setup_mfa(request: SetupMfaRequest, db: Session = Depends(get_db)):
    """
    Generate MFA secret and QR code for setup
    """
    
    user = db.query(User).filter(User.username == request.username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.mfa_enabled:
        raise HTTPException(status_code=400, detail="MFA already enabled for this user")
    
    # Generate secret
    secret = generate_mfa_secret()
    
    # Generate QR code
    totp = pyotp.TOTP(secret)
    qr_uri = totp.provisioning_uri(name=user.username, issuer_name="CyberSecurityChatbot")
    
    # Create QR code image
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(qr_uri)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Convert to base64
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    qr_code_base64 = base64.b64encode(buffer.getvalue()).decode()
    
    # Store secret temporarily in session (frontend will complete setup)
    # In production, use proper session management
    
    return {
        "mfa_secret": secret,
        "qr_code_url": f"data:image/png;base64,{qr_code_base64}",
        "provisioning_uri": qr_uri,
        "message": "Scan QR code with authenticator app. Enter code to confirm setup."
    }

@app.post("/auth/confirm-mfa-setup")
async def confirm_mfa_setup(request: ConfirmMfaSetupRequest, db: Session = Depends(get_db)):
    """
    Confirm MFA setup by verifying code
    """
    
    user = db.query(User).filter(User.username == request.username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # In production, the secret should come from a temporary session
    # For now, we'll expect it to be re-generated
    secret = generate_mfa_secret()
    
    # Verify the code
    if not verify_totp(secret, request.mfa_code):
        raise HTTPException(status_code=400, detail="Invalid MFA code")
    
    # Store secret in database
    user.mfa_secret = secret
    user.mfa_enabled = True
    
    audit_log = AuditLog(
        user_id=user.id,
        event_type="mfa_setup",
        event_status="success",
        details=json.dumps({"method": "totp"})
    )
    db.add(audit_log)
    db.commit()
    
    return {"message": "MFA setup successful", "status": "enabled"}

# --- USER MFA ENDPOINTS ---
@app.post("/auth/user/setup-mfa")
async def user_setup_mfa(request: SetupMfaRequest, db: Session = Depends(get_db)):
    """
    User setup MFA - Generate secret and QR code
    """
    
    user = db.query(User).filter(User.username == request.username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.mfa_enabled:
        raise HTTPException(status_code=400, detail="MFA already enabled for this account")
    
    # Generate secret
    secret = generate_mfa_secret()
    
    # Generate QR code
    totp = pyotp.TOTP(secret)
    qr_uri = totp.provisioning_uri(name=user.username, issuer_name="CyberSecurityChatbot")
    
    # Create QR code image
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(qr_uri)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Convert to base64
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    qr_code_base64 = base64.b64encode(buffer.getvalue()).decode()
    
    audit_log = AuditLog(
        user_id=user.id,
        event_type="user_mfa_setup_initiated",
        event_status="success",
        details=json.dumps({"method": "totp"})
    )
    db.add(audit_log)
    db.commit()
    
    return {
        "mfa_secret": secret,
        "qr_code_url": f"data:image/png;base64,{qr_code_base64}",
        "provisioning_uri": qr_uri,
        "message": "Scan QR code with authenticator app. Enter code to confirm setup."
    }

@app.post("/auth/user/confirm-mfa")
async def user_confirm_mfa(request: ConfirmMfaSetupRequest, db: Session = Depends(get_db)):
    """
    User confirm MFA setup by verifying code
    """
    
    user = db.query(User).filter(User.username == request.username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # For security, secret should come from a session store
    # For now, regenerate and verify
    secret = generate_mfa_secret()
    
    if not verify_totp(secret, request.mfa_code):
        raise HTTPException(status_code=400, detail="Invalid MFA code")
    
    # Store secret in database
    user.mfa_secret = secret
    user.mfa_enabled = True
    user.updated_at = datetime.utcnow()
    
    audit_log = AuditLog(
        user_id=user.id,
        event_type="user_mfa_setup_confirmed",
        event_status="success",
        details=json.dumps({"method": "totp"})
    )
    db.add(audit_log)
    db.commit()
    
    return {"message": "MFA setup successful", "status": "enabled"}

@app.post("/auth/refresh-token")
async def refresh_token_endpoint(request: RefreshTokenRequest, db: Session = Depends(get_db)):
    """
    Refresh access token using refresh token
    """
    
    payload = decode_access_token(request.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    
    username = payload.get("sub")
    user = db.query(User).filter(User.username == username).first()
    
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    # Create new access token
    access_token = create_access_token(data={"sub": user.username, "role": user.role})
    
    # Update login session
    login_session = db.query(LoginSession).filter(
        LoginSession.refresh_token == request.refresh_token,
        LoginSession.is_active == True
    ).first()
    
    if login_session:
        login_session.access_token = access_token
        login_session.expires_at = datetime.utcnow() + timedelta(minutes=15)
        db.commit()
    
    return {
        "access_token": access_token,
        "token_type": "bearer"
    }

@app.get("/auth/trusted-devices")
async def get_trusted_devices(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """
    Get list of trusted devices for current user
    """
    
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
    
    devices = db.query(TrustedDevice).filter(
        TrustedDevice.user_id == user.id,
        TrustedDevice.is_active == True
    ).all()
    
    return {
        "devices": [
            {
                "device_name": d.device_name,
                "device_fingerprint": d.device_fingerprint[:16] + "***",
                "last_used": d.last_used.isoformat(),
                "created_at": d.created_at.isoformat()
            }
            for d in devices
        ]
    }

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
