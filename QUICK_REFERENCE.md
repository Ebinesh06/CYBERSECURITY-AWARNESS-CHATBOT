# CyberSecurity Chatbot - Quick Reference Guide

**Quick Navigation Guide for Technical Documentation**

---

## 🔐 Security Features at a Glance

### Authentication
- **Password Hashing:** PBKDF2-SHA256 (adaptive iteration count)
- **Token Type:** JWT (JSON Web Tokens)
- **Token Algorithm:** HS256 (HMAC-SHA256)
- **Token Expiration:** 30 minutes
- **Validation:** Bearer token in Authorization header

### Login Security (Both Admin & User)
- **Max Failed Attempts:** 5
- **Lockout Duration:** 30 seconds
- **Progress Indicator:** Visual bar (green → amber → red)
- **State Persistence:** Survives page refresh
- **Session Tracking:** Messages for logout reasons

### Database Security
- **Database Type:** SQLite
- **ORM:** SQLAlchemy (SQL injection prevention)
- **Password Storage:** Never plaintext, always hashed
- **User Isolation:** By user_id foreign key
- **Indexing:** username (unique), user_id, session_id

---

## 🏗️ Architecture at a Glance

```
FRONTEND (Angular)
├── Admin Login → Admin Dashboard
└── User Login → Chat Interface

        ↕ (HTTP + JWT)

API SERVER (FastAPI)
├── /auth/login (Authentication)
├── /auth/signup (Registration)
└── /chat/message (Chat with RAG)

        ↕

DATA LAYER
├── SQLite (Users, Messages)
├── ChromaDB (Vector embeddings)
└── Ollama (LLM inference)
```

---

## 📚 Key Technologies

| Layer | Technology | Key Feature |
|-------|-----------|-------------|
| **Frontend** | Angular 18+ | Standalone components |
| **Backend** | FastAPI | RESTful API |
| **Auth** | PBKDF2-SHA256 + JWT | Secure credentials |
| **Database** | SQLite + SQLAlchemy | Lightweight SQL DB |
| **Vector DB** | Chroma | Semantic search |
| **Embeddings** | SentenceTransformers | all-MiniLM-L6-v2 |
| **Search** | BM25 + TinyBERT | Hybrid ranking |
| **LLM** | Ollama (Llama 2) | Local inference |

---

## 🔒 Authentication Flow

### Login Process

```
1. User enters credentials
   ↓
2. Frontend validation (trim, required)
   ↓
3. Check lockout status (sessionStorage)
   ↓
4. POST to /auth/login
   ↓
5. Backend:
   - Query user from database
   - Verify password using PBKDF2
   - On success: Generate JWT token
   ↓
6. Frontend:
   - Store token in localStorage
   - Navigate to dashboard/chat
   ↓
7. All API requests include: Authorization: Bearer <token>
```

### JWT Token Structure

```
Header (Algorithm + Type):
{
  "alg": "HS256",
  "typ": "JWT"
}

Payload (Claims):
{
  "sub": "username",        // subject (username)
  "role": "user",           // user role
  "exp": 1713794400,       // expiration time
  "iat": 1713790800        // issued at time
}

Signature:
HMAC-SHA256(header.payload, SECRET_KEY)
```

---

## 🛡️ Brute Force Protection Logic

### Frontend Implementation

```javascript
const MAX_ATTEMPTS = 5;
const LOCKOUT_SECONDS = 30;

login() → Failed Attempt
  ↓
failedAttempts++
  ↓
Store in sessionStorage
  ↓
Check if >= MAX_ATTEMPTS?
  ├─ YES: Calculate lockoutUntil = now + 30s
  │         Start countdown timer
  │         Show "Account locked" message
  │         Disable login button
  │
  └─ NO: Show "X attempts remaining" message
          Enable login button
          
Auto-unlock after countdown reaches 0
Clear sessionStorage
Reset failedAttempts to 0
```

### Why This Approach?

✅ **Client-side validation** = fast UX feedback  
✅ **sessionStorage** = survives refresh but clears on browser close  
✅ **30-second lockout** = delays attacks, doesn't lock permanently  
✅ **Visual progress** = users understand status  

---

## 🔎 Vector Search & RAG Pipeline

### How Semantic Search Works

