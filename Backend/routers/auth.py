try:
    from fastapi import APIRouter, Depends, HTTPException, status, Header
except Exception:
    from Backend._compat_fastapi import APIRouter, Depends, HTTPException, Header
    class status:
        HTTP_401_UNAUTHORIZED = 401
        HTTP_423_LOCKED = 423
        HTTP_429_TOO_MANY_REQUESTS = 429

from typing import Optional
from datetime import datetime, timedelta
import secrets
import io
import base64

from Backend.database import User, AuditLog, LoginSession, PasswordHistory, TrustedDevice
from Backend.services.database_service import get_db
from Backend.auth_utils import (
    verify_password,
    create_access_token,
    create_refresh_token,
    get_password_hash,
    validate_password_strength,
    is_suspicious_login,
    RateLimiter,
    generate_mfa_secret,
    verify_totp,
    decode_access_token,
    decode_refresh_token,
    get_totp_provisioning_uri,
    SECRET_KEY,
    ALGORITHM
)

try:
    import qrcode
except Exception:
    qrcode = None

try:
    from pydantic import BaseModel
except Exception:
    class BaseModel:
        def __init__(self, **data):
            for k, v in data.items():
                setattr(self, k, v)

router = APIRouter()

rate_limiter = RateLimiter()

temp_mfa_secrets: dict[str, str] = {}


def get_client_ip(request_ip: str = "127.0.0.1") -> str:
    return request_ip if request_ip else "127.0.0.1"


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


class VerifyMfaRequest(BaseModel):
    mfa_token: str
    mfa_code: str
    trust_device: bool = False
    device_name: str = "web"


class SetupMfaRequest(BaseModel):
    username: str


class ConfirmMfaSetupRequest(BaseModel):
    username: str
    mfa_code: str


class RefreshTokenRequest(BaseModel):
    refresh_token: str


def decode_mfa_token(token: str) -> Optional[dict]:
    try:
        from jose import JWTError, jwt
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "mfa":
            return None
        return payload
    except Exception:
        return None


def create_session_tokens(user: User, db, device_fingerprint: str, ip_address: str):
    access_token = create_access_token(data={"sub": user.username, "role": user.role})
    refresh_token = create_refresh_token(data={"sub": user.username})
    login_session = LoginSession(
        user_id=user.id,
        access_token=access_token,
        refresh_token=refresh_token,
        device_fingerprint=device_fingerprint,
        ip_address=ip_address,
        user_agent="web",
        created_at=datetime.utcnow(),
        expires_at=datetime.utcnow() + timedelta(minutes=15),
        refresh_expires_at=datetime.utcnow() + timedelta(days=7),
        is_active=True
    )
    db.add(login_session)
    user.failed_login_attempts = 0
    user.last_login = datetime.utcnow()
    db.commit()
    return access_token, refresh_token


@router.post("/auth/setup-admin")
async def setup_admin(db = Depends(get_db)):
    admin_exists = db.query(User).filter(User.username == "admin").first()
    if admin_exists:
        return {"message": "Admin already exists"}

    new_admin = User(
        username="admin",
        password_hash=get_password_hash("admin123"),
        role="admin",
        mfa_enabled=False,
        account_locked=False,
        failed_login_attempts=0,
        password_changed_at=datetime.utcnow(),
        password_expiry=datetime.utcnow() + timedelta(days=90),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(new_admin)
    db.commit()
    return {"message": "Admin created! Username: admin, Password: admin123"}


@router.post("/auth/login")
async def login(request: UserLoginRequest, db = Depends(get_db)):
    request.username = request.username.lower()
    client_ip = get_client_ip(request.ip_address)
    rate_limit_key_user = f"user_login:{request.username}"
    rate_limit_key_ip = f"user_login_ip:{client_ip}"

    if rate_limiter.is_rate_limited(rate_limit_key_user, max_attempts=5, window_seconds=300):
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many login attempts")

    if rate_limiter.is_rate_limited(rate_limit_key_ip, max_attempts=20, window_seconds=3600):
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many login attempts from this IP")

    user = db.query(User).filter(User.username == request.username).first()
    rate_limiter.record_attempt(rate_limit_key_user)
    rate_limiter.record_attempt(rate_limit_key_ip)

    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")

    if user.account_locked:
        if user.locked_until and user.locked_until > datetime.utcnow():
            remaining_seconds = int((user.locked_until - datetime.utcnow()).total_seconds())
            raise HTTPException(status_code=status.HTTP_423_LOCKED, detail=f"Account locked. Try again in {remaining_seconds} seconds.")
        user.account_locked = False
        user.locked_until = None
        user.failed_login_attempts = 0

    if user.password_expiry and user.password_expiry < datetime.utcnow():
        user.force_mfa = True

    previous_logins = db.query(LoginSession).filter(LoginSession.user_id == user.id, LoginSession.is_active == True).all()
    formatted_previous_logins = [(l.ip_address, l.device_fingerprint, l.created_at) for l in previous_logins]
    is_suspicious, reason = is_suspicious_login(user.id, client_ip, request.device_fingerprint, formatted_previous_logins)
    if is_suspicious:
        user.force_mfa = True
        db.commit()

    if user.mfa_enabled or user.force_mfa:
        mfa_token = create_access_token(data={"sub": user.username, "type": "mfa", "session": secrets.token_hex(16)}, expires_delta=timedelta(minutes=5))
        return {"mfa_required": True, "mfa_token": mfa_token, "force_mfa": user.force_mfa}

    access_token, refresh_token = create_session_tokens(user, db, request.device_fingerprint, client_ip)
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "role": user.role,
        "username": user.username,
        "mfa_required": False
    }


