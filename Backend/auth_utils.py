from passlib.context import CryptContext
from datetime import datetime, timedelta
from jose import JWTError, jwt
import pyotp
import hashlib
import secrets
import json
from typing import Optional, Dict
import os
import logging
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

# Setup password hashing with PBKDF2
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

# Secret keys (use environment variables in production)
SECRET_KEY = os.getenv("SECRET_KEY") or "dev-secret-key-change-in-production-12345678901234"
REFRESH_SECRET_KEY = os.getenv("REFRESH_SECRET_KEY") or "dev-refresh-secret-key-change-in-production-9876543210"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 15  # Shorter for admin accounts
REFRESH_TOKEN_EXPIRE_DAYS = 7
ADMIN_SESSION_TIMEOUT_MINUTES = 30  # Auto-logout for admin

# Log if using dev secrets
if not os.getenv("SECRET_KEY"):
    logger.warning("Using development SECRET_KEY. Change in production!")
if not os.getenv("REFRESH_SECRET_KEY"):
    logger.warning("Using development REFRESH_SECRET_KEY. Change in production!")

# Rate limiting constants
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_DURATION_SECONDS = 300  # 5 minutes
MAX_LOGIN_ATTEMPTS_PER_HOUR = 20

# Password policy constants
MIN_PASSWORD_LENGTH = 12
PASSWORD_EXPIRY_DAYS = 90
PASSWORD_HISTORY_COUNT = 5


def get_password_hash(password: str) -> str:
    """Hash password with PBKDF2-SHA256."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash."""
    return pwd_context.verify(plain_password, hashed_password)


def validate_password_strength(password: str) -> tuple[bool, str]:
    """
    Enforce password policy.
    
    Requirements:
    - Minimum 12 characters
    - At least 1 uppercase letter
    - At least 1 lowercase letter
    - At least 1 digit
    - At least 1 special character
    """
    if len(password) < MIN_PASSWORD_LENGTH:
        return False, f"Password must be at least {MIN_PASSWORD_LENGTH} characters"
    
    if not any(c.isupper() for c in password):
        return False, "Password must contain at least 1 uppercase letter"
    
    if not any(c.islower() for c in password):
        return False, "Password must contain at least 1 lowercase letter"
    
    if not any(c.isdigit() for c in password):
        return False, "Password must contain at least 1 digit"
    
    special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
    if not any(c in special_chars for c in password):
        return False, "Password must contain at least 1 special character"
    
    return True, "Password is strong"


