# CyberSecurity Chatbot - Implementation Guide

**Practical guide for developers to implement and extend the system**

---

## Quick Start

### 1. Installation & Setup

```bash
# Clone repository
git clone <repo-url>
cd cybersecuritychatbot

# Backend setup
cd Backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install fastapi uvicorn sqlalchemy python-jose passlib pbkdf2 \
            pydantic chromadb langchain langchain-community \
            sentence-transformers flashrank rank-bm25 ollama requests

# Run backend
python main.py
# Server runs on http://127.0.0.1:8000
```

```bash
# Frontend setup
cd ../Backend/Frontend
npm install
ng serve
# App runs on http://localhost:4200
```

### 2. Initialize Database

```bash
cd Backend
python -c "from batabase import Base, engine; Base.metadata.create_all(bind=engine)"
```

### 3. Load Data

```bash
python ingest_intelligence.py  # Load CISA KEV feed
python vector_db.py            # Process local documents
```

---

## Implementation Patterns

### Pattern 1: User Authentication

#### Backend Implementation

```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from auth_utils import verify_password, create_access_token, get_password_hash
from datetime import timedelta

app = FastAPI()

class LoginRequest(BaseModel):
    username: str
    password: str

@app.post("/auth/login")
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    """
    User login endpoint.
    
    Process:
    1. Validate input
    2. Query user from database
    3. Verify password hash
    4. Generate JWT token
    5. Return token to client
    """
    
    # 1. Validate input
    if not request.username or not request.password:
        raise HTTPException(status_code=400, detail="Missing credentials")
    
    # 2. Query user
    user = db.query(User).filter(User.username == request.username).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # 3. Verify password
    if not verify_password(request.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # 4. Generate token (30 minute expiration)
    token = create_access_token(
        data={"sub": user.username, "role": user.role},
        expires_delta=timedelta(minutes=30)
    )
    
    # 5. Return token
    return {
        "access_token": token,
        "token_type": "bearer",
        "username": user.username,
        "role": user.role
    }

@app.post("/auth/signup")
async def signup(request: LoginRequest, db: Session = Depends(get_db)):
    """User registration endpoint."""
    
    # Check username exists
    existing = db.query(User).filter(User.username == request.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username already taken")
    
    # Create user with hashed password
    hashed_pwd = get_password_hash(request.password)
    user = User(username=request.username, password_hash=hashed_pwd, role="user")
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # Generate token
    token = create_access_token(
        data={"sub": user.username, "role": user.role},
        expires_delta=timedelta(minutes=30)
    )
    
    return {
        "access_token": token,
        "token_type": "bearer",
        "username": user.username,
        "role": user.role
    }
```

#### Frontend Implementation

```typescript
export class LoginComponent {
  username = '';
  password = '';
  isLoading = false;
  errorMessage = '';
  
  constructor(
    private router: Router,
    private http: HttpClient
  ) {}
  
  login() {
    // 1. Validate
    if (!this.username.trim() || !this.password.trim()) {
      this.errorMessage = 'Username and password required';
      return;
    }
    
    this.isLoading = true;
    this.errorMessage = '';
    
    // 2. POST to backend
    this.http.post<any>('http://127.0.0.1:8000/auth/login', {
      username: this.username.trim(),
      password: this.password.trim()
    }).subscribe({
      next: (response) => {
        // 3. Store token
        localStorage.setItem('token', response.access_token);
        localStorage.setItem('role', response.role);
        localStorage.setItem('username', response.username);
        
        // 4. Navigate to dashboard
        this.router.navigate(['/chat']);
        this.isLoading = false;
      },
      error: (error) => {
        this.isLoading = false;
        this.errorMessage = 'Authentication failed';
      }
    });
  }
}
```

---

### Pattern 2: Brute Force Protection

#### Implementation

