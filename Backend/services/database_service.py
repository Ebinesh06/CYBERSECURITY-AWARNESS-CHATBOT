from typing import Any, Generator

from fastapi import Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from constants import ROLE_USER
from database import ChatMessage, SessionLocal


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


chat_history: dict[str, list[dict[str, str]]] = {}


def save_chat(session_id: str, user_id: int, role: str, content: str, db: Session) -> ChatMessage:
    message = ChatMessage(session_id=session_id, user_id=user_id, role=role, content=content)
    db.add(message)
    db.commit()
    db.refresh(message)
    chat_history.setdefault(session_id, []).append({"role": role, "content": content})
    return message


def load_chat_history(session_id: str, user_id: int, db: Session) -> list[ChatMessage]:
    return db.query(ChatMessage).filter(ChatMessage.session_id == session_id, ChatMessage.user_id == user_id).order_by(ChatMessage.id.asc()).all()


def list_chat_sessions(user_id: int, db: Session) -> list[dict[str, Any]]:
    sessions_raw = db.query(ChatMessage.session_id, func.min(ChatMessage.id).label("first_id"), func.max(ChatMessage.created_at).label("last_active"), func.count(ChatMessage.id).label("msg_count")).filter(ChatMessage.user_id == user_id, ChatMessage.session_id.isnot(None)).group_by(ChatMessage.session_id).order_by(func.max(ChatMessage.created_at).desc()).all()
    sessions: list[dict[str, Any]] = []
    for session in sessions_raw:
        first_message = db.query(ChatMessage).filter(ChatMessage.session_id == session.session_id, ChatMessage.role == ROLE_USER).order_by(ChatMessage.id.asc()).first()
        sessions.append({"id": session.session_id, "title": first_message.content[:60] if first_message else "New Chat", "last_active": session.last_active.isoformat() if session.last_active else None, "msg_count": session.msg_count})
    return sessions


def delete_chat_session(session_id: str, user_id: int, db: Session) -> None:
    db.query(ChatMessage).filter(ChatMessage.session_id == session_id, ChatMessage.user_id == user_id).delete()
    db.commit()
    chat_history.pop(session_id, None)
