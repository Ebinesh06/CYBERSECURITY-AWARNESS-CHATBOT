# CyberSecurity Chatbot - Technical Glossary

**Complete terminology and technical concepts explained in simple terms**

---

## Table of Contents

1. [Authentication & Security](#authentication--security)
2. [Cryptography](#cryptography)
3. [Database & ORM](#database--orm)
4. [Vector Databases & Embeddings](#vector-databases--embeddings)
5. [Machine Learning](#machine-learning)
6. [API & Web Technologies](#api--web-technologies)
7. [Threat Intelligence](#threat-intelligence)

---

## Authentication & Security

### JWT (JSON Web Token)
**What it is:** A standardized format for securely transmitting information between parties as a JSON object.

**Structure:**
```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c2VyMTIzIiwiZXhwIjoxNzEzNzk0NDAwfQ.signature...
```
Consists of 3 parts separated by dots:
1. **Header:** Algorithm (HS256) and token type
2. **Payload:** User claims (username, expiration, etc.)
3. **Signature:** Cryptographic hash to verify authenticity

**Why use JWT?**
- Stateless (no server session storage needed)
- Self-contained (all info in token)
- Verifiable (cryptographically signed)
- Scalable (works across multiple servers)

**In our system:** Token expires after 30 minutes, forcing re-authentication for security.

---

### Bearer Token
**What it is:** A token included in the HTTP Authorization header.

**Format:**
```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**How it works:**
1. Client receives JWT token on login
2. Client includes token in every API request
3. Server validates token signature
4. Server checks expiration time
5. Server extracts user information from token

**Benefits:**
- ✅ Stateless authentication
- ✅ Simple implementation
- ✅ Works with REST APIs
- ✅ Can be stored in localStorage or cookies

---

### PBKDF2-SHA256
**What it is:** Password-Based Key Derivation Function 2 with SHA-256 hashing.

**How it works:**
```
Raw Password
  ↓
1. Add random salt
2. Apply SHA256 hash function
3. Repeat 29,000+ times (adaptive)
4. Generate final hash
  ↓
Stored Hash (looks like: $pbkdf2$sha256$29000$salt$hash)
```

**Why so many iterations?**
- Each iteration takes computational time
- Makes brute force attacks slow
- Iterations increase as computers get faster
- 29,000 iterations ≈ 100ms per hash attempt
- To crack 1 password takes 100ms × 10^9 possibilities = 3+ years!

**Comparison:**
| Method | Speed | Security | Notes |
|--------|-------|----------|-------|
| Plain text | ✅✅✅ | ❌ | Never use |
| MD5/SHA1 | ✅✅ | ❌ | Outdated |
| bcrypt | ✅ | ✅✅✅ | Best (slower) |
| PBKDF2 | ✅ | ✅✅ | Good (faster) |
| Argon2 | ❌ | ✅✅✅ | Best (slowest) |

---

### Brute Force Attack
**What it is:** Trying many password combinations to guess credentials.

**Example:**
```
Try: password1 → Fail
Try: password2 → Fail
Try: password3 → Fail
...
Try: correct_password → Success (after 10^9 attempts)
```

**Protection in our system:**
- ✅ Max 5 failed attempts
- ✅ 30-second lockout period
- ✅ No rate limiting required (frontend handles this)
- ✅ Lockout survives page refresh (sessionStorage)

**Why this works:**
- Attacker can only try 5 passwords every 30 seconds
- 5 attempts/30 seconds = 1 attempt every 6 seconds
- To try 10^9 passwords = 6 seconds × 10^9 = 1,900+ years!

---

### CORS (Cross-Origin Resource Sharing)
**What it is:** Mechanism allowing requests from one domain to access resources on another domain.

**Current Configuration:**
```python
allow_origins=["*"]        # Allow all origins
allow_methods=["*"]        # Allow all HTTP methods
allow_headers=["*"]        # Allow all headers
```

**Security Issue:**
- `allow_origins=["*"]` is okay for development
- ❌ UNSAFE for production!

**Production Configuration:**
```python
allow_origins=[
    "https://yourdomain.com",
    "https://app.yourdomain.com"
]
```

---

## Cryptography

### HMAC (Hash-Based Message Authentication Code)
**What it is:** A method to verify both the integrity and authenticity of a message.

**How it works:**
```
Message + Secret Key
  ↓
HMAC(message, secret_key)
  ↓
Hash that proves only someone with the secret key could create it
```

**In JWT:**
```
SIGNATURE = HMAC-SHA256(
  base64(header) + "." + base64(payload),
  SECRET_KEY
)
```

**Why it matters:**
- Proves the token hasn't been tampered with
- Only server knows SECRET_KEY
- If someone modifies the token, signature won't match
- Server rejects tampered tokens

---

### Encryption vs. Hashing

| Property | Encryption | Hashing |
|----------|-----------|---------|
| **Purpose** | Confidentiality | Integrity |
| **Reversible?** | ✅ Yes (with key) | ❌ No |
| **Use Case** | Secrets | Passwords |
| **Example** | AES-256 | PBKDF2 |

**In our system:**
- ✅ Passwords: Hashed (one-way)
- ✅ Tokens: Signed HMAC (not encrypted)
- ❌ No encryption at rest (SQLite stores plaintext data)

**Recommendation for production:**
- ✅ Use encryption for sensitive fields
- ✅ Use HTTPS/TLS for data in transit
- ✅ Use key management service (AWS KMS, etc.)

---

## Database & ORM

### SQLAlchemy ORM
**What it is:** Object-Relational Mapping library for Python.

**Concept:**
```
Database Table          Python Class
┌─────────────┐        ┌──────────────┐
│ users       │   ←→   │ class User   │
│ id, name    │        │ id, name     │
└─────────────┘        └──────────────┘
```

**Example:**
```python
# SQL Way (dangerous - SQL injection risk)
query = "SELECT * FROM users WHERE username = '" + username + "'"

# SQLAlchemy Way (safe - parameterized)
user = db.query(User).filter(User.username == username).first()
```

**Benefits:**
- ✅ Prevents SQL injection
- ✅ Database agnostic (can switch SQLite → PostgreSQL)
- ✅ Cleaner Python syntax
- ✅ Automatic query optimization

---

### SQL Injection
**What it is:** Attack by injecting SQL code through user input.

**Vulnerable Example:**
```python
# ❌ DANGEROUS
username = "admin' OR '1'='1"
query = "SELECT * FROM users WHERE username = '" + username + "'"
# Results in: WHERE username = 'admin' OR '1'='1'
# This always returns true!
```

**Safe Example:**
```python
# ✅ SAFE
user = db.query(User).filter(User.username == username).first()
# SQLAlchemy parametrizes: WHERE username = ?
# Input is treated as data, not code
```

**In our system:**
- ✅ Using SQLAlchemy (protected)
- ✅ Never concatenate SQL strings
- ✅ Always use ORM queries

---

### Foreign Key
**What it is:** A reference from one table to another.

**In our system:**
```
ChatMessage.user_id → User.id

┌──────────────────────────────┐
│ users                        │
│ id (primary key)             │
│ username                     │
└──────────────────────────────┘
          ▲
          │ (one-to-many)
          │
┌──────────────────────────────┐
│ messages                     │
│ id (primary key)             │
│ user_id (foreign key)────────┘
│ content                      │
└──────────────────────────────┘
```

**Benefits:**
- ✅ Data integrity (can't have orphaned messages)
- ✅ User isolation (message belongs to specific user)
- ✅ Query efficiency (can fetch all messages for a user)

---

### Index
**What it is:** Data structure for fast lookups (like a book's index).

**In our system:**
```python
username = Column(String, unique=True, index=True)
# Creates index on username for fast lookups
```

**Without index:**
```
SELECT * FROM users WHERE username = 'john'
→ Scans entire table (slow)
```

**With index:**
```
SELECT * FROM users WHERE username = 'john'
→ Uses B-tree to find directly (fast)
```

**Trade-off:**
- ✅ Faster reads
- ❌ Slower writes (must update index)
- ❌ More storage (duplicate data in index)

---

## Vector Databases & Embeddings

### Embedding
**What it is:** Converting text into numerical representation (vector).

**Example:**
```
Text: "DDoS attack"
         ↓
Embedding: [0.234, -0.891, 0.456, 0.123, ..., 0.789]
          (384 dimensions in our case)
```

**How it captures meaning:**
- Similar words → Similar vectors
- Opposite words → Opposite vectors
- "attack" and "assault" → Similar embeddings
- "attack" and "peaceful" → Different embeddings

**Model we use:** all-MiniLM-L6-v2
- Size: ~22 MB (lightweight)
- Dimensions: 384
- Speed: Fast inference
- Quality: High semantic similarity

---

### Vector Database (Chroma)
**What it is:** Database optimized for storing and searching vectors.

**Traditional Database:**
```
Query: username = "john"
→ B-tree lookup → O(log n)
```

**Vector Database:**
```
Query: vector similar to [0.234, -0.891, ...]
→ Calculate cosine similarity to all vectors
→ Return top N most similar
```

**Data Structure:** Uses HNSW (Hierarchical Navigable Small World) graph for fast nearest-neighbor search.

---

### Semantic Search
**What it is:** Finding documents by meaning, not just keywords.

**Keyword Search:**
```
Query: "zero day vulnerability"
Finds: Documents containing exact phrase
```

**Semantic Search:**
```
Query: "zero day vulnerability"
Finds: Documents about new exploits, unknown threats, etc.
→ Understands meaning, not just keywords
```

**Cosine Similarity (how we measure similarity):**
```
Vector A: [0.2, 0.5, 0.3]
Vector B: [0.3, 0.4, 0.2]

Similarity = dot_product(A, B) / (|A| × |B|)
           = (0.2×0.3 + 0.5×0.4 + 0.3×0.2) / (norm_a × norm_b)
           ≈ 0.91 (on scale 0-1)

0.9+ = Very similar
0.5-0.9 = Somewhat similar
< 0.5 = Different
```

---

### Chunk
**What it is:** Breaking large documents into smaller pieces.

**Why chunk?**
```
Document: 10,000 characters
Embed entire document?
→ Information becomes diluted
→ Embedding loses specificity

Chunk into: 300-character pieces
→ Each chunk has clear topic
→ Better semantic clarity
→ Faster search
```

**Chunking Strategy:**
```
Original: "Introduction... [1000 chars] ...Conclusion..."
           ↓
Chunk 1: [chars 0-300]
Chunk 2: [chars 250-550]      (50-char overlap)
Chunk 3: [chars 500-800]      (50-char overlap)

Overlap prevents:
✅ Information loss at boundaries
✅ Broken sentences
✅ Missing context
```

---

## Machine Learning

### RAG (Retrieval-Augmented Generation)
**What it is:** Technique combining document search with LLM generation.

**Traditional LLM:**
```
Query: "What is a zero-day?"
→ LLM generates from training data
→ May hallucinate (make up false info)
```

**RAG (Our System):**
```
Query: "What is a zero-day?"
  ↓
[1] RETRIEVE: Search knowledge base
    → Find 3 relevant documents
  ↓
[2] AUGMENT: Format as context
    → "Based on [doc1, doc2, doc3]..."
  ↓
[3] GENERATE: Use LLM to answer
    → Grounded in actual documents
    → Less hallucination
    → Can cite sources
```

**Benefits:**
- ✅ Factually accurate (grounded in documents)
- ✅ Up-to-date (can use live data)
- ✅ Traceable (can point to sources)
- ✅ Domain-specific (uses your knowledge base)

---

### Ollama
**What it is:** Framework for running LLMs locally.

**Why local LLM?**
- ✅ Privacy (data doesn't go to cloud)
- ✅ No API costs
- ✅ No rate limiting
- ✅ Offline capability
- ❌ Slower (CPU/GPU inference)
- ❌ Hardware requirement (4GB+ RAM)

**Model we use:** Llama 2
- Size: 7B parameters (lightweight)
- Speed: ~10 tokens/second
- Quality: Good for domain tasks
- Free and open source

---

### BM25 (Okapi BM25)
**What it is:** Algorithm for keyword-based document ranking.

**How it works:**
```
Query: "DDoS attack prevention"

Score = IDF(term) × (tf × (k₁ + 1)) / (tf + k₁(1 - b + b × doclen/avglen))

Where:
IDF = Inverse Document Frequency (rarity of term)
tf = Term frequency (how often term appears)
doclen = Document length
```

**Simple explanation:**
- Scores based on keyword presence
- Rare keywords weighted higher
- Longer documents penalized
- Good for exact matches

**Use Case:** Find documents with specific keywords.

---

### Ranking
**What it is:** Ordering documents by relevance.

**Our Hybrid Approach:**
```
1. Get results from Vector Search
2. Get results from BM25 Search
3. Merge results
4. Re-rank using neural model (TinyBERT)
5. Return top results
```

**Why hybrid?**
- Vector search: Good at semantic meaning
- BM25: Good at keyword matching
- Together: Best of both worlds

**Re-ranking Model (TinyBERT):**
- Small, fast neural model
- Trained on relevance judgment
- Fine-tunes merged results
- Improves final ranking quality

---

## API & Web Technologies

### REST (Representational State Transfer)
**What it is:** Standard way to design web APIs.

**Principles:**
```
GET    /users          → Retrieve all users
GET    /users/123      → Retrieve user 123
POST   /users          → Create new user
PUT    /users/123      → Update user 123
DELETE /users/123      → Delete user 123
```

**In our system:**
```
POST /auth/login                 → User login
POST /auth/signup                → User registration
POST /chat/message               → Send chat message
GET  /chat/history?session_id=X  → Get chat history
```

---

### HTTP Status Codes
**What they mean:**

| Code | Meaning | Example |
|------|---------|---------|
| 200 | ✅ OK | Successful request |
| 201 | ✅ Created | Resource created |
| 400 | ❌ Bad Request | Invalid input |
| 401 | ❌ Unauthorized | Not authenticated |
| 403 | ❌ Forbidden | No permission |
| 404 | ❌ Not Found | Resource doesn't exist |
| 500 | ❌ Server Error | Backend crashed |

**In our system:**
```python
raise HTTPException(status_code=401, detail="Invalid token")
raise HTTPException(status_code=403, detail="Admin access required")
```

---

### Streaming Response
**What it is:** Sending response in chunks instead of all at once.

**Use case:** Chat responses character by character.

```
User: "What is DDoS?"
  ↓
[Chunk 1]: "A "
[Chunk 2]: "DDoS "
[Chunk 3]: "is "
[Chunk 4]: "a distributed "
...
```

**Benefits:**
- ✅ Faster perceived response time
- ✅ Lower memory usage
- ✅ Better UX (see response appearing)
- ❌ Can't check full response for errors

---

## Threat Intelligence

### CVE (Common Vulnerabilities and Exposures)
**What it is:** Unique identifier for known vulnerabilities.

**Format:**
```
CVE-YYYY-NNNNN

Example: CVE-2024-1234
YYYY = Year discovered (2024)
NNNNN = Sequential number (1234)
```

**CISA KEV Database:**
- Contains "Known Exploited Vulnerabilities"
- Only vulnerabilities actively being exploited
- Prioritized by threat level
- Updated daily
- Used in our system for threat intelligence

---

### DDoS (Distributed Denial of Service)
**What it is:** Attack overwhelming server with traffic.

**Types:**
- **Layer 3/4:** Volumetric attacks (UDP floods, DNS amplification)
- **Layer 7:** Application attacks (HTTP floods, slowloris)

**Protection:**
- Rate limiting
- WAF (Web Application Firewall)
- DDoS mitigation services
- Geo-blocking

---

### Malware
**What it is:** Software designed to harm systems.

**Types:**
- **Virus:** Self-replicating, requires host
- **Worm:** Self-replicating, spreads on its own
- **Trojan:** Disguised as legitimate software
- **Ransomware:** Encrypts data, demands payment
- **Spyware:** Steals information

**Detection:**
- Signature-based (known malware hashes)
- Behavior-based (suspicious activity)
- Sandboxing (isolated execution)
- ML-based (anomaly detection)

---

### Phishing
**What it is:** Social engineering attack via fake communications.

**Types:**
- **Email phishing:** Fake emails with malicious links
- **Spear phishing:** Targeted attacks with personalization
- **Whaling:** Targets high-value individuals
- **SMS phishing (Smishing):** Fake text messages
- **Voice phishing (Vishing):** Fake phone calls

**Prevention:**
- User training
- Email filtering
- Multi-factor authentication
- Domain verification (SPF, DKIM, DMARC)

---

### Zero-Day
**What it is:** Vulnerability unknown to vendors.

**Terminology:**
- **Day 0:** Vulnerability discovered
- **Day 1+:** Vendor knows, working on patch
- **Patch Day:** Fix released

**Risk:**
- ✅ No patch available initially
- ✅ Attackers have advantage
- ✅ Higher impact if exploited widely

**Mitigation:**
- Defense-in-depth (don't rely on patches)
- Monitor for suspicious activity
- Limit privilege
- Network segmentation

---

## Glossary Quick Reference

| Term | Definition | Example |
|------|-----------|---------|
| **JWT** | Secure token for authentication | `eyJhbGciOiJIUzI1NiI...` |
| **Bearer** | Token format in Authorization header | `Authorization: Bearer <token>` |
| **Hashing** | One-way function to obscure data | PBKDF2, SHA256 |
| **Encryption** | Reversible function to protect data | AES-256 |
| **ORM** | Object mapping to database | SQLAlchemy |
| **Embedding** | Text as vector | 384-dimensional vector |
| **Chunk** | Document fragment | 300 characters with overlap |
| **RAG** | Retrieval + generation | Search + LLM |
| **BM25** | Keyword ranking algorithm | Document relevance |
| **REST** | API design pattern | GET/POST/PUT/DELETE |
| **CVE** | Vulnerability identifier | CVE-2024-1234 |

---

**Document Last Updated:** April 22, 2026  
**Glossary Version:** 1.0
