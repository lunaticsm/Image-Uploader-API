import os
from dotenv import load_dotenv

load_dotenv()

UPLOAD_DIR = os.getenv(
    "UPLOAD_DIR", os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "uploads"))
)
DB_URL = os.getenv("DB_URL", "sqlite:///./cdn.db")
DELETE_AFTER_HOURS = int(os.getenv("DELETE_AFTER_HOURS", "72"))
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*")

DB_CONNECT_ARGS = {"check_same_thread": False} if DB_URL.startswith("sqlite") else {}
ENABLE_CLEANER = os.getenv("ENABLE_CLEANER", "true").lower() in {"true", "1", "yes"}