@router.post("/auth/admin-login")
async def admin_login(request: UserLoginRequest, db = Depends(get_db)):
    request.username = request.username.lower()
    user = db.query(User).filter(User.username == request.username, User.role == "admin").first()
    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid admin credentials")
    return await login(request, db)


@router.post("/auth/signup")
async def signup(request: UserSignupRequest, db = Depends(get_db)):
    request.username = request.username.lower()
    client_ip = get_client_ip(request.ip_address)
    existing_user = db.query(User).filter(User.username == request.username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already exists")

    is_strong, reason = validate_password_strength(request.password)
    if not is_strong:
        raise HTTPException(status_code=400, detail=f"Password strength failed: {reason}")

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
    db.flush()
    password_history = PasswordHistory(user_id=new_user.id, password_hash=password_hash, changed_at=datetime.utcnow())
    db.add(password_history)
    db.commit()

    access_token, refresh_token = create_session_tokens(new_user, db, request.device_fingerprint, client_ip)
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "role": new_user.role,
        "username": new_user.username,
        "message": "Account created successfully. You can setup MFA in settings."
    }


@router.post("/auth/verify-mfa")
async def verify_mfa(request: VerifyMfaRequest, db = Depends(get_db)):
    payload = decode_mfa_token(request.mfa_token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid MFA token")

    username = payload.get("sub")
    user = db.query(User).filter(User.username == username).first()
    if not user or not user.mfa_secret:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="MFA not configured")

    if not verify_totp(user.mfa_secret, request.mfa_code):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid MFA code")

    access_token = create_access_token(data={"sub": user.username, "role": user.role})
    refresh_token = create_refresh_token(data={"sub": user.username})
    login_session = LoginSession(
        user_id=user.id,
        access_token=access_token,
        refresh_token=refresh_token,
        device_fingerprint=request.mfa_token[:32],
        ip_address="web",
        user_agent="web",
        created_at=datetime.utcnow(),
        expires_at=datetime.utcnow() + timedelta(minutes=15),
        refresh_expires_at=datetime.utcnow() + timedelta(days=7),
        is_active=True
    )
    db.add(login_session)
    db.commit()

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "role": user.role,
        "username": user.username
    }


@router.post("/auth/setup-mfa")
async def setup_mfa(request: SetupMfaRequest, db = Depends(get_db)):
    user = db.query(User).filter(User.username == request.username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.mfa_enabled:
        raise HTTPException(status_code=400, detail="MFA already enabled for this user")

    secret = generate_mfa_secret()
    temp_mfa_secrets[request.username] = secret
    qr_uri = get_totp_provisioning_uri(secret, user.username, issuer="CyberSecurityChatbot")

    qr_code_base64 = ""
    if qrcode is not None:
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(qr_uri)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        qr_code_base64 = base64.b64encode(buffer.getvalue()).decode()

    return {
        "mfa_secret": secret,
        "qr_code_url": f"data:image/png;base64,{qr_code_base64}" if qr_code_base64 else "",
        "provisioning_uri": qr_uri,
        "message": "Scan QR code with authenticator app. Enter code to confirm setup."
    }


@router.post("/auth/confirm-mfa-setup")
async def confirm_mfa_setup(request: ConfirmMfaSetupRequest, db = Depends(get_db)):
    user = db.query(User).filter(User.username == request.username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    secret = temp_mfa_secrets.get(request.username)
    if not secret:
        raise HTTPException(status_code=400, detail="MFA setup session expired")

    if not verify_totp(secret, request.mfa_code):
        raise HTTPException(status_code=400, detail="Invalid MFA code")

    user.mfa_secret = secret
    user.mfa_enabled = True
    user.updated_at = datetime.utcnow()
    db.commit()
    del temp_mfa_secrets[request.username]

    return {"message": "MFA setup successful", "status": "enabled"}


@router.post("/auth/user/setup-mfa")
async def user_setup_mfa(request: SetupMfaRequest, db = Depends(get_db)):
    return await setup_mfa(request, db)


@router.post("/auth/user/confirm-mfa")
async def user_confirm_mfa(request: ConfirmMfaSetupRequest, db = Depends(get_db)):
    return await confirm_mfa_setup(request, db)


@router.post("/auth/refresh-token")
async def refresh_token_endpoint(request: RefreshTokenRequest, db = Depends(get_db)):
    payload = decode_refresh_token(request.refresh_token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    username = payload.get("sub")
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    login_session = db.query(LoginSession).filter(
        LoginSession.refresh_token == request.refresh_token,
        LoginSession.is_active == True
    ).first()

    if not login_session:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh session invalid")

    access_token = create_access_token(data={"sub": user.username, "role": user.role})
    login_session.access_token = access_token
    login_session.expires_at = datetime.utcnow() + timedelta(minutes=15)
    db.commit()

    return {
        "access_token": access_token,
        "refresh_token": request.refresh_token,
        "token_type": "bearer"
    }
