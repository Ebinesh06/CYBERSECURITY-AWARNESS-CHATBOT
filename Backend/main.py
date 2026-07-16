from flashrank import RerankRequest
from fastapi import FastAPI, Depends, HTTPException, status, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from database import SessionLocal, ChatMessage, User, AuditLog, LoginSession, TrustedDevice, PasswordHistory
from sqlalchemy.orm import Session
from sqlalchemy import func, distinct
from vector_db import ChatRequest, hybrid_search
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
temp_mfa_secrets = {}

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


