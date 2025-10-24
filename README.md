# Image Uploader API

FastAPI-powered micro CDN for storing and serving uploaded assets. Files are written to disk, indexed with SQLModel, and delivered with CDN-friendly cache headers plus live usage stats on the landing page.

## Features
- Public upload and listing endpoints with UUID-based storage.
- 10&nbsp;MB per-file upload cap with friendly error responses.
- In-memory rate limiting (per-client/minute) to prevent abuse.
- Automatic cleanup job that prunes files after the configured retention window.
- Live metrics (uploads, downloads, cleanups) exposed on the home page.
- SQLite by default, with environment overrides for production databases.

## Live Demo
- Try the hosted instance at https://cdn.lunaticsm.web.id to see the animated metrics, HTML landing page, and API guide in action.

## Getting Started

```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

Optional environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `UPLOAD_DIR` | `./uploads` | Directory for stored files. Created automatically. |
| `DB_URL` | `sqlite:///./cdn.db` | SQLModel database URL. Use PostgreSQL/MySQL for multi-worker deployments. |
| `DELETE_AFTER_HOURS` | `72` | Retention window for the cleaner job. |
| `CORS_ORIGINS` | `*` | Comma-separated list of allowed origins. |
| `ENABLE_CLEANER` | `true` | Disable (`false`) to skip scheduling the cleanup job. |
| `MAX_FILE_SIZE_BYTES` | `10485760` | Max upload size in bytes (default 10 MB). |
| `RATE_LIMIT_PER_MINUTE` | `60` | Allowed requests per client per minute. |
| `CACHE_MAX_AGE_SECONDS` | `3600` | Cache lifetime used for served files. |

Run the API:

```bash
./run.sh
# or
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2 --proxy-headers
```

Visit `/` for a minimalist landing page with real-time usage metrics, and `/api-info` for a human-friendly API guide.

## API Overview

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/upload` | Accepts multipart file upload (respecting the configured size limit) and returns metadata (`id`, `url`, `size`, `type`). |
| `GET` | `/list` | Returns a JSON array of stored files ordered by newest first. |
| `GET` | `/{filename}` | Serves a stored file by UUID filename and includes `Cache-Control` headers. |

Returned `url` values are relative (e.g. `/3d4d...jpg`), suitable for prefixing with your CDN/API host.

## Cleaning Expired Files

If `ENABLE_CLEANER` is `true`, a background APScheduler job runs hourly to delete files older than `DELETE_AFTER_HOURS`. Each run emits structured logs and increments the on-page cleanup counter.

## Development & Testing

Run the unit tests (requires dependencies from `requirements.txt`):

```bash
pytest
```

The suite bootstraps the FastAPI app against a temporary SQLite database to cover:
- Upload/list/serve happy path and cache headers.
- Directory traversal protections for served files.
- Upload rejection for files above the configured size.
- Rate limiting behaviour (HTTP 429).
- Rendering of the home and API documentation pages.

## Deployment Notes
- For higher concurrency, point `DB_URL` at a server database and keep the provided SQLite connection args if you stay on SQLite.
- Mount or back up `UPLOAD_DIR` storage if files need to persist beyond the cleaner retention window.
- Tune `RATE_LIMIT_PER_MINUTE`, `MAX_FILE_SIZE_BYTES`, and `CACHE_MAX_AGE_SECONDS` to match your traffic patterns.
