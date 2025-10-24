import logging
from datetime import datetime
from pathlib import Path
from string import Template
from urllib.parse import quote

from fastapi import Depends, FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from sqlmodel import SQLModel, Session, create_engine, select
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.cleaner import start_cleaner
from app.config import (
    CACHE_MAX_AGE_SECONDS,
    DB_CONNECT_ARGS,
    DB_URL,
    ENABLE_CLEANER,
    MAX_FILE_SIZE,
    RATE_LIMIT_PER_MINUTE,
    UPLOAD_DIR,
    CORS_ORIGINS,
)
from app.metrics import metrics
from app.models import File as FileModel
from app.rate_limit import RateLimiter
from app.storage import save_file

app = FastAPI(title="AlterBase CDN API", version="1.0")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("image_uploader")

rate_limiter = RateLimiter(RATE_LIMIT_PER_MINUTE)
MAX_FILE_SIZE_MB = MAX_FILE_SIZE / (1024 * 1024)
TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"


def render_template(filename: str, context: dict[str, str | int | float]) -> str:
    path = TEMPLATE_DIR / filename
    if not path.is_file():
        return "<h1>Template missing</h1>"
    content = path.read_text(encoding="utf-8")
    template = Template(content)
    return template.safe_substitute(context)

# CORS
origins = [o.strip() for o in CORS_ORIGINS.split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

engine = create_engine(DB_URL, connect_args=DB_CONNECT_ARGS)
SQLModel.metadata.create_all(engine)
if ENABLE_CLEANER:
    start_cleaner(engine, metrics, logger)  # background scheduler


async def enforce_rate_limit(request: Request):
    client = request.client.host if request.client else "unknown"
    allowed, retry_after = rate_limiter.hit(client)
    if not allowed:
        headers = {"Retry-After": str(retry_after)}
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Try again in {retry_after} seconds.",
            headers=headers,
        )


@app.exception_handler(404)
async def not_found_handler(request: Request, exc: StarletteHTTPException):
    accept = request.headers.get("accept", "")
    detail = exc.detail if hasattr(exc, "detail") else "Not Found"
    if "application/json" in accept and "text/html" not in accept:
        return JSONResponse({"detail": detail}, status_code=404)
    detail_text = (
        detail
        if detail not in (None, "", "Not found", "Not Found")
        else "The resource you were looking for isn't here. It may have been removed or its link is outdated."
    )
    html = render_template("404.html", {"detail": detail_text})
    return HTMLResponse(content=html, status_code=404)

# --- Pages ---

@app.get("/", response_class=HTMLResponse)
async def home():
    stats = metrics.snapshot()
    html = render_template(
        "index.html",
        {
            "max_file_mb": f"{MAX_FILE_SIZE_MB:.1f}",
            "uploads": str(stats.get("uploads", 0)),
            "downloads": str(stats.get("downloads", 0)),
            "deleted": str(stats.get("deleted", 0)),
            "year": str(datetime.utcnow().year),
        },
    )
    return HTMLResponse(content=html)


@app.get("/api-info", response_class=HTMLResponse)
async def api_info():
    html = render_template(
        "api.html",
        {"max_file_mb": f"{MAX_FILE_SIZE_MB:.1f}", "rate_limit": str(RATE_LIMIT_PER_MINUTE)},
    )
    return HTMLResponse(content=html)


@app.get("/metrics", dependencies=[Depends(enforce_rate_limit)])
def metrics_snapshot():
    data = metrics.snapshot()
    response = JSONResponse(data)
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
    return response

# --- Routes ---

@app.post("/upload", dependencies=[Depends(enforce_rate_limit)])
async def upload(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing filename")
    data = await file.read()
    size_bytes = len(data)
    if size_bytes > MAX_FILE_SIZE:
        logger.warning(
            "event=upload_rejected reason=max_size filename=%s size_bytes=%s limit_bytes=%s",
            file.filename,
            size_bytes,
            MAX_FILE_SIZE,
        )
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum allowed size is {MAX_FILE_SIZE_MB:.1f} MB.",
        )
    stored_name, size_bytes = save_file(data, file.filename, file.content_type or "application/octet-stream")
    file_id = stored_name.split(".")[0]

    with Session(engine) as session:
        rec = FileModel(
            id=file_id,
            original_name=file.filename,
            stored_name=stored_name,
            content_type=file.content_type or "application/octet-stream",
            size_bytes=size_bytes,
        )
        session.add(rec)
        session.commit()

    metrics.record_upload(size_bytes)
    logger.info(
        "event=upload_success file_id=%s stored_name=%s size_bytes=%s content_type=%s",
        file_id,
        stored_name,
        size_bytes,
        file.content_type or "application/octet-stream",
    )

    return {
        "id": file_id,
        "url": f"/{quote(stored_name)}",
        "size": size_bytes,
        "type": file.content_type,
    }

@app.get("/list", dependencies=[Depends(enforce_rate_limit)])
def list_files():
    with Session(engine) as session:
        files = session.exec(select(FileModel).order_by(FileModel.created_at.desc())).all()
        return [
            {
                "id": f.id,
                "url": f"/{quote(f.stored_name)}",
                "name": f.original_name,
                "size": f.size_bytes,
                "created_at": f.created_at,
            } for f in files
        ]

@app.get("/{filename}", dependencies=[Depends(enforce_rate_limit)])
def serve_file(filename: str):
    upload_root = Path(UPLOAD_DIR).resolve()
    try:
        path = (upload_root / filename).resolve()
        path.relative_to(upload_root)
    except (ValueError, RuntimeError):
        raise HTTPException(status_code=404, detail="Not found")
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Not found")
    metrics.record_download()
    logger.info("event=file_served filename=%s path=%s", filename, path)
    response = FileResponse(path)
    response.headers["Cache-Control"] = f"public, max-age={CACHE_MAX_AGE_SECONDS}"
    return response
