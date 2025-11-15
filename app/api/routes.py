from __future__ import annotations

import logging
import html
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import quote
import json

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
from sqlmodel import Session, select

from app.config import (
    ADMIN_LOCK_STEP_SECONDS,
    ADMIN_PASSWORD,
    API_KEY,
    CACHE_MAX_AGE_SECONDS,
    MAX_FILE_SIZE,
    RATE_LIMIT_PER_MINUTE,
    UPLOAD_DIR,
    MEGA_BACKUP_ENABLED,
    REDIS_URL,
)
from app.core.metrics import metrics
from app.core.rate_limit import RateLimiter
from app.core.templates import render_template
from app.db import get_session, session_scope
from app.models import File as FileModel
from app.services.stats import fetch_storage_totals
from app.storage import save_file, backup_and_mark

router = APIRouter()

logger = logging.getLogger("image_uploader")

rate_limiter = RateLimiter(RATE_LIMIT_PER_MINUTE)
MAX_FILE_SIZE_MB = MAX_FILE_SIZE / (1024 * 1024)
UPLOAD_ROOT = Path(UPLOAD_DIR).resolve()
FRONTEND_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist" / "index.html"
FRONTEND_PRESENT = FRONTEND_DIST.exists()
# Admin attempts will be stored in Redis when available, fallback to in-memory
# We'll implement Redis-based storage for admin attempts


def handle_backup_after_upload(file_id: str, stored_name: str):
    """Handle file backup to MEGA after upload"""
    if MEGA_BACKUP_ENABLED:
        # In production, you might want to run this in a background task.
        # For now, we'll run it synchronously.
        from app.storage import backup_and_mark
        from app.db import session_scope

        with session_scope() as session:
            backup_and_mark(session, file_id)


def backup_to_mega_in_background(file_id: str):
    """Background task function to handle MEGA backup"""
    if MEGA_BACKUP_ENABLED:
        from app.storage import backup_and_mark
        from app.db import session_scope

        logger.info(f"Starting background MEGA backup for file {file_id}")
        try:
            with session_scope() as session:
                backup_and_mark(session, file_id)
            logger.info(f"Successfully backed up file {file_id} to MEGA")
        except Exception as e:
            logger.error(f"Failed to backup file {file_id} to MEGA in background: {e}")


def require_api_key(request: Request):
    """Dependency to check for valid API key in headers or query parameters."""
    if not API_KEY:
        raise HTTPException(status_code=403, detail="Permanent uploads are disabled on this server")

    api_key = request.headers.get("x-api-key") or request.query_params.get("api_key")

    if not api_key or api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")

    return api_key


def _flash_html(message: str | None, level: str = "info", reason: str | None = None) -> str:
    if not message:
        return ""
    safe_level = level if level in {"success", "error", "warning", "info"} else "info"
    allowed_reasons = {"auth", "general", "success"}
    reason_attr = f" data-flash-reason='{reason}'" if reason in allowed_reasons else ""
    return (
        f"<div class='flash flash--{safe_level}' data-flash-level='{safe_level}'{reason_attr} role='alert'>"
        f"{html.escape(message)}"
        "</div>"
    )


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


@router.get("/", include_in_schema=False)
async def home(session: Session = Depends(get_session)):
    if FRONTEND_PRESENT:
        return RedirectResponse(url="/app", status_code=307)

    stats = metrics.snapshot()
    totals = fetch_storage_totals(session)
    uploads_count = max(int(stats.get("uploads", 0)), totals["total_files"])
    max_file_text = f"{MAX_FILE_SIZE_MB:.1f} MB"

    html = render_template(
        "pages/home.html",
        {
            "max_file_text": max_file_text,
            "uploads": str(uploads_count),
            "downloads": str(stats.get("downloads", 0)),
            "deleted": str(stats.get("deleted", 0)),
            "storage_bytes": str(totals["total_bytes"]),
            "year": str(datetime.utcnow().year),
        },
    )
    return HTMLResponse(content=html)


@router.get("/api-info", include_in_schema=False)
async def api_info_redirect():
    if FRONTEND_PRESENT:
        return RedirectResponse(url="/app/api-guide", status_code=307)

    max_file_text = f"{MAX_FILE_SIZE_MB:.1f} MB"
    html = render_template(
        "pages/api.html",
        {"max_file_text": max_file_text, "rate_limit": str(RATE_LIMIT_PER_MINUTE)},
    )
    return HTMLResponse(content=html)


