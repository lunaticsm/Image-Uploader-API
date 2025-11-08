from collections.abc import Iterator
import logging

from sqlmodel import Session, SQLModel, create_engine
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from app.config import DB_CONNECT_ARGS, DB_URL

engine = create_engine(DB_URL, connect_args=DB_CONNECT_ARGS)


def init_db() -> None:
    SQLModel.metadata.create_all(engine)
    # Ensure the permanent column exists (for schema migrations)
    ensure_schema_compatibility()


def ensure_schema_compatibility():
    """Ensure the database schema is compatible with current models, adding missing columns if needed."""
    with engine.connect() as conn:
        # Check if permanent column exists in file table by querying table info
        try:
            result = conn.execute(text("PRAGMA table_info(file)")).fetchall()
            column_names = [row[1] for row in result]  # Second column in PRAGMA is column name
            if 'permanent' not in column_names:
                # For SQLite, we need to recreate the table with the new column
                # First, backup existing data
                conn.execute(text("ALTER TABLE file RENAME TO file_backup"))
                
                # Create new table with permanent column
                SQLModel.metadata.tables['file'].create(conn)
                
                # Copy data from backup to new table, setting permanent to false for existing records
                conn.execute(text("""
                    INSERT INTO file (id, original_name, stored_name, content_type, size_bytes, permanent, created_at)
                    SELECT id, original_name, stored_name, content_type, size_bytes, 0, created_at 
                    FROM file_backup
                """))
                
                # Drop backup table
                conn.execute(text("DROP TABLE file_backup"))
                conn.commit()
                logging.info("Migrated 'file' table to include 'permanent' column")
            else:
                logging.info("Database schema is up to date")
        except OperationalError as e:
            logging.warning(f"Could not check or migrate database schema: {e}")


def get_session() -> Iterator[Session]:
    with Session(engine) as session:
        yield session