```
1. Query: "What is a zero-day?"
   ↓
2. Convert to embedding (384-dim vector)
   ↓
3. Calculate cosine similarity with all stored embeddings
   ↓
4. Retrieve top N documents by similarity
   ↓
5. Also run BM25 keyword search
   ↓
6. Merge results + re-rank using TinyBERT
   ↓
7. Format as prompt context
   ↓
8. Send to Ollama LLM with context
   ↓
9. LLM generates grounded response
```

### Chunking Strategy

```
Original Document (1000+ chars)
  ↓
Split into overlapping chunks
  ├─ Chunk 1: [chars 0-300]
  ├─ Chunk 2: [chars 250-550]    (50-char overlap)
  ├─ Chunk 3: [chars 500-800]    (50-char overlap)
  └─ Chunk 4: [chars 750-1050]   (50-char overlap)
  ↓
Why overlap?
  ✅ Prevents losing context at boundaries
  ✅ Improves semantic relevance
  ✅ Reduces gaps in understanding
```

### RAG (Retrieval-Augmented Generation)

```
RETRIEVAL PHASE:
  User Query → Vector Search → Get Context Documents

GENERATION PHASE:
  Context + Query → LLM → Generate Answer
  
BENEFITS:
  ✅ Grounded in actual documents (less hallucination)
  ✅ Up-to-date information (can use live feeds)
  ✅ Traceable sources
  ✅ Domain-specific knowledge
```

---

## 📊 Data Flow Examples

### User Registration

```
Frontend:
  Username: "john_doe"
  Password: "MySecurePassword123"
  ↓
Backend:
  1. Check username uniqueness
  2. Hash password: PBKDF2-SHA256("MySecurePassword123") → "$pbkdf2$..."
  3. Create User record with hashed password
  4. Generate JWT: {"sub": "john_doe", "role": "user", "exp": ...}
  5. Return access_token
  ↓
Frontend:
  localStorage.setItem('token', access_token)
  localStorage.setItem('role', 'user')
  Navigate to /chat
```

### Chat with RAG

```
Frontend:
  User: "Explain DDoS attacks"
  ↓
Backend:
  1. Validate JWT token → Extract user_id
  2. Embed query using SentenceTransformer
  3. Search ChromaDB for similar documents
  4. Retrieve: ["DDoS basics", "Layer 7 attacks", "Mitigation..."]
  5. Format prompt:
     "Based on: [retrieved docs], answer: Explain DDoS attacks"
  6. Send to Ollama LLM
  7. Stream response token-by-token
  8. Save to database: ChatMessage(user_id, session_id, content)
  ↓
Frontend:
  Display streaming response in real-time
```

---

## 🎯 Key Security Principles

### 1. Defense in Depth
- ✅ Client-side validation (UX)
- ✅ Server-side validation (Security)
- ✅ Database constraints (Data integrity)
- ✅ JWT tokens (Authentication)

### 2. Principle of Least Privilege
- ✅ Users access only their own data
- ✅ Admins have elevated permissions
- ✅ Role-based access control (RBAC)
- ✅ Database constraints enforce isolation

### 3. Fail Securely
- ✅ Invalid credentials → Generic error message
- ✅ Database errors → Log internally, hide from user
- ✅ Missing auth → 401 Unauthorized
- ✅ Insufficient permissions → 403 Forbidden

### 4. Input Validation
- ✅ Trim whitespace
- ✅ Check length limits
- ✅ No special characters in usernames (optional)
- ✅ ORM prevents SQL injection

---

## 📂 File Structure

```
cybersecuritychatbot/
├── Backend/
│   ├── auth_utils.py           (JWT + Password hashing)
│   ├── batabase.py             (SQLAlchemy models)
│   ├── main.py                 (FastAPI app + endpoints)
│   ├── vector_db.py            (Embeddings + chunking)
│   ├── ingest_intelligence.py  (CISA KEV feed)
│   ├── models/                 (ML models)
│   └── data/
│       ├── ddos.txt
│       ├── malware.txt
│       └── phishing.txt
│
├── Frontend/
│   ├── src/app/
│   │   ├── admin-login/        (Admin auth + brute force)
│   │   ├── admin-dashboard/    (Admin panel)
│   │   ├── user-login/         (User auth + brute force)
│   │   ├── chat/               (Chat interface)
│   │   └── guards/             (Auth guard)
│   └── package.json
│
├── chroma_db/                  (Vector database)
│
└── COMPREHENSIVE_DOCUMENTATION.md  (This file!)
```