def _human_bytes(value: int) -> str:
    units = ["B", "KB", "MB", "GB", "TB"]
    size = float(max(value, 0))
    for unit in units:
        if size < 1024 or unit == units[-1]:
            formatted = f"{size:.1f}".rstrip("0").rstrip(".")
            return f"{formatted or '0'} {unit}"
        size /= 1024
    return "0 B"


async def _get_admin_password(request: Request) -> str | None:
    password = request.headers.get("x-admin-password") or request.query_params.get("password")
    if password:
        return password
    if request.method in {"POST", "PUT", "DELETE"}:
        form_data = getattr(request.state, "admin_form", None)
        if form_data is None:
            try:
                form_data = await request.form()
            except Exception:
                form_data = None
            else:
                request.state.admin_form = form_data
        if form_data:
            return form_data.get("password")
    return None


# Initialize Redis for admin attempts (with fallback to memory)
def _get_admin_redis_client():
    if REDIS_URL:
        try:
            import redis
            return redis.from_url(REDIS_URL)
        except ImportError:
            logger.warning("Redis not available, using in-memory storage for admin attempts")
        except Exception:
            logger.warning("Could not connect to Redis, using in-memory storage for admin attempts")
    return None


def _get_admin_attempts_redis_key(client: str) -> str:
    return f"admin_attempts:{client}"


# Module-level variable for in-memory fallback
_admin_attempts_memory = {}

def _get_admin_attempts(client: str):
    """Get admin attempts from Redis or fallback to in-memory."""
    redis_client = _get_admin_redis_client()
    if redis_client:
        try:
            key = _get_admin_attempts_redis_key(client)
            attempts_data = redis_client.get(key)
            if attempts_data:
                return json.loads(attempts_data)
            return {"failures": 0, "penalty": 0, "lock_until": None}
        except Exception:
            logger.warning(f"Failed to get admin attempts from Redis for {client}, using default")
            return {"failures": 0, "penalty": 0, "lock_until": None}
    else:
        # In-memory fallback
        return _admin_attempts_memory.setdefault(client, {"failures": 0, "penalty": 0, "lock_until": None})


def _set_admin_attempts(client: str, state: dict):
    """Set admin attempts in Redis or fallback to in-memory."""
    redis_client = _get_admin_redis_client()
    if redis_client:
        try:
            key = _get_admin_attempts_redis_key(client)
            redis_client.setex(key, 3600, json.dumps(state))  # Expire after 1 hour
        except Exception:
            logger.warning(f"Failed to set admin attempts in Redis for {client}")
            # Still update in-memory as fallback if needed
            _admin_attempts_memory[client] = state
    else:
        # In-memory fallback
        _admin_attempts_memory[client] = state


