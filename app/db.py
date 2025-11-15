from collections.abc import Iterator
from contextlib import contextmanager
import logging

from sqlmodel import Session, SQLModel, create_engine
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from sqlalchemy.pool import QueuePool

from app.config import DB_CONNECT_ARGS, DB_URL

# Configure engine with connection pooling parameters to handle long-running processes
engine = create_engine(
    DB_URL,
    connect_args=DB_CONNECT_ARGS,
    poolclass=QueuePool,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,  # Verify connections before use
    pool_recycle=3600,   # Recycle connections after 1 hour
    echo=False           # Set to True for debugging SQL queries
)


def init_db() -> None:
    SQLModel.metadata.create_all(engine)
    # Ensure the permanent column exists (for schema migrations)
    ensure_schema_compatibility()


def ensure_schema_compatibility():
    """Ensure the database schema is compatible with current models, adding missing columns if needed."""
    with engine.connect() as conn:
        try:
            # Check if database is SQLite or PostgreSQL and use appropriate approach
            if 'sqlite' in DB_URL.lower():
                # SQLite-specific approach
                result = conn.execute(text("PRAGMA table_info(file)")).fetchall()
                column_names = [row[1] for row in result]  # Second column in PRAGMA is column name

                # Add missing columns if they don't exist
                if 'permanent' not in column_names:
                    conn.execute(text("ALTER TABLE file ADD COLUMN permanent BOOLEAN DEFAULT FALSE"))

                if 'backed_up' not in column_names:
                    conn.execute(text("ALTER TABLE file ADD COLUMN backed_up BOOLEAN DEFAULT FALSE"))

                if 'backup_id' not in column_names:
                    conn.execute(text("ALTER TABLE file ADD COLUMN backup_id TEXT DEFAULT NULL"))

                if 'backup_time' not in column_names:
                    conn.execute(text("ALTER TABLE file ADD COLUMN backup_time TIMESTAMP DEFAULT NULL"))

                conn.commit()
                logging.info("Database schema is up to date")
            else:
                # PostgreSQL-specific approach
                # Check for permanent column
                result = conn.execute(text("""
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_name = 'file' AND column_name = 'permanent'
                """)).fetchall()

                if not result:
                    # Add the permanent column to the file table
                    conn.execute(text("ALTER TABLE file ADD COLUMN permanent BOOLEAN DEFAULT FALSE"))

                # Check for backed_up column
                result = conn.execute(text("""
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_name = 'file' AND column_name = 'backed_up'
                """)).fetchall()

                if not result:
                    # Add the backed_up column to the file table
                    conn.execute(text("ALTER TABLE file ADD COLUMN backed_up BOOLEAN DEFAULT FALSE"))

                # Check for backup_id column
                result = conn.execute(text("""
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_name = 'file' AND column_name = 'backup_id'
                """)).fetchall()

                if not result:
                    # Add the backup_id column to the file table
                    conn.execute(text("ALTER TABLE file ADD COLUMN backup_id VARCHAR DEFAULT NULL"))

                # Check for backup_time column
                result = conn.execute(text("""
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_name = 'file' AND column_name = 'backup_time'
                """)).fetchall()

                if not result:
                    # Add the backup_time column to the file table
                    conn.execute(text("ALTER TABLE file ADD COLUMN backup_time TIMESTAMP DEFAULT NULL"))

                conn.commit()
                logging.info("Database schema is up to date")
        except OperationalError as e:
            logging.warning(f"Could not check or migrate database schema: {e}")


def get_session() -> Iterator[Session]:
    with Session(engine) as session:
        yield session


session_scope = contextmanager(get_session)


def ensure_connection():
    """
    Verify that the database connection is alive.
    This is useful for long-running processes that might encounter stale connections.
    """
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except OperationalError:
        return False
