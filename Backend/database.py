from sqlalchemy import create_engine, Column, Integer, String, Text, ForeignKey, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
# SQLite is great for local development; it creates a 'cybersecurity.db' file
DATABASE_URL = "sqlite:///./cybersecurity.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password_hash = Column(String)
    role = Column(String)  # 'admin' or 'user'
    
    # Security enhancements
    mfa_enabled = Column(Boolean, default=False)
    mfa_secret = Column(String, nullable=True)  # TOTP secret
    password_changed_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)
    account_locked = Column(Boolean, default=False)
    locked_until = Column(DateTime, nullable=True)
    failed_login_attempts = Column(Integer, default=0)
    password_expiry = Column(DateTime, nullable=True)  # Force password change
    force_mfa = Column(Boolean, default=False)  # Force MFA for next login
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    # ✅ IMPROVEMENT 1: Added index=True to foreign keys for instant lookups
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    session_id = Column(String, index=True) 
    
    role = Column(String) # "user" or "assistant"
    content = Column(Text)
    
    # ✅ IMPROVEMENT 2: AI Metadata
    model_used = Column(String, default="llama3")
    prompt_tokens = Column(Integer, nullable=True) 
    completion_tokens = Column(Integer, nullable=True)
    
    # ✅ IMPROVEMENT 3: RLHF (Reinforcement Learning from Human Feedback)
    user_rating = Column(Integer, nullable=True) # 1 for thumbs up, -1 for thumbs down
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # ✅ IMPROVEMENT 4: Soft Deletes for Forensics
    is_deleted = Column(Boolean, default=False)

class AuditLog(Base):
    """Track all security-relevant events"""
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    event_type = Column(String, index=True)  # 'login', 'failed_login', 'logout', 'mfa_setup', 'password_change'
    event_status = Column(String)  # 'success', 'failure', 'suspicious'
    ip_address = Column(String, index=True)
    user_agent = Column(String)
    device_fingerprint = Column(String, index=True)
    details = Column(Text)  # JSON string with additional details
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

class LoginSession(Base):
    """Track active sessions"""
    __tablename__ = "login_sessions"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    access_token = Column(String, unique=True, index=True)
    refresh_token = Column(String, unique=True, index=True)
    device_fingerprint = Column(String)
    ip_address = Column(String)
    user_agent = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, index=True)
    refresh_expires_at = Column(DateTime)
    is_active = Column(Boolean, default=True)

class TrustedDevice(Base):
    """Track trusted devices for MFA bypass"""
    __tablename__ = "trusted_devices"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    device_fingerprint = Column(String, index=True)
    device_name = Column(String)
    last_used = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class PasswordHistory(Base):
    """Prevent password reuse"""
    __tablename__ = "password_history"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    password_hash = Column(String)
    changed_at = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(bind=engine)