import logging

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routes import router
from app.cleaner import start_cleaner
from app.config import CORS_ORIGINS, ENABLE_CLEANER
from app.core.exceptions import register_exception_handlers
from app.core.metrics import metrics
from app.db import engine, init_db

app = FastAPI(title="AlterBase CDN API", version="3.5.0")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("image_uploader")

origins = [origin.strip() for origin in CORS_ORIGINS.split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

init_db()
app.include_router(router)
register_exception_handlers(app)

if ENABLE_CLEANER:
    start_cleaner(engine, metrics, logger)

static_dir = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=static_dir), name="static")
