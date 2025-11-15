import logging

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.api.routes import router
from app.cleaner import start_cleaner
from app.config import CORS_ORIGINS, ENABLE_CLEANER, MEGA_BACKUP_ENABLED
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

if MEGA_BACKUP_ENABLED:
    from app.storage import initialize_backup_service

    try:
        initialize_backup_service()
        logger.info("MEGA backup service initialized successfully.")
    except Exception as exc:
        logger.error("Failed to initialize MEGA backup service: %s", exc)
        raise

static_dir = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Frontend (React SPA)
FRONTEND_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if FRONTEND_DIST.exists():
    logger.info("Serving React frontend from %s", FRONTEND_DIST)
    app.mount("/frontend", StaticFiles(directory=FRONTEND_DIST), name="frontend")

    def _spa_response() -> FileResponse:
        index_path = FRONTEND_DIST / "index.html"
        if not index_path.exists():
            logger.error("Frontend index missing at %s", index_path)
            raise HTTPException(status_code=404, detail="Frontend build missing index.html")
        return FileResponse(index_path)

    @app.get("/app", include_in_schema=False)
    async def serve_spa_root():
        return _spa_response()

    @app.get("/app/{path:path}", include_in_schema=False)
    async def serve_spa_paths(path: str):  # noqa: ARG001
        return _spa_response()
else:
    logger.info("Frontend build not found at %s. Serving API endpoints only.", FRONTEND_DIST)

app.include_router(router)
register_exception_handlers(app)

if ENABLE_CLEANER:
    start_cleaner(engine, metrics, logger)
