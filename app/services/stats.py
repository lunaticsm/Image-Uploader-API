from sqlalchemy import func
from sqlmodel import Session, select

from app.models import File as FileModel


def fetch_storage_totals(session: Session) -> dict[str, int]:
    total_files = session.exec(select(func.count(FileModel.id))).one()
    total_bytes = session.exec(select(func.coalesce(func.sum(FileModel.size_bytes), 0))).one()

    return {
        "total_files": int(total_files or 0),
        "total_bytes": int(total_bytes or 0),
    }
