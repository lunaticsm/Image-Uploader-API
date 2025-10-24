# Image Uploader API

FastAPI application that stores uploaded files to disk, tracks them with SQLModel, and serves them back through a lightweight CDN-like interface.

## Features
- Public upload and listing endpoints with UUID-based storage.
- Files stored with generated UUID names while preserving the original name for metadata.
- Optional background cleaner that prunes files older than a configured retention window.
- SQLite by default, with configurable database URL via environment variables.

## Getting Started

```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

Optional settings:

| Variable | Default | Description |
|----------|---------|-------------|
| `UPLOAD_DIR` | `./uploads` | Directory for stored files. Created automatically. |
| `DB_URL` | `sqlite:///./cdn.db` | SQLModel database URL. Use a server DB in production. |
| `DELETE_AFTER_HOURS` | `72` | Retention window for cleanup. |
| `CORS_ORIGINS` | `*` | Comma-separated list of allowed origins. |
| `ENABLE_CLEANER` | `true` | Disable (`false`) to skip scheduling the cleanup job. |

Run the API:

```bash
./run.sh
# or
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2 --proxy-headers
```

## API Overview

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/upload` | Accepts multipart file upload, stores file, returns metadata (`id`, `url`, `size`, `type`). |
| `GET` | `/list` | Returns list of stored files with original name, size, and creation timestamp. |
| `GET` | `/{filename}` | Serves a stored file by UUID filename as returned by `/upload`. |

Returned `url` values are relative (e.g. `/3d4d...jpg`), suitable for prefixing with your CDN/API host.

## Cleaning Expired Files

If `ENABLE_CLEANER` is `true`, a background APScheduler job runs hourly to delete files older than `DELETE_AFTER_HOURS`. The job removes both the file on disk and its database row.

## Development & Testing

Run the unit tests (requires dependencies from `requirements.txt`):

```bash
pytest
```

The test suite spins up the FastAPI app against a temporary SQLite database to cover:
- Upload/list/serve happy path.
- Directory traversal hardening for file serving.

## Deployment Notes
- When using SQLite, the app configures thread-safe connection settings. For higher concurrency, consider a PostgreSQL or MySQL instance and update `DB_URL`.
- Mount or back up `UPLOAD_DIR` storage if files need to persist beyond the cleaner retention window.