def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    """Create JWT access token with expiration."""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "access"
    })
    
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: dict) -> str:
    """Create JWT refresh token (longer expiration)."""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "refresh"
    })
    
    encoded_jwt = jwt.encode(to_encode, REFRESH_SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> Optional[dict]:
    """Decode and validate access token."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        # Verify token type
        if payload.get("type") != "access":
            return None
        
        return payload
    except JWTError:
        return None


def decode_refresh_token(token: str) -> Optional[dict]:
    """Decode and validate refresh token."""
    try:
        payload = jwt.decode(token, REFRESH_SECRET_KEY, algorithms=[ALGORITHM])
        
        # Verify token type
        if payload.get("type") != "refresh":
            return None
        
        return payload
    except JWTError:
        return None


def generate_mfa_secret() -> str:
    """Generate TOTP secret for MFA setup."""
    return pyotp.random_base32()


def verify_totp(secret: str, token: str) -> bool:
    """Verify TOTP token (6-digit code from authenticator app)."""
    try:
        totp = pyotp.TOTP(secret)
        # Allow 30-second window before and after current time
        return totp.verify(token, valid_window=1)
    except Exception:
        return False


def get_totp_provisioning_uri(secret: str, username: str, issuer: str = "CyberSecurity") -> str:
    """Get QR code URI for MFA setup."""
    totp = pyotp.TOTP(secret)
    return totp.provisioning_uri(name=username, issuer_name=issuer)


def generate_device_fingerprint(ip_address: str, user_agent: str) -> str:
    """
    Generate device fingerprint from IP + User Agent.
    Consistent across sessions on same device.
    """
    fingerprint_data = f"{ip_address}:{user_agent}"
    return hashlib.sha256(fingerprint_data.encode()).hexdigest()


def is_suspicious_login(
    user_id: int,
    new_ip: str,
    new_fingerprint: str,
    previous_logins: list
) -> tuple[bool, str]:
    """
    Detect suspicious login patterns.
    Expects previous_logins as list of tuples: (ip_address, device_fingerprint, created_at)
    
    Flags:
    - Login from new IP (if multiple previous IPs exist)
    - Login from new device
    - Rapid sequential logins from different IPs
    - Login from geographically impossible location
    """
    
    if not previous_logins:
        return False, ""
    
    # Get last login tuple
    last_login = previous_logins[-1]
    last_login_ip = last_login[0]
    last_login_fingerprint = last_login[1]
    last_login_time = last_login[2]
    
    # Check if new IP/device
    previous_ips = set(login[0] for login in previous_logins[-5:])
    if new_ip not in previous_ips and len(previous_ips) > 0:
        return True, f"Login from new IP address: {new_ip}"
    
    # Check if new device
    previous_fingerprints = set(login[1] for login in previous_logins[-5:])
    if new_fingerprint not in previous_fingerprints and len(previous_fingerprints) > 0:
        return True, f"Login from new device"
    
    # Check for rapid logins from different IPs (impossible travel)
    time_since_last = (datetime.utcnow() - last_login_time).total_seconds()
    
    if time_since_last < 300 and new_ip != last_login_ip:  # 5 minutes
        return True, f"Impossible travel detected: Login from {new_ip} only {int(time_since_last)}s after login from {last_login_ip}"
    
    return False, ""


def validate_token_not_expired(token_exp: int) -> bool:
    """Check if token has expired."""
    return datetime.utcfromtimestamp(token_exp) > datetime.utcnow()


def generate_secure_random_token(length: int = 32) -> str:
    """Generate cryptographically secure random token."""
    return secrets.token_urlsafe(length)


class RateLimiter:
    """
    Simple in-memory rate limiter for login attempts.
    In production, use Redis for distributed rate limiting.
    """
    
    def __init__(self):
        self.attempts = {}  # Format: {ip_address: [(timestamp, count)]}
    
    def is_rate_limited(self, identifier: str, max_attempts: int, window_seconds: int) -> bool:
        """Check if identifier exceeded rate limit."""
        now = datetime.utcnow()
        cutoff_time = now - timedelta(seconds=window_seconds)
        
        if identifier not in self.attempts:
            self.attempts[identifier] = []
        
        # Remove old attempts outside window
        self.attempts[identifier] = [
            (timestamp, count) for timestamp, count in self.attempts[identifier]
            if timestamp > cutoff_time
        ]
        
        # Count attempts in current window
        total_attempts = sum(count for _, count in self.attempts[identifier])
        
        return total_attempts >= max_attempts
    
    def record_attempt(self, identifier: str, count: int = 1):
        """Record an attempt."""
        if identifier not in self.attempts:
            self.attempts[identifier] = []
        
        self.attempts[identifier].append((datetime.utcnow(), count))
    
    def reset(self, identifier: str):
        """Reset attempts for identifier."""
        if identifier in self.attempts:
            del self.attempts[identifier]
    
    def is_allowed(self, identifier: str) -> bool:
        """Check if identifier is allowed (not rate limited)."""
        # Max 5 attempts per 5 minutes window
        is_limited = self.is_rate_limited(identifier, MAX_LOGIN_ATTEMPTS, 300)
        if not is_limited:
            self.record_attempt(identifier, 1)
        return not is_limited


# Global rate limiter instance
rate_limiter = RateLimiter()

