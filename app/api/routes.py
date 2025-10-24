from __future__ import annotations

import logging
import html
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from sqlmodel import Session, select

from app.config import (
    ADMIN_LOCK_STEP_SECONDS,
    ADMIN_PASSWORD,
    CACHE_MAX_AGE_SECONDS,
    MAX_FILE_SIZE,
    RATE_LIMIT_PER_MINUTE,
    UPLOAD_DIR,
)
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
_admin_attempts: dict[str, dict] = {}


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


@router.get("/", response_class=HTMLResponse)
async def home(session: Session = Depends(get_session)):
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


@router.get("/api-info", response_class=HTMLResponse)
async def api_info():
    max_file_text = f"{MAX_FILE_SIZE_MB:.1f} MB"
    html = render_template(
        "pages/api.html",
        {"max_file_text": max_file_text, "rate_limit": str(RATE_LIMIT_PER_MINUTE)},
    )
    return HTMLResponse(content=html)


def _render_admin_table(files: list[FileModel]) -> str:
    rows: list[str] = []
    for file in files:
        preview = f"<img src='/{quote(file.stored_name)}' alt='preview' loading='lazy' />"
        rows.append(
            "<tr>"
            f"<td>{html.escape(file.id)}</td>"
            f"<td class='preview-cell'>{preview}</td>"
            f"<td>{html.escape(file.original_name)}</td>"
            f"<td>{file.size_bytes} B</td>"
            f"<td>{file.created_at}</td>"
            "<td>"
            "<form method='post' action='/admin/delete' class='inline'>"
            f"<input type='hidden' name='file_id' value='{html.escape(file.id)}' />"
            "<input type='password' name='password' placeholder='Admin password' required />"
            "<button type='submit'>Delete</button>"
            "</form>"
            "</td>"
            "</tr>"
        )
    return "".join(rows) or "<tr><td colspan='5'>No files yet</td></tr>"


def _human_bytes(value: int) -> str:
    units = ["B", "KB", "MB", "GB", "TB"]
    size = float(max(value, 0))
    for unit in units:
        if size < 1024 or unit == units[-1]:
            formatted = f"{size:.1f}".rstrip("0").rstrip(".")
            return f"{formatted or '0'} {unit}"
        size /= 1024
    return "0 B"


def _render_admin_login(message: str | None = None, level: str = "info", reason: str | None = None) -> str:
    flash_html = _flash_html(message, level, reason)
    return render_template("pages/admin_login.html", {"flash_message": flash_html})


def _render_admin_page(
    session: Session, message: str | None = None, level: str = "info", reason: str | None = None
) -> str:
    totals = fetch_storage_totals(session)
    snapshot = metrics.snapshot()
    stmt = select(FileModel).order_by(FileModel.created_at.desc()).limit(50)
    files = session.exec(stmt).all()
    flash_html = _flash_html(message, level, reason)
    return render_template(
        "pages/admin.html",
        {
            "uploads": totals["total_files"],
            "downloads": snapshot.get("downloads", 0),
            "deleted": snapshot.get("deleted", 0),
            "storage_human": _human_bytes(totals["total_bytes"]),
            "table_rows": _render_admin_table(files),
            "flash_message": flash_html,
        },
    )


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


async def _auth_admin(request: Request, allow_blank: bool):
    client = request.client.host if request.client else "unknown"
    state = _admin_attempts.setdefault(client, {"failures": 0, "penalty": 0, "lock_until": None})
    now = datetime.utcnow()
    lock_until = state.get("lock_until")
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
        return True, None, False

    state["failures"] = state.get("failures", 0) + 1
    if state["failures"] >= 3:
        state["failures"] = 0
        state["penalty"] = state.get("penalty", 0) + 1
        duration = state["penalty"] * ADMIN_LOCK_STEP_SECONDS
        state["lock_until"] = now + timedelta(seconds=duration)
        minutes = max(1, duration // 60)
        msg = f"Too many attempts. Too many failures. Locked for {minutes} minutes."
        if allow_blank:
            return False, msg, True
        raise HTTPException(status_code=429, detail=msg)
    msg = "Invalid password"
    if allow_blank:
        return False, msg, False
    raise HTTPException(status_code=401, detail=msg)


def _remove_file_from_disk(stored_name: str) -> None:
    try:
        path = (UPLOAD_ROOT / stored_name).resolve()
        path.relative_to(UPLOAD_ROOT)
    except (ValueError, RuntimeError):
        return
    path.unlink(missing_ok=True)


@router.api_route("/admin", methods=["GET", "POST"], response_class=HTMLResponse)
async def admin_dashboard(request: Request, session: Session = Depends(get_session)):
    success, message, locked = await _auth_admin(request, allow_blank=True)
    if success:
        html = _render_admin_page(session, message)
        return HTMLResponse(content=html)
    html = _render_admin_login(message, "error" if message else "info", "auth" if message else None)
    status = 429 if locked and message else 200
    return HTMLResponse(content=html, status_code=status)


@router.post("/admin/delete", response_class=HTMLResponse)
async def admin_delete_file(
    request: Request,
    session: Session = Depends(get_session),
):
    form = getattr(request.state, "admin_form", None)
    if form is None:
        form = await request.form()
        request.state.admin_form = form

    success, message, locked = await _auth_admin(request, allow_blank=True)
    if not success:
        status = 429 if locked else 401
        failure_message = message or "Admin password required."
        html = _render_admin_page(session, failure_message, "error", "auth")
        return HTMLResponse(content=html, status_code=status)

    file_id = form.get("file_id")
    if not file_id:
        raise HTTPException(status_code=400, detail="Missing file_id")
    file = session.get(FileModel, file_id)
    if not file:
        html = _render_admin_page(session, "File not found.", "error", "general")
        return HTMLResponse(content=html, status_code=404)

    _remove_file_from_disk(file.stored_name)
    session.delete(file)
    session.commit()
    html = _render_admin_page(session, "File deleted.", "success", "success")
    return HTMLResponse(content=html)


@router.post("/admin/delete-all", response_class=HTMLResponse)
async def admin_delete_all(
    request: Request,
    session: Session = Depends(get_session),
):
    form = getattr(request.state, "admin_form", None)
    if form is None:
        form = await request.form()
        request.state.admin_form = form

    success, message, locked = await _auth_admin(request, allow_blank=True)
    if not success:
        status = 429 if locked else 401
        failure_message = message or "Admin password required."
        html = _render_admin_page(session, failure_message, "error", "auth")
        return HTMLResponse(content=html, status_code=status)

    files = session.exec(select(FileModel)).all()
    deleted = 0
    for file in files:
        _remove_file_from_disk(file.stored_name)
        session.delete(file)
        deleted += 1
    session.commit()
    html = _render_admin_page(session, f"Deleted {deleted} files.", "success", "success")
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