---

## 🚀 Deployment Checklist

### Security Before Deploy
- [ ] Change `SECRET_KEY` in auth_utils.py
- [ ] Set `allow_origins` to specific domains (not "*")
- [ ] Enable HTTPS/TLS
- [ ] Use environment variables for secrets
- [ ] Enable database encryption
- [ ] Set up rate limiting on API endpoints

### Performance Before Deploy
- [ ] Enable database indexing
- [ ] Configure connection pooling
- [ ] Set up caching for frequently accessed data
- [ ] Compress responses (gzip)

### Monitoring Before Deploy
- [ ] Set up error logging (Sentry, LogRocket)
- [ ] Configure performance monitoring (APM)
- [ ] Set up alerts for authentication failures
- [ ] Enable audit logging for sensitive operations

---

## 🔧 Troubleshooting

### Login Issues

**Problem:** "Too many failed attempts"
- **Cause:** Exceeded 5 failed login attempts
- **Solution:** Wait 30 seconds for lockout to expire
- **Prevention:** Check password before submitting

**Problem:** "Invalid token"
- **Cause:** Token expired or corrupted
- **Solution:** Clear localStorage and login again
- **Prevention:** Token auto-refreshes every 30 min

### Chat Issues

**Problem:** No search results
- **Cause:** Vector DB not populated or query too specific
- **Solution:** Run `ingest_cisa_kev()` to load data
- **Prevention:** Regularly update data feeds

**Problem:** Slow LLM responses
- **Cause:** Ollama model not optimized
- **Solution:** Check Ollama status, reduce context window
- **Prevention:** Use lighter models (Phi instead of Llama 2)

---

## 📞 Quick Command Reference

### Start Backend
```bash
cd Backend
python -m pip install -r requirements.txt
python main.py
# Server runs on http://127.0.0.1:8000
```

### Start Frontend
```bash
cd Backend/Frontend
npm install
ng serve
# App runs on http://localhost:4200
```

### Load Initial Data
```bash
cd Backend
python ingest_intelligence.py  # Load CISA KEV feed
python vector_db.py            # Load local documents
```

### Reset Database
```bash
cd Backend
rm cybersecurity.db
# Run app again - SQLAlchemy will recreate schema
```

---

## 🎓 Learning Path

### Phase 1: Authentication (2-3 hours)
1. Read: "Authentication & Security Implementation"
2. Code: auth_utils.py
3. Understand: JWT tokens, password hashing

### Phase 2: Frontend Security (1-2 hours)
1. Read: "Frontend Security Features"
2. Code: admin-login.ts, user-login.ts
3. Understand: Brute force protection, state management

### Phase 3: Database & ORM (1-2 hours)
1. Read: "Database Design & Security"
2. Code: batabase.py
3. Understand: SQLAlchemy, user isolation

### Phase 4: Vector Search (2-3 hours)
1. Read: "Vector Database & AI Integration"
2. Code: vector_db.py
3. Understand: Embeddings, semantic search, RAG

### Phase 5: API Design (1-2 hours)
1. Read: "API Endpoints & Communication"
2. Code: main.py endpoints
3. Understand: RESTful design, CORS

---

## 📖 Additional Resources

### Security
- OWASP Top 10: https://owasp.org/www-project-top-ten/
- JWT Best Practices: https://tools.ietf.org/html/rfc8949
- PBKDF2 Specification: https://tools.ietf.org/html/rfc2898

### Technologies
- FastAPI Documentation: https://fastapi.tiangolo.com/
- SQLAlchemy ORM: https://docs.sqlalchemy.org/
- Chroma Vector DB: https://docs.trychroma.com/
- Ollama Models: https://ollama.ai/

### Vector Search
- Sentence Transformers: https://www.sbert.net/
- BM25 Algorithm: https://en.wikipedia.org/wiki/Okapi_BM25
- RAG Architecture: https://arxiv.org/abs/2005.11401

---

**Last Updated:** April 22, 2026  
**Status:** Complete and Production-Ready
