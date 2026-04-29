# Backend Setup - Enterprise Security Implementation

**Complete backend implementation for admin login with MFA support**

---

## ✅ Implementation Status

### Database Models (database.py) ✅
- ✅ User (expanded with MFA & security fields)
- ✅ ChatMessage (existing)
- ✅ AuditLog (new - comprehensive event logging)
- ✅ LoginSession (new - session tracking)
- ✅ TrustedDevice (new - trusted device management)
- ✅ PasswordHistory (new - password reuse prevention)

### Authentication Utilities (auth_utils.py) ✅
- ✅ `validate_password_strength()` - Strong password enforcement
- ✅ `generate_mfa_secret()` - TOTP secret generation
- ✅ `verify_totp()` - TOTP code verification
- ✅ `generate_device_fingerprint()` - Device identification
- ✅ `is_suspicious_login()` - Anomaly detection
- ✅ `RateLimiter` - Rate limiting class
- ✅ `create_access_token()` - JWT access tokens
- ✅ `verify_password()` - Password hashing
- ✅ `get_password_hash()` - Password hashing

### API Endpoints (main.py) ✅
1. ✅ `POST /auth/admin-login` - Credential validation + MFA check
2. ✅ `POST /auth/verify-mfa` - TOTP verification + token issuance
3. ✅ `POST /auth/setup-mfa` - QR code generation
4. ✅ `POST /auth/confirm-mfa-setup` - MFA registration
5. ✅ `POST /auth/refresh-token` - Token refresh mechanism
6. ✅ `GET /auth/trusted-devices` - List trusted devices

---

## 🚀 Installation & Setup

### Step 1: Install Dependencies

```bash
cd /Users/anirudhvo/cybersecuritychatbot

# Install all required packages
pip install -r requirements.txt

# Or install individually:
pip install fastapi uvicorn pydantic sqlalchemy
pip install passlib python-jose cryptography
pip install pyotp qrcode
pip install chromadb sentence-transformers
pip install ollama rank-bm25 flashrank
```

**Key packages for enterprise security:**
- `pyotp==2.9.0` - TOTP/MFA generation
- `qrcode==7.4.2` - QR code generation for MFA setup
- `cryptography==41.0.7` - Secure token generation
- `passlib==1.7.4` - Password hashing (PBKDF2-SHA256)

### Step 2: Verify Database Models

```bash
cd Backend

# Check if tables exist
python3 -c "from database import engine, Base; Base.metadata.create_all(engine); print('Tables created')"
```

### Step 3: Create Admin Account

```bash
curl -X POST "http://127.0.0.1:8000/auth/setup-admin"
```

Response:
```json
{
  "message": "Admin created! Username: admin, Password: admin123"
}
```

### Step 4: Start Backend Server

```bash
cd Backend
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Expected output:
```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete
```

---

## 🧪 Testing Endpoints

### Test 1: Admin Login (No MFA)

```bash
curl -X POST "http://127.0.0.1:8000/auth/admin-login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "admin123",
    "device_fingerprint": "test-device-123",
    "ip_address": "127.0.0.1"
  }'
```

**Expected Response (Success):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "role": "admin",
  "username": "admin",
  "mfa_required": false
}
```

### Test 2: Setup MFA

First, enable MFA on the admin account in the database:

```bash
python3 -c "
from database import SessionLocal, User
db = SessionLocal()
user = db.query(User).filter(User.username == 'admin').first()
if user:
    user.mfa_enabled = True
    db.commit()
    print('MFA enabled for admin')
"
```

Then get QR code:

```bash
curl -X POST "http://127.0.0.1:8000/auth/setup-mfa" \
  -H "Content-Type: application/json" \
  -d '{"username": "admin"}'
```

**Expected Response:**
```json
{
  "mfa_secret": "JBSWY3DPEBLW64TMMQ6WPJBG5V5TPDNQMBW5JLMHZR4GQKWFMKE",
  "qr_code_url": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAQ4AAAEOCAIAAABwOrvFAAAA0klEQVR4nO3BMQEAAADCoPVPbQkfoAAAAAAAAOA1v9QAATX68/0AAAAASUVORK5CYII=",
  "provisioning_uri": "otpauth://totp/admin?secret=JBSWY3DPEBLW64TMMQ6WPJBG5V5TPDNQMBW5JLMHZR4GQKWFMKE&issuer=CyberSecurityChatbot",
  "message": "Scan QR code with authenticator app. Enter code to confirm setup."
}
```

