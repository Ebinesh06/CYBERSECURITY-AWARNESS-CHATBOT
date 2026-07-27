"""Central configuration for backend storage and model integrations."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CHROMA_PATH = PROJECT_ROOT / "chroma_db"
MODEL_PATH = PROJECT_ROOT / "models"
MODEL_NAME = "all-MiniLM-L6-v2"
FLASHRANK_MODEL = "ms-marco-TinyBERT-L-2-v2"
GEMINI_MODEL = "gemini-3.5-flash"