from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from sqlmodel import Session, select

from app.config import CACHE_MAX_AGE_SECONDS, MAX_FILE_SIZE, RATE_LIMIT_PER_MINUTE, UPLOAD_DIR
from app.core.metrics import metrics
from app.core.rate_limit import RateLimiter
from app.core.templates import render_template
from app.db import get_session
from app.models import File as FileModel
from app.services.stats import fetch_storage_totals
from app.storage import save_file

router = APIRouter()

logger = logging.getLogger("image_uploader")

rate_limiter = RateLimiter(RATE_LIMIT_PER_MINUTE)
MAX_FILE_SIZE_MB = MAX_FILE_SIZE / (1024 * 1024)
UPLOAD_ROOT = Path(UPLOAD_DIR).resolve()


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


@router.get("/", response_class=HTMLResponse)
async def home(session: Session = Depends(get_session)):
    stats = metrics.snapshot()
    totals = fetch_storage_totals(session)
    uploads_count = max(int(stats.get("uploads", 0)), totals["total_files"])

    html = render_template(
        "pages/home.html",
        {
            "max_file_mb": f"{MAX_FILE_SIZE_MB:.1f}",
            "uploads": str(uploads_count),
            "downloads": str(stats.get("downloads", 0)),
            "deleted": str(stats.get("deleted", 0)),
            "storage_bytes": str(totals["total_bytes"]),
            "year": str(datetime.utcnow().year),
        },
    )
    return HTMLResponse(content=html)


@router.get("/api-info", response_class=HTMLResponse)
async def api_info():
    html = render_template(
        "pages/api.html",
        {"max_file_mb": f"{MAX_FILE_SIZE_MB:.1f}", "rate_limit": str(RATE_LIMIT_PER_MINUTE)},
    )
    return HTMLResponse(content=html)


@router.get("/list", dependencies=[Depends(enforce_rate_limit)])
def list_files(session: Session = Depends(get_session)):
    files = session.exec(select(FileModel).order_by(FileModel.created_at.desc())).all()
    return [
        {
            "id": f.id,
            "url": f"/{quote(f.stored_name)}",
            "name": f.original_name,
            "size": f.size_bytes,
            "created_at": f.created_at,
        }
        for f in files
    ]


@router.post("/upload", dependencies=[Depends(enforce_rate_limit)])
async def upload(file: UploadFile = File(...), session: Session = Depends(get_session)):
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

    record = FileModel(
        id=file_id,
        original_name=file.filename,
        stored_name=stored_name,
        content_type=file.content_type or "application/octet-stream",
        size_bytes=size_bytes,
    )
    session.add(record)
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


@router.get("/metrics", dependencies=[Depends(enforce_rate_limit)])
def metrics_snapshot(session: Session = Depends(get_session)):
    stats = metrics.snapshot()
    totals = fetch_storage_totals(session)
    payload = {
        "uploads": max(int(stats.get("uploads", 0)), totals["total_files"]),
        "downloads": int(stats.get("downloads", 0)),
        "deleted": int(stats.get("deleted", 0)),
        "storage_bytes": totals["total_bytes"],
    }
    response = JSONResponse(payload)
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
    return response


@router.get("/{filename}", dependencies=[Depends(enforce_rate_limit)])
def serve_file(filename: str):
    try:
        path = (UPLOAD_ROOT / filename).resolve()
        path.relative_to(UPLOAD_ROOT)
    except (ValueError, RuntimeError):
        raise HTTPException(status_code=404, detail="Not found")
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Not found")

    metrics.record_download()
    logger.info("event=file_served filename=%s path=%s", filename, path)

    response = FileResponse(path)
    response.headers["Cache-Control"] = f"public, max-age={CACHE_MAX_AGE_SECONDS}"
    return response
