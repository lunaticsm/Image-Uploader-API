from __future__ import annotations

import os
import secrets
import string
from datetime import datetime, timedelta
from sqlmodel import Session, select
from app.config import UPLOAD_DIR, DELETE_AFTER_HOURS, FILE_ID_LENGTH
from app.models import File

os.makedirs(UPLOAD_DIR, exist_ok=True)

_SLUG_ALPHABET = string.ascii_letters + string.digits
_MAX_SLUG_ATTEMPTS = 5


def _generate_file_id(length: int = FILE_ID_LENGTH) -> str:
    return "".join(secrets.choice(_SLUG_ALPHABET) for _ in range(length))


def _reserve_path(ext: str) -> tuple[str, str]:
    for _ in range(_MAX_SLUG_ATTEMPTS):
        file_id = _generate_file_id()
        stored_name = f"{file_id}{ext}"
        path = os.path.join(UPLOAD_DIR, stored_name)
        if not os.path.exists(path):
            return stored_name, path
    raise RuntimeError("Unable to allocate a unique file slug")


def save_file(file_bytes: bytes, original_name: str, content_type: str) -> str:
    ext = os.path.splitext(original_name)[1] or ".bin"
    stored_name, path = _reserve_path(ext)
    with open(path, "wb") as f:
        f.write(file_bytes)
    return stored_name, len(file_bytes)

def delete_expired_files(engine):
    from datetime import datetime
    with Session(engine) as session:
        cutoff = datetime.utcnow() - timedelta(hours=DELETE_AFTER_HOURS)
        # Only delete non-permanent files that are older than the cutoff
        stmt = select(File).where(File.created_at < cutoff, File.permanent == False)
        old_files = session.exec(stmt).all()
        for f in old_files:
            try:
                os.remove(os.path.join(UPLOAD_DIR, f.stored_name))
            except FileNotFoundError:
                pass
            session.delete(f)
        session.commit()
    return len(old_files)