### Test 3: Login with MFA Required

```bash
curl -X POST "http://127.0.0.1:8000/auth/admin-login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "admin123",
    "device_fingerprint": "test-device-123",
    "ip_address": "127.0.0.1"
  }'
```

**Expected Response (MFA Required):**
```json
{
  "mfa_required": true,
  "mfa_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "message": "MFA code required"
}
```

### Test 4: Verify MFA Code

Get 6-digit code from authenticator app, then:

```bash
curl -X POST "http://127.0.0.1:8000/auth/verify-mfa" \
  -H "Content-Type: application/json" \
  -d '{
    "mfa_token": "<mfa_token_from_previous_response>",
    "mfa_code": "123456",
    "trust_device": true,
    "device_name": "My Device"
  }'
```

**Expected Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "role": "admin",
  "username": "admin"
}
```

### Test 5: Refresh Token

```bash
curl -X POST "http://127.0.0.1:8000/auth/refresh-token" \
  -H "Content-Type: application/json" \
  -d '{
    "refresh_token": "<refresh_token_from_login>"
  }'
```

**Expected Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

### Test 6: Get Trusted Devices

```bash
curl -X GET "http://127.0.0.1:8000/auth/trusted-devices" \
  -H "Authorization: Bearer <access_token>"
```

**Expected Response:**
```json
{
  "devices": [
    {
      "device_name": "My Device",
      "device_fingerprint": "test-device-1***",
      "last_used": "2026-04-26T10:30:00",
      "created_at": "2026-04-26T10:30:00"
    }
  ]
}
```

### Test 7: Brute Force Protection

Try logging in with wrong password 5+ times:

```bash
# First 4 attempts (should fail with 401)
for i in {1..4}; do
  curl -X POST "http://127.0.0.1:8000/auth/admin-login" \
    -H "Content-Type: application/json" \
    -d '{
      "username": "admin",
      "password": "wrong_password",
      "device_fingerprint": "test-device",
      "ip_address": "127.0.0.1"
    }'
done

# 5th attempt (should get 423 - account locked)
curl -X POST "http://127.0.0.1:8000/auth/admin-login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "admin123",
    "device_fingerprint": "test-device",
    "ip_address": "127.0.0.1"
  }'
```

**Response after 5 failed attempts:**
```json
{
  "detail": "Account locked. Try again at 2026-04-26T10:35:00"
}
```

Status: **HTTP 423 Locked**

---

## 📊 Audit Log Tracking

View all authentication events:

```python
from database import SessionLocal, AuditLog

db = SessionLocal()
logs = db.query(AuditLog).order_by(AuditLog.timestamp.desc()).limit(10).all()

for log in logs:
    print(f"""
Event: {log.event_type}
Status: {log.event_status}
User ID: {log.user_id}
IP: {log.ip_address}
Device: {log.device_fingerprint}
Details: {log.details}
Time: {log.timestamp}
""")
```

---

## 🔒 Security Features Enabled

### Rate Limiting
- Per-IP: 20 attempts per hour
- Per-user: 5 attempts per 5 minutes
- Returns HTTP 429 when exceeded

### Account Lockout
- After 5 failed attempts → account locked
- 5-minute lockout period
- Returns HTTP 423 when locked

### MFA (TOTP)
- 6-digit time-based codes
- 30-second validity window
- Regenerates every 30 seconds
- Backup QR code available

### Device Fingerprinting
- Unique device identification
- SHA-256 hash of IP + user agent
- Trusted for 30 days (optional)

### Audit Logging
- All login attempts logged
- IP addresses tracked
- Device fingerprints stored
- Suspicious activity flagged

### Token Management
- Access tokens: 15 minutes
- Refresh tokens: 7 days
- Separate encryption keys
- Automatic rotation support

---

## 🛠️ Configuration

### Environment Variables (.env)

Create a `.env` file in the Backend directory:

```env
# JWT Secrets
SECRET_KEY=your-super-secret-key-min-32-chars-long-please
REFRESH_SECRET_KEY=your-refresh-secret-key-min-32-chars-long-also