```typescript
const MAX_ATTEMPTS = 5;
const LOCKOUT_SECONDS = 30;

export class SecureLoginComponent {
  failedAttempts = 0;
  isLockedOut = false;
  
  ngOnInit() {
    // Restore lockout state on page load
    const lockoutUntil = Number(sessionStorage.getItem('lockoutUntil') || 0);
    this.failedAttempts = Number(sessionStorage.getItem('failedAttempts') || 0);
    
    if (lockoutUntil > Date.now()) {
      this.startLockoutCountdown(Math.ceil((lockoutUntil - Date.now()) / 1000));
    }
  }
  
  login() {
    // Prevent login if locked out
    if (this.isLockedOut) {
      return;
    }
    
    this.http.post('/auth/login', credentials).subscribe({
      next: (response) => {
        // Clear lockout on success
        this.clearLockout();
        this.navigateToChat();
      },
      error: () => {
        this.recordFailedAttempt();
      }
    });
  }
  
  private recordFailedAttempt() {
    this.failedAttempts++;
    sessionStorage.setItem('failedAttempts', String(this.failedAttempts));
    
    if (this.failedAttempts >= MAX_ATTEMPTS) {
      const until = Date.now() + LOCKOUT_SECONDS * 1000;
      sessionStorage.setItem('lockoutUntil', String(until));
      this.startLockoutCountdown(LOCKOUT_SECONDS);
    }
  }
  
  private startLockoutCountdown(seconds: number) {
    this.isLockedOut = true;
    let countdown = seconds;
    
    const timer = setInterval(() => {
      countdown--;
      if (countdown <= 0) {
        clearInterval(timer);
        this.clearLockout();
      }
    }, 1000);
  }
  
  private clearLockout() {
    this.isLockedOut = false;
    this.failedAttempts = 0;
    sessionStorage.removeItem('failedAttempts');
    sessionStorage.removeItem('lockoutUntil');
  }
}
```

---

### Pattern 3: Protected API Endpoints

#### Backend

```python
from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

def get_current_user(authorization: Optional[str] = Header(None), db: Session = Depends(get_db)):
    """
    Extract user from JWT token in Authorization header.
    Use this as a dependency for protected endpoints.
    """
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

@app.get("/chat/history")
async def get_history(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get chat history - only for authenticated users.
    User can only see their own messages.
    """
    messages = db.query(ChatMessage).filter(
        ChatMessage.user_id == current_user.id,
        ChatMessage.session_id == session_id
    ).all()
    
    return [
        {
            "id": msg.id,
            "role": msg.role,
            "content": msg.content,
            "created_at": msg.created_at
        }
        for msg in messages
    ]

@app.post("/chat/message")
async def send_message(
    message: str,
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Send message - user isolated."""
    
    # Save user message
    user_msg = ChatMessage(
        user_id=current_user.id,
        session_id=session_id,
        role="user",
        content=message
    )
    db.add(user_msg)
    db.commit()
    
    # Get RAG context and generate response
    context = retrieve_context(message)
    response = generate_response(message, context)
    
    # Save assistant message
    asst_msg = ChatMessage(
        user_id=current_user.id,
        session_id=session_id,
        role="assistant",
        content=response
    )
    db.add(asst_msg)
    db.commit()
    
    return {"response": response}
```

#### Frontend

```typescript
export class ChatComponent {
  constructor(private http: HttpClient) {}
  
  sendMessage(text: string) {
    // Get token from localStorage
    const token = localStorage.getItem('token');
    
    if (!token) {
      // Redirect to login if no token
      this.router.navigate(['/login']);
      return;
    }
    
    // Include token in Authorization header
    const headers = new HttpHeaders({
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    });
    
    this.http.post<any>(
      'http://127.0.0.1:8000/chat/message',
      { message: text, session_id: this.sessionId },
      { headers }
    ).subscribe({
      next: (response) => {
        console.log('Response:', response.response);
      },
      error: (error) => {
        if (error.status === 401) {
          // Token expired or invalid
          localStorage.removeItem('token');
          this.router.navigate(['/login']);
        }
      }
    });
  }
}
```

---

### Pattern 4: Vector Search with RAG

#### Backend Implementation

```python
from langchain_community.embeddings import SentenceTransformerEmbeddings
from rank_bm25 import BM25Okapi
import chromadb

# Initialize embeddings
embeddings = SentenceTransformerEmbeddings(model_name="all-MiniLM-L6-v2")

# Initialize Chroma
chroma_client = chromadb.PersistentClient(path="./chroma_db")
collection = chroma_client.get_or_create_collection(name="cyber_intelligence")

def retrieve_context(query: str, top_k: int = 3) -> List[str]:
    """
    Retrieve relevant documents using vector search.
    
    Process:
    1. Embed the query
    2. Search ChromaDB for similar vectors
    3. Return top-k documents
    """
    
    # 1. Embed query
    query_vector = embeddings.embed_query(query)
    
    # 2. Vector search
    results = collection.query(
        query_embeddings=[query_vector],
        n_results=top_k,
        include=["documents", "metadatas"]
    )
    
    # 3. Extract documents
    documents = results["documents"][0]  # First query's results
    return documents

def generate_response(query: str, context: List[str]) -> str:
    """
    Generate response using context documents.
    
    Process:
    1. Format context into prompt
    2. Send to Ollama
    3. Return generated text
    """
    
    # 1. Format prompt
    context_text = "\n\n".join(context)
    prompt = f"""Based on the following information:

{context_text}

Answer this question: {query}"""
    
    # 2. Call Ollama (local LLM)
    response = ollama.generate(
        model="llama2",
        prompt=prompt,
        stream=False
    )
    
    # 3. Return response
    return response['response']

@app.post("/chat/message")
async def chat(message: str):
    """RAG-powered chat endpoint."""
    
    # 1. Retrieve relevant documents
    context = retrieve_context(message)
    
    # 2. Generate response
    response = generate_response(message, context)
    
    # 3. Return to client
    return {"response": response}
```

