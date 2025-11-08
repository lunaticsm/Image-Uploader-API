from datetime import datetime
from sqlmodel import SQLModel, Field

class File(SQLModel, table=True):
    id: str = Field(primary_key=True)
    original_name: str
    stored_name: str
    content_type: str
    size_bytes: int
    permanent: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)
