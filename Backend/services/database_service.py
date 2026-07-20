from typing import Generator, List
from sqlalchemy import func
from fastapi import Depends
from sqlalchemy.orm import Session
from Backend.database import SessionLocal, ChatMessage


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# In-memory chat history cache (session_id -> list of messages)
chat_history: dict = {}


def save_chat(session_id: str, user_id: int, role: str, content: str, db: Session) -> ChatMessage:
    msg = ChatMessage(session_id=session_id, user_id=user_id, role=role, content=content)
    db.add(msg)
    db.commit()
    db.refresh(msg)
    chat_history.setdefault(session_id, []).append({"role": role, "content": content})
    return msg


def load_chat_history(session_id: str, user_id: int, db: Session) -> List[ChatMessage]:
    messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session_id, ChatMessage.user_id == user_id)
        .order_by(ChatMessage.id.asc())
        .all()
    )
    return messages


def list_chat_sessions(user_id: int, db: Session):
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
    for session in sessions_raw:
        first_msg = (
            db.query(ChatMessage)
            .filter(ChatMessage.session_id == session.session_id, ChatMessage.role == "user")
            .order_by(ChatMessage.id.asc())
            .first()
        )
        title = first_msg.content[:60] if first_msg else "New Chat"
        sessions.append({
            "id": session.session_id,
            "title": title,
            "last_active": session.last_active.isoformat() if session.last_active else None,
            "msg_count": session.msg_count,
        })
    return sessions


def delete_chat_session(session_id: str, user_id: int, db: Session):
    db.query(ChatMessage).filter(ChatMessage.session_id == session_id, ChatMessage.user_id == user_id).delete()
    db.commit()
    if session_id in chat_history:
        del chat_history[session_id]
