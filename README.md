# 🛡️ CyberSecurity Awareness Chatbot

An AI-powered cybersecurity awareness chatbot that uses Retrieval-Augmented Generation (RAG) to answer cybersecurity-related questions accurately using a local knowledge base and live vulnerability intelligence.

---

## Features

- 🔐 JWT Authentication
- 👤 User Registration & Login
- 💬 Conversation History
- 🧠 Retrieval-Augmented Generation (RAG)
- 📚 Local Cybersecurity Knowledge Base
- 🌐 Live CISA Known Exploited Vulnerabilities Feed
- 🔍 Hybrid Retrieval
  - ChromaDB (Semantic Search)
  - BM25 (Keyword Search)
  - Reciprocal Rank Fusion (RRF)
  - FlashRank Re-ranking
- 🤖 Local Llama 3 inference using Ollama
- ⚡ Streaming AI Responses
- 🗄 SQLite Database

---

## Tech Stack

### Frontend
- React
- Axios
- React Router

### Backend
- FastAPI
- SQLAlchemy
- JWT Authentication

### AI
- Ollama
- Llama 3
- ChromaDB
- Sentence Transformers
- FlashRank
- BM25

---

## Architecture

User

↓

React Frontend

↓

FastAPI Backend

↓

Authentication

↓

Hybrid Retrieval

↓

ChromaDB + BM25

↓

FlashRank

↓

Llama 3 (Ollama)

↓

Response

---

## Installation

See SETUP.md

---

## Future Improvements

- PDF Upload
- URL Ingestion
- Voice Assistant
- Threat Severity Classification
- Admin Dashboard
- Docker Deployment

---

## License

MIT