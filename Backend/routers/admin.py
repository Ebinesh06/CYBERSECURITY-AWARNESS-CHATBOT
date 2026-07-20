
try:
    from fastapi import APIRouter, Depends, HTTPException, Header
except Exception:
    from Backend._compat_fastapi import APIRouter, Depends, HTTPException, Header
from typing import Optional
from Backend.services.auth_service import require_admin
from Backend.services.database_service import get_db
from Backend.database import User, ChatMessage
from sqlalchemy.orm import Session

router = APIRouter()


@router.get("/admin/users")
async def admin_list_users(db: Session = Depends(get_db), authorization: Optional[str] = Header(None)):
    require_admin(authorization, db)
    users = db.query(User).order_by(User.id.asc()).all()
    return [{"id": u.id, "username": u.username, "role": u.role} for u in users]


@router.delete("/admin/users/{user_id}")
async def admin_delete_user(user_id: int, db: Session = Depends(get_db), authorization: Optional[str] = Header(None)):
    require_admin(authorization, db)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.role == "admin":
        raise HTTPException(status_code=403, detail="Cannot delete admin accounts")
    db.query(ChatMessage).filter(ChatMessage.user_id == user_id).delete()
    db.delete(user)
    db.commit()
    return {"status": "deleted"}
