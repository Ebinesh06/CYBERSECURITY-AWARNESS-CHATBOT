# Setup Guide

## Clone Repository

```bash
git clone <repository_url>
```

---

# Backend

Create virtual environment

```bash
python -m venv venv
```

Activate

Windows

```bash
venv\Scripts\activate
```

Install dependencies

```bash
pip install -r requirements.txt
```

Create vector database

```bash
python ingest_intelligence.py
```

Run backend

```bash
uvicorn main:app --reload
```

---

# Ollama

Install Ollama

Download Llama 3

```bash
ollama pull llama3
```

Verify

```bash
ollama list
```

---

# Frontend

```bash
npm install
```

Run

```bash
npm run dev
```

---

# Troubleshooting

## NumPy Import Error

Delete venv

Recreate it

Install requirements again.

---

## SSL Certificate Error

```bash
pip install python-certifi-win32
```

---

## Missing Package

```bash
pip install langchain-text-splitters
```

---

## ChromaDB

Delete

```
Backend/chroma_db
```

Run

```bash
python ingest_intelligence.py
```