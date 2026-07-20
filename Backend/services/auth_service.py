from typing import Optional
try:
	from fastapi import Header, HTTPException, Depends
except Exception:
	from _compat_fastapi import Header, HTTPException, Depends
from sqlalchemy.orm import Session
from database import User
from auth_utils import decode_access_token
from constants import ROLE_ADMIN
from .database_service import get_db


def get_current_user(authorization: Optional[str] = Header(None), db: Session = Depends(get_db)) -> User:
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


def require_admin(authorization: Optional[str] = Header(None), db: Session = Depends(get_db)) -> User:
	payload = get_current_user(authorization, db)
	# payload may be a User object; check role
	if getattr(payload, "role", None) != ROLE_ADMIN:
		raise HTTPException(status_code=403, detail="Admin access required")
	return payload
