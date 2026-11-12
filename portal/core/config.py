import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Load .env if present
env_path = BASE_DIR / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)

# Default to the user's PostgreSQL credentials, fallback to SQLite if needed
DEFAULT_PG_URL = "postgresql://postgres:tushar%407744@localhost:5432/collegepur_db"
DEFAULT_SQLITE_URL = f"sqlite:///{BASE_DIR / 'data' / 'exam_engine.db'}"

DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_PG_URL)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai/")
