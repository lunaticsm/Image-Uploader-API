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
MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE_BYTES", str(10 * 1024 * 1024)))
RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))
CACHE_MAX_AGE_SECONDS = int(os.getenv("CACHE_MAX_AGE_SECONDS", "3600"))
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin-dev-password")
ADMIN_LOCK_STEP_SECONDS = int(os.getenv("ADMIN_LOCK_STEP_SECONDS", str(5 * 60)))
FILE_ID_LENGTH = max(4, min(32, int(os.getenv("FILE_ID_LENGTH", "7"))))