async def _auth_admin(request: Request, allow_blank: bool):
    client = request.client.host if request.client else "unknown"
    state = _get_admin_attempts(client)
    now = datetime.utcnow()
    lock_until_str = state.get("lock_until")
    lock_until = datetime.fromisoformat(lock_until_str) if lock_until_str else None

    if lock_until and now < lock_until:
        remaining = lock_until - now
        minutes = max(1, int(remaining.total_seconds() // 60) + 1)
        msg = f"Too many attempts. Try again in {minutes} minutes."
        if allow_blank:
            return False, msg, True
        raise HTTPException(status_code=429, detail=msg)
    if lock_until and now >= lock_until:
        state["lock_until"] = None

    password = await _get_admin_password(request)
    if not password:
        if allow_blank:
            return False, None, False
        raise HTTPException(status_code=401, detail="Admin password required")

    if ADMIN_PASSWORD and password == ADMIN_PASSWORD:
        state["failures"] = 0
        _set_admin_attempts(client, state)
        return True, None, False

    state["failures"] = state.get("failures", 0) + 1
    if state["failures"] >= 3:
        state["failures"] = 0
        state["penalty"] = state.get("penalty", 0) + 1
        duration = state["penalty"] * ADMIN_LOCK_STEP_SECONDS
        state["lock_until"] = (now + timedelta(seconds=duration)).isoformat()
        minutes = max(1, duration // 60)
        msg = f"Too many attempts. Too many failures. Locked for {minutes} minutes."
        _set_admin_attempts(client, state)
        if allow_blank:
            return False, msg, True
        raise HTTPException(status_code=429, detail=msg)
    msg = "Invalid password"
    _set_admin_attempts(client, state)
    if allow_blank:
        return False, msg, False
    raise HTTPException(status_code=401, detail=msg)


async def _require_admin_api(request: Request):
    success, message, locked = await _auth_admin(request, allow_blank=False)
    if success:
        return
    detail = message or "Admin password required."
    if locked:
        raise HTTPException(status_code=429, detail=detail)
    raise HTTPException(status_code=401, detail=detail)


def _remove_file_from_disk(stored_name: str) -> None:
    try:
        path = (UPLOAD_ROOT / stored_name).resolve()
        path.relative_to(UPLOAD_ROOT)
    except (ValueError, RuntimeError):
        return
    path.unlink(missing_ok=True)




@router.get("/api/admin/summary")
async def admin_summary(request: Request, session: Session = Depends(get_session)):
    await _require_admin_api(request)
    totals = fetch_storage_totals(session)
    snapshot = metrics.snapshot()
    return {
        "uploads": totals["total_files"],
        "downloads": snapshot.get("downloads", 0),
        "deleted": snapshot.get("deleted", 0),
        "storage_bytes": totals["total_bytes"],
        "storage_human": _human_bytes(totals["total_bytes"]),
    }


@router.get("/api/admin/files")
async def admin_files(request: Request, session: Session = Depends(get_session)):
    await _require_admin_api(request)
    files = session.exec(select(FileModel).order_by(FileModel.created_at.desc()).limit(200)).all()
    return {
        "files": [
            {
                "id": f.id,
                "name": f.original_name,
                "size": f.size_bytes,
                "created_at": f.created_at,
                "url": f"/{quote(f.stored_name)}",
            }
            for f in files
        ]
    }


@router.delete("/api/admin/files/{file_id}")
async def admin_delete_single(
    file_id: str,
    request: Request,
    session: Session = Depends(get_session),
):
    await _require_admin_api(request)
    file = session.get(FileModel, file_id)
    if not file:
        raise HTTPException(status_code=404, detail="File not found")
    _remove_file_from_disk(file.stored_name)
    session.delete(file)
    session.commit()
    return {"status": "deleted", "file_id": file_id}


@router.delete("/api/admin/files")
async def admin_delete_everything(request: Request, session: Session = Depends(get_session)):
    await _require_admin_api(request)
    files = session.exec(select(FileModel)).all()
    deleted = 0
    for file in files:
        _remove_file_from_disk(file.stored_name)
        session.delete(file)
        deleted += 1
    session.commit()
    return {"status": "deleted", "count": deleted}


@router.post("/upload", dependencies=[Depends(enforce_rate_limit)])
async def upload(file: UploadFile = File(...), background_tasks: BackgroundTasks = BackgroundTasks(), session: Session = Depends(get_session)):
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

    # Schedule backup to MEGA as a background task
    if MEGA_BACKUP_ENABLED:
        background_tasks.add_task(backup_to_mega_in_background, file_id)

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


@router.post("/upload-permanent", dependencies=[Depends(require_api_key), Depends(enforce_rate_limit)])
async def upload_permanent(file: UploadFile = File(...), background_tasks: BackgroundTasks = BackgroundTasks(), session: Session = Depends(get_session)):
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
        permanent=True,
    )
    session.add(record)
    session.commit()

    # Schedule backup to MEGA as a background task
    if MEGA_BACKUP_ENABLED:
        background_tasks.add_task(backup_to_mega_in_background, file_id)

    metrics.record_upload(size_bytes)
    logger.info(
        "event=upload_success file_id=%s stored_name=%s size_bytes=%s content_type=%s permanent=%s",
        file_id,
        stored_name,
        size_bytes,
        file.content_type or "application/octet-stream",
        True,
    )

    return {
        "id": file_id,
        "url": f"/{quote(stored_name)}",
        "size": size_bytes,
        "type": file.content_type,
        "permanent": True,
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