---

### Pattern 5: Secure Data Storage

#### Database Model

```python
from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class User(Base):
    """User account model."""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password_hash = Column(String)  # PBKDF2-SHA256 hash, NEVER plaintext
    role = Column(String)  # 'admin' or 'user'
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Never store these:
    # ❌ password (plaintext)
    # ❌ api_key
    # ❌ secret_token
    # Use hashing/encryption for all sensitive data

class ChatMessage(Base):
    """Chat message model."""
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    session_id = Column(String, index=True)
    role = Column(String)  # 'user' or 'assistant'
    content = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Foreign key ensures user_id exists in users table
    # Index on user_id enables fast user-specific queries

class AuditLog(Base):
    """Log important security events (recommended)."""
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    event_type = Column(String)  # 'login', 'logout', 'role_change'
    details = Column(Text)
    ip_address = Column(String)  # Recommended: track IP for security
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
```

---

## Best Practices Checklist

### Authentication
- ✅ Never store plaintext passwords
- ✅ Use PBKDF2, bcrypt, Argon2 (not MD5, SHA1)
- ✅ Hash passwords server-side only
- ✅ Use JWT for stateless auth
- ✅ Implement token expiration (30-60 minutes)
- ✅ Validate tokens on every request
- ✅ Use Bearer token in Authorization header

### Frontend Security
- ✅ Validate all user inputs
- ✅ Implement brute force protection
- ✅ Clear sensitive data on logout
- ✅ Don't log passwords or tokens
- ✅ Use HTTPS only in production
- ✅ Implement CSRF protection (if using cookies)
- ✅ Sanitize HTML output (prevent XSS)

### Backend Security
- ✅ Validate all inputs server-side
- ✅ Use ORM to prevent SQL injection
- ✅ Implement rate limiting
- ✅ Log security events
- ✅ Use environment variables for secrets
- ✅ Don't expose implementation details in errors
- ✅ Implement CORS properly (not "*" in production)

### Database Security
- ✅ Use unique constraints on usernames
- ✅ Use foreign keys for integrity
- ✅ Index frequently searched columns
- ✅ Encrypt sensitive data at rest
- ✅ Use strong database passwords
- ✅ Enable audit logging
- ✅ Regular backups

### Data Protection
- ✅ HTTPS/TLS for all data in transit
- ✅ Encryption for data at rest
- ✅ User isolation by user_id
- ✅ Role-based access control
- ✅ Audit trails for sensitive operations
- ✅ Implement data retention policies
- ✅ GDPR compliance (if applicable)

---

## Testing & Validation

### Unit Test Example

```python
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_login_success():
    """Test successful login."""
    response = client.post(
        "/auth/login",
        json={"username": "testuser", "password": "password123"}
    )
    assert response.status_code == 200
    assert "access_token" in response.json()

def test_login_invalid_credentials():
    """Test login with wrong password."""
    response = client.post(
        "/auth/login",
        json={"username": "testuser", "password": "wrongpassword"}
    )
    assert response.status_code == 401

def test_signup_duplicate_username():
    """Test signup with existing username."""
    # First signup
    client.post(
        "/auth/signup",
        json={"username": "john", "password": "pass123"}
    )
    
    # Duplicate signup
    response = client.post(
        "/auth/signup",
        json={"username": "john", "password": "pass456"}
    )
    assert response.status_code == 400

def test_protected_endpoint_without_token():
    """Test accessing protected endpoint without token."""
    response = client.get("/chat/history?session_id=123")
    assert response.status_code == 401

def test_protected_endpoint_with_invalid_token():
    """Test accessing protected endpoint with invalid token."""
    response = client.get(
        "/chat/history?session_id=123",
        headers={"Authorization": "Bearer invalid_token"}
    )
    assert response.status_code == 401
```