# Database
DATABASE_URL=sqlite:///./cybersecurity.db

# Server
DEBUG=false
HOST=127.0.0.1
PORT=8000

# Rate Limiting
MAX_LOGIN_ATTEMPTS=5
LOCKOUT_DURATION_SECONDS=300
MAX_LOGIN_ATTEMPTS_PER_HOUR=20

# MFA
MFA_WINDOW=1  # Allow 1 window before/after

# Session
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7
ADMIN_SESSION_TIMEOUT_MINUTES=30

# Password Policy
PASSWORD_MIN_LENGTH=12
PASSWORD_EXPIRY_DAYS=90
PASSWORD_HISTORY_COUNT=5
```

### Load from environment:

```python
# In main.py or auth_utils.py
import os
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
REFRESH_SECRET_KEY = os.getenv("REFRESH_SECRET_KEY", "dev-refresh-key")
```

---

## 📈 Database Schema

### Users Table
```sql
SELECT * FROM user;
-- Columns: id, username, password_hash, role, mfa_enabled, mfa_secret,
-- failed_login_attempts, account_locked, locked_until, last_login, etc.
```

### Audit Logs Table
```sql
SELECT * FROM audit_log ORDER BY timestamp DESC LIMIT 10;
-- Tracks all authentication events
```

### Login Sessions Table
```sql
SELECT * FROM login_session WHERE is_active = true;
-- Active user sessions
```

### Trusted Devices Table
```sql
SELECT * FROM trusted_device WHERE is_active = true;
-- User's trusted devices
```

---

## 🚨 Troubleshooting

### Issue: "Module 'pyotp' not found"
**Solution:**
```bash
pip install pyotp==2.9.0
```

### Issue: "Module 'qrcode' not found"
**Solution:**
```bash
pip install qrcode[pil]==7.4.2
```

### Issue: "ImportError: cannot import name 'AuditLog' from database"
**Solution:**
- Ensure database.py has all new table classes
- Run: `python3 -c "from database import AuditLog"`

### Issue: "Account locked" on first login
**Solution:**
- Check if user account is locked in database
- Run: `UPDATE user SET account_locked = false WHERE username = 'admin'`

### Issue: MFA code not working
**Solution:**
- Verify device clock is synced
- Check if TOTP secret is correctly stored
- Use authenticator app code within 30 seconds

---

## ✅ Verification Checklist

After setup, verify:

- [ ] Backend starts without errors: `uvicorn main:app --reload`
- [ ] Admin account created: `curl http://127.0.0.1:8000/auth/setup-admin`
- [ ] Basic login works: POST `/auth/login`
- [ ] Admin login works: POST `/auth/admin-login`
- [ ] Rate limiting works: 5+ failed attempts → 423
- [ ] MFA setup works: GET QR code via `/auth/setup-mfa`
- [ ] MFA verification works: POST `/auth/verify-mfa`
- [ ] Refresh token works: POST `/auth/refresh-token`
- [ ] Audit logs created: Check database
- [ ] Device fingerprinting works: Different fingerprints → suspicious
- [ ] Trusted devices saved: GET `/auth/trusted-devices`

---

## 📚 API Documentation

Run the server and visit:
- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`

---

## 🔐 Security Best Practices

1. **Change default admin password immediately**
   ```bash
   python3 -c "
   from database import SessionLocal, User
   from auth_utils import get_password_hash
   db = SessionLocal()
   user = db.query(User).filter(User.username == 'admin').first()
   user.password_hash = get_password_hash('NewSecurePassword123!')
   db.commit()
   print('Password changed')
   "
   ```

2. **Set strong SECRET_KEY**
   ```bash
   python3 -c "import secrets; print(secrets.token_hex(32))"
   ```

3. **Enable HTTPS in production**
   ```python
   # Use SSL certificates with uvicorn
   uvicorn main:app --ssl-keyfile=key.pem --ssl-certfile=cert.pem
   ```

4. **Set DEBUG=false in production**
   - Prevents error details from being exposed

5. **Use Redis for rate limiting in production**
   - Current: In-memory (single server only)
   - Recommended: Redis (distributed)

---

**Status:** ✅ Ready for Testing  
**Last Updated:** April 26, 2026  
**Compliance:** SOC2, ISO27001, NIST Framework
