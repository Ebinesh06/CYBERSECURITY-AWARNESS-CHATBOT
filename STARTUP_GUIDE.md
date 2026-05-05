# CyberBot Project - Complete Setup & Startup Guide

## Quick Start (5 minutes)

### Prerequisites
- Python 3.9+ with pip
- Node.js 18+ with npm
- Git

### Backend Setup

```bash
# 1. Navigate to Backend
cd Backend

# 2. Create and activate virtual environment
python -m venv venv

# Windows
venv\Scripts\activate

# Mac/Linux
source venv/bin/activate

# 3. Install dependencies
pip install -r ../requirements.txt

# 4. Initialize database
python init_db.py

# 5. Check ChromaDB
python check_db.py

# 6. Start backend (runs on http://127.0.0.1:8000)
python main.py
```

### Frontend Setup (New Terminal)

```bash
# 1. Navigate to Frontend
cd Frontend

# 2. Install dependencies
npm install

# 3. Start development server (runs on http://127.0.0.1:4200)
npm start
```

---

## Project Structure Overview

### Backend (FastAPI)
```
Backend/
├── main.py              # FastAPI app with all endpoints
├── database.py          # SQLAlchemy models & database setup
├── auth_utils.py        # Authentication & security utilities
├── vector_db.py         # Vector database integration
├── ingest_intelligence.py  # Data ingestion pipeline
├── check_db.py          # Database verification script
├── init_db.py           # Database initialization script
├── .env                 # Environment variables (local)
├── requirements.txt     # Python dependencies
├── chroma_db/           # ChromaDB storage
├── models/              # ML models (TinyBERT)
└── data/                # Intelligence data files
```

### Frontend (Angular)
```
Frontend/
├── src/
│   ├── app/
│   │   ├── app.routes.ts       # Main routing configuration
│   │   ├── app.config.ts       # Angular app configuration
│   │   ├── guards/
│   │   │   └── auth-guard.ts   # Route protection
│   │   ├── login/              # DEPRECATED - use user-login
│   │   ├── user-login/         # User authentication
│   │   ├── user-management/    # DEPRECATED - admin uses AdminUsersComponent
│   │   ├── chat/               # Main chat interface
│   │   ├── admin-login/        # Admin authentication
│   │   ├── admin-shell/        # Admin layout container
│   │   ├── admin-dashboard/    # Admin dashboard
│   │   ├── admin-users/        # User management
│   │   ├── admin-settings/     # Settings
│   │   └── admin-activity/     # Activity logs
│   └── environments/
│       └── environment.ts      # API configuration
└── package.json
```

---

## Active Components (Used in Routes)

✅ **User Features**
- `UserLoginComponent` - User login/signup
- `ChatComponent` - Chat interface

✅ **Admin Features**
- `AdminLoginComponent` - Admin authentication
- `AdminShellComponent` - Admin layout (container)
- `AdminDashboardComponent` - Operations overview
- `AdminUsersComponent` - User management
- `AdminSettingsComponent` - Configuration
- `AdminActivityComponent` - Audit logs

---

## Legacy Components (Not in Current Routes)

⚠️ These can be:
1. **Removed** if not needed
2. **Integrated** if they add value
3. **Kept** for future use

- `login/LoginComponent` - Duplicate of UserLoginComponent
- `user-management/UserManagementComponent` - Replaced by AdminUsersComponent

---

## API Endpoints Summary

### Authentication Endpoints
```
POST   /auth/setup-admin              # Create initial admin (run once)
POST   /auth/login                    # User login
POST   /auth/signup                   # User registration
POST   /auth/admin-login              # Admin login
POST   /auth/verify-mfa               # Verify 2FA code
POST   /auth/setup-mfa                # Setup 2FA for admin
POST   /auth/confirm-mfa-setup        # Confirm 2FA setup
POST   /auth/user/setup-mfa           # User 2FA setup
POST   /auth/user/confirm-mfa         # User confirm 2FA
POST   /auth/refresh-token            # Refresh access token
GET    /auth/trusted-devices          # List trusted devices
```

