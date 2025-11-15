from __future__ import annotations

import logging
import os
import secrets
import string
from datetime import datetime, timedelta
from sqlmodel import Session, select
from app.config import (
    UPLOAD_DIR,
    DELETE_AFTER_HOURS,
    FILE_ID_LENGTH,
    MEGA_BACKUP_ENABLED,
    MEGA_EMAIL,
    MEGA_PASSWORD,
    MEGA_FOLDER_NAME,
)
from app.models import File

os.makedirs(UPLOAD_DIR, exist_ok=True)

_SLUG_ALPHABET = string.ascii_letters + string.digits
_MAX_SLUG_ATTEMPTS = 5

# Global variable to store the MEGA backup service instance
_mega_backup_service = None

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


def _get_mega_backup():
    """Lazily initialize the MEGA backup service."""
    global _mega_backup_service
    if _mega_backup_service is None:
        from app.services.mega_backup import MegaBackup
        _mega_backup_service = MegaBackup(
            email=MEGA_EMAIL,
            password=MEGA_PASSWORD,
            folder_name=MEGA_FOLDER_NAME or None,
        )
    return _mega_backup_service


def initialize_backup_service():
    """Ensure the MEGA backup service is initialized (used during startup)."""
    if MEGA_BACKUP_ENABLED:
        _get_mega_backup()


def backup_to_cloud(file_path: str, stored_name: str) -> tuple[str, str]:
    """Backup file to MEGA."""
    backup_service = _get_mega_backup()
    return backup_service.upload_file(file_path, stored_name)


def delete_expired_files(engine):
    from datetime import datetime
    from sqlalchemy.exc import OperationalError
    from app.db import ensure_connection
    import time

    # First, ensure the connection is alive
    if not ensure_connection():
        # If connection is dead, try to let SQLAlchemy handle it with the new connection pool settings
        pass

    # Exponential backoff retry mechanism to handle connection issues
    max_retries = 5
    base_delay = 1  # Start with 1 second
    for attempt in range(max_retries):
        try:
            with Session(engine) as session:
                cutoff = datetime.utcnow() - timedelta(hours=DELETE_AFTER_HOURS)
                # Only delete non-permanent files that are both expired AND backed up remotely
                if MEGA_BACKUP_ENABLED:
                    # Only delete files that are both expired AND backed up remotely
                    stmt = select(File).where(
                        File.created_at < cutoff,
                        File.permanent == False,
                        File.backed_up == True  # Only delete if backed up
                    )
                else:
                    # Original behavior if MEGA backup not enabled
                    stmt = select(File).where(
                        File.created_at < cutoff,
                        File.permanent == False
                    )

                old_files = session.exec(stmt).all()

                deleted = 0
                mega_delete_failures = 0
                for f in old_files:
                    try:
                        os.remove(os.path.join(UPLOAD_DIR, f.stored_name))
                    except FileNotFoundError:
                        pass  # File already deleted

                    # If MEGA backup is enabled and file has a backup, delete from MEGA too
                    if MEGA_BACKUP_ENABLED and f.backup_id:
                        try:
                            backup_service = _get_mega_backup()
                            backup_service.delete_file(f.backup_id)
                        except Exception as e:
                            mega_delete_failures += 1
                            logger = logging.getLogger("image_uploader.storage")
                            logger.error(
                                "event=mega_delete_failure file_id=%s backup_id=%s error=%s",
                                f.id, f.backup_id, str(e)
                            )
                            # Continue with local deletion even if MEGA deletion fails
                            # This prevents backup drift where local files are deleted but MEGA copies remain

                    session.delete(f)
                    deleted += 1

                session.commit()

                # Log summary if there were any MEGA deletion failures
                if mega_delete_failures > 0:
                    logger = logging.getLogger("image_uploader.storage")
                    logger.warning(
                        "event=cleaner_summary deleted=%d mega_deletion_failures=%d",
                        deleted, mega_delete_failures
                    )

                return deleted
        except OperationalError as e:
            error_msg = str(e).lower()
            if ("ssl connection has been closed unexpectedly" in error_msg or
                "connection not found" in error_msg or
                "server closed the connection unexpectedly" in error_msg or
                "connection timed out" in error_msg or
                "could not connect to server" in error_msg):

                if attempt < max_retries - 1:
                    # Exponential backoff: wait longer after each failed attempt
                    delay = base_delay * (2 ** attempt)  # 1s, 2s, 4s, 8s, 16s
                    logger = logging.getLogger("image_uploader.storage")
                    logger.warning(
                        "event=cleaner_retry attempt=%d delay_seconds=%d error=%s",
                        attempt + 1, delay, str(e)
                    )
                    time.sleep(delay)
                    continue
                else:
                    logger = logging.getLogger("image_uploader.storage")
                    logger.error(
                        "event=cleaner_give_up max_retries=%d error=%s",
                        max_retries, str(e)
                    )
                    # Re-raise the exception if all retries are exhausted
                    raise
            else:
                # Re-raise other types of OperationalError
                logger = logging.getLogger("image_uploader.storage")
                logger.error(
                    "event=cleaner_unexpected_error error=%s",
                    str(e)
                )
                raise


def backup_and_mark(session: Session, file_id: str):
    """Backup a specific file to MEGA and mark it as backed up"""
    file_record = session.get(File, file_id)
    if file_record and not file_record.backed_up:
        file_path = os.path.join(UPLOAD_DIR, file_record.stored_name)

        if os.path.exists(file_path):
            try:
                backup_file_id, _ = backup_to_cloud(file_path, file_record.stored_name)

                # Update the database record
                file_record.backed_up = True
                file_record.backup_id = backup_file_id
                file_record.backup_time = datetime.utcnow()
                session.add(file_record)
                session.commit()

                return True
            except Exception as e:
                logger = logging.getLogger("image_uploader.storage")
                logger.error(
                    "event=mega_backup_failure file_id=%s error=%s",
                    file_id, str(e)
                )
                return False

    return False
