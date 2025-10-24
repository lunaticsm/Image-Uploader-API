import os
import uuid
from datetime import datetime, timedelta
from sqlmodel import Session, select
from app.config import UPLOAD_DIR, DELETE_AFTER_HOURS
from app.models import File

os.makedirs(UPLOAD_DIR, exist_ok=True)

def save_file(file_bytes: bytes, original_name: str, content_type: str) -> str:
    ext = os.path.splitext(original_name)[1] or ".bin"
    file_id = str(uuid.uuid4())
    stored_name = f"{file_id}{ext}"
    path = os.path.join(UPLOAD_DIR, stored_name)
    with open(path, "wb") as f:
        f.write(file_bytes)
    return stored_name, len(file_bytes)

def delete_expired_files(engine):
    from datetime import datetime
    with Session(engine) as session:
        cutoff = datetime.utcnow() - timedelta(hours=DELETE_AFTER_HOURS)
        stmt = select(File).where(File.created_at < cutoff)
        old_files = session.exec(stmt).all()
        for f in old_files:
            try:
                os.remove(os.path.join(UPLOAD_DIR, f.stored_name))
            except FileNotFoundError:
                pass
            session.delete(f)
        session.commit()
    return len(old_files)