### Chat Endpoints
```
POST   /chat                          # Send chat message (streaming)
GET    /chat/sessions                 # List user's chat sessions
GET    /chat/sessions/{session_id}    # Get session messages
DELETE /chat/sessions/{session_id}    # Delete session
```

### Admin Endpoints
```
GET    /admin/users                   # List all users
DELETE /admin/users/{user_id}         # Delete user
```

---

## First-Time Setup Steps

### 1. Create Admin User
```bash
# The backend automatically creates admin on first run
# Or manually visit:
curl http://127.0.0.1:8000/auth/setup-admin
```

### 2. Access the Application
```
User Login:  http://127.0.0.1:4200/user-login
Admin Login: http://127.0.0.1:4200/admin-login
Chat:        http://127.0.0.1:4200/chat (after login)
```

### 3. Test Credentials
```
Username: admin
Password: admin123  (CHANGE THIS IN PRODUCTION!)
```

---

## Environment Variables (.env)

Located at: `Backend/.env`

**Critical Variables:**
```
SECRET_KEY=change-this-to-something-secret
REFRESH_SECRET_KEY=change-this-to-something-else
API_URL=http://127.0.0.1:8000
FRONTEND_URL=http://127.0.0.1:4200
```

---

## Troubleshooting

### Backend Won't Start
```bash
# 1. Check Python version
python --version  # Should be 3.9+

# 2. Install dependencies
pip install -r requirements.txt

# 3. Check if port 8000 is in use
netstat -ano | findstr :8000  # Windows
lsof -i :8000                 # Mac/Linux

# 4. Initialize database
python Backend/init_db.py
```

### Frontend Won't Start
```bash
# 1. Clear cache
rm -rf node_modules package-lock.json
npm install

# 2. Check Node version
node --version  # Should be 18+

# 3. Try a different port
ng serve --port 4201
```

### Database Errors
```bash
# Backup and reset database
python Backend/check_db.py          # Check status
rm Backend/cybersecurity.db         # Delete old
python Backend/init_db.py           # Reinitialize
```

### ChromaDB Issues
```bash
# Check ChromaDB status
python Backend/check_db.py

# Reset ChromaDB if needed
rm -rf Backend/chroma_db
python Backend/ingest_intelligence.py
```

---

## Security Notes

⚠️ **BEFORE PRODUCTION:**
1. Change SECRET_KEY in .env
2. Change REFRESH_SECRET_KEY in .env
3. Change default admin password
4. Enable HTTPS
5. Update CORS settings (not allow all origins)
6. Use proper database (PostgreSQL, not SQLite)
7. Add rate limiting configs
8. Enable MFA enforcement

---

## Running Tests

```bash
# Backend tests (if available)
python -m pytest Backend/

# Frontend tests
npm test
```

---

## Common Issues & Solutions

| Issue | Solution |
|-------|----------|
| CORS errors | Check frontend URL in Backend CORS config |
| Auth token expired | Refresh token or login again |
| Database locked | Close other instances, restart backend |
| Port 8000 in use | Change port in Backend/main.py |
| Module not found errors | Run `pip install -r requirements.txt` |
| Port 4200 in use | Use `ng serve --port 4201` |

---

## Project Status

✅ **Working Features:**
- User authentication with password strength validation
- MFA (TOTP) support for both users and admins
- Rate limiting and account lockout
- Session management with device tracking
- Chat interface with session history
- Admin dashboard with security metrics
- User management system
- Audit logging
- Vector database integration
- RAG pipeline with reranking

🔧 **Configuration Needed:**
- Environment variables (.env) - DONE
- API endpoints - All functional
- Database - Initialized

📝 **Components Reference:**
- Active routes: 8 components fully integrated
- Legacy components: 2 (kept for reference)
- All endpoints: 15+ fully functional

---

## Next Steps

1. ✅ Setup Backend: `cd Backend && python main.py`
2. ✅ Setup Frontend: `cd Frontend && npm install && npm start`
3. ✅ Access app: http://127.0.0.1:4200
4. ✅ Create account or login with admin/admin123
5. ✅ Start using chat interface

---

For detailed technical documentation, see: `COMPREHENSIVE_DOCUMENTATION.md`