### Manual Testing

```bash
# Test login
curl -X POST http://127.0.0.1:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "password"}'

# Test protected endpoint with token
TOKEN="your_token_from_login"
curl -X GET http://127.0.0.1:8000/chat/history?session_id=123 \
  -H "Authorization: Bearer $TOKEN"

# Test chat message
curl -X POST http://127.0.0.1:8000/chat/message \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "What is a DDoS attack?", "session_id": "123"}'
```

---

## Deployment Checklist

### Before Production

- [ ] Change `SECRET_KEY` in auth_utils.py to random 32+ char string
- [ ] Set `DEBUG = False` in FastAPI
- [ ] Update CORS `allow_origins` to specific domains
- [ ] Set `password_hash_algorithm` to "bcrypt" (if possible)
- [ ] Enable HTTPS/TLS certificates
- [ ] Configure environment variables for secrets
- [ ] Set up database backups
- [ ] Enable audit logging
- [ ] Implement rate limiting on API endpoints
- [ ] Add monitoring and alerting
- [ ] Set up WAF (Web Application Firewall)
- [ ] Conduct security audit

### Production Configuration

```python
# .env file
SECRET_KEY="your-random-secret-key-min-32-chars"
DEBUG=false
ALLOWED_ORIGINS="https://yourdomain.com,https://app.yourdomain.com"
DATABASE_URL="postgresql://user:password@db.example.com/cyberchat"
OLLAMA_URL="http://ollama:11434"
```

```python
# main.py
from dotenv import load_dotenv
import os

load_dotenv()

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ALLOWED_ORIGINS", "").split(","),
    allow_methods=["GET", "POST"],  # Restrict methods
    allow_headers=["Authorization", "Content-Type"],
    allow_credentials=True
)
```

---

## Monitoring & Logging

### Recommended Logging

```python
import logging
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

@app.post("/auth/login")
async def login(request: LoginRequest):
    logger.info(f"Login attempt: {request.username}")
    
    try:
        # ... authentication logic
        logger.info(f"Successful login: {request.username}")
        return token
    except Exception as e:
        logger.warning(f"Failed login: {request.username} - {str(e)}")
        raise HTTPException(status_code=401, detail="Invalid credentials")
```

### Metrics to Monitor

```
- Authentication success rate
- Authentication failure rate
- Average response time
- Vector search latency
- Chat response generation time
- Database query performance
- Memory usage
- Disk usage
- Error rates
```

---

## Troubleshooting Guide

### Issue: "Invalid token" error
**Cause:** Token expired or corrupted  
**Solution:**
```typescript
// Clear token and redirect to login
localStorage.removeItem('token');
this.router.navigate(['/login']);
```

### Issue: "SQL injection" warning
**Cause:** Not using ORM properly  
**Solution:**
```python
# ❌ Wrong
query = f"SELECT * FROM users WHERE username = '{username}'"

# ✅ Correct
user = db.query(User).filter(User.username == username).first()
```

### Issue: Slow vector search
**Cause:** Too many documents or large chunks  
**Solution:**
```python
# Reduce chunk size
splitter = RecursiveCharacterTextSplitter(chunk_size=200, chunk_overlap=30)

# Add metadata filtering
results = collection.query(
    query_embeddings=[vector],
    where={"source": "CISA"},  # Filter by source
    n_results=3
)
```

### Issue: Out of memory
**Cause:** Loading entire documents into memory  
**Solution:**
```python
# Process in batches
batch_size = 10
for i in range(0, len(documents), batch_size):
    batch = documents[i:i+batch_size]
    # Process batch
```

---

## Additional Resources

### Security
- OWASP Top 10: https://owasp.org/www-project-top-ten/
- JWT Best Practices: https://tools.ietf.org/html/rfc8949
- PBKDF2: https://tools.ietf.org/html/rfc2898

### Technologies
- FastAPI: https://fastapi.tiangolo.com/
- SQLAlchemy: https://docs.sqlalchemy.org/
- Chroma: https://docs.trychroma.com/
- Ollama: https://ollama.ai/

### Testing
- Pytest: https://docs.pytest.org/
- curl: https://curl.se/

---

**Last Updated:** April 22, 2026  
**Status:** Production-Ready
