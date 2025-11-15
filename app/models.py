from datetime import datetime
from sqlmodel import SQLModel, Field

class File(SQLModel, table=True):
    id: str = Field(primary_key=True)
    original_name: str
    stored_name: str
    content_type: str
    size_bytes: int
    permanent: bool = Field(default=False)
    backed_up: bool = Field(default=False)  # Whether file has been backed up to remote storage
    backup_id: str = Field(default=None, nullable=True)    # Remote backup file identifier
    backup_time: datetime = Field(default=None, nullable=True)  # Time of backup
    created_at: datetime = Field(default_factory=datetime.utcnow)
