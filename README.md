# Image Uploader API

FastAPI-powered micro CDN for storing and serving uploaded assets. Files are written to disk, indexed with SQLModel, and delivered with CDN-friendly cache headers plus live usage stats on the landing page.

## Features
- Public upload and listing endpoints with compact base62 slugs (Telegraph/ImgBB style URLs).
- 10&nbsp;MB per-file upload cap with friendly error responses.
- In-memory rate limiting (per-client/minute) to prevent abuse.
- Automatic cleanup job that prunes files after the configured retention window.
- Live metrics (uploads, downloads, cleanups) exposed on the home page.
- Password-protected admin dashboard to inspect uploads, storage usage, and prune files with lockout protection.
- SQLite by default, with environment overrides for production databases.

## Live Demo
- Try the hosted instance at [https://cdn.lunaticsm.web.id](https://cdn.alterbase.web.id/) to see the animated metrics, HTML landing page, and API guide in action.

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
| `DB_URL` | `sqlite:///./cdn.db` | SQLModel database URL. Use PostgreSQL/MySQL for multi-worker deployments. Use `postgresql+psycopg2://user:pass@host:5432/db` inside Docker. |
| `DELETE_AFTER_HOURS` | `72` | Retention window for the cleaner job. |
| `CORS_ORIGINS` | `*` | Comma-separated list of allowed origins. |
| `ENABLE_CLEANER` | `true` | Disable (`false`) to skip scheduling the cleanup job. |
| `MAX_FILE_SIZE_BYTES` | `10485760` | Max upload size in bytes (default 10 MB). |
| `RATE_LIMIT_PER_MINUTE` | `60` | Allowed requests per client per minute. |
| `CACHE_MAX_AGE_SECONDS` | `3600` | Cache lifetime used for served files. |
| `ADMIN_PASSWORD` | `admin-dev-password` | Password required to access the `/admin` dashboard. |
| `ADMIN_LOCK_STEP_SECONDS` | `300` | Lock duration increment (in seconds) after repeated failed admin logins. |
| `FILE_ID_LENGTH` | `7` | Length of generated slug IDs (min 4, max 32). |

Run the API:

```bash
./run.sh
# or
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2 --proxy-headers
```

Visit `/` for a minimalist landing page with real-time usage metrics, and `/api-info` for a human-friendly API guide.

### Docker

Build and run with Docker:

```bash
docker build -t image-uploader .
docker run --rm -p 8000:8000 --env-file .env -v $(pwd)/uploads:/app/uploads image-uploader
```

Customize `DB_URL`, `UPLOAD_DIR`, etc. via the `--env-file` or individual `-e` flags.

### Docker Compose & Postgres

For a Postgres-backed setup (with uploads persisted to a Docker volume), use the provided composition:

```bash
docker compose up --build
```

The compose file maps uploads into a named volume at `/data/uploads`, points the API at the bundled Postgres (`postgresql+psycopg2://cdn:cdn@db:5432/cdn`), and loads overrides from `.env`.

Key environment variables for production deployments:

| Variable | Description |
|----------|-------------|
| `DB_URL` | Should point to your managed database, e.g. `postgresql+psycopg2://user:pass@host:5432/dbname`. |
| `UPLOAD_DIR` | Mounted path where files are stored (use a persistent volume or S3-compatible backend). |
| `RATE_LIMIT_PER_MINUTE` | Adjust per-client quotas according to expected traffic. |
| `MAX_FILE_SIZE_BYTES` | Enforce a tighter upload cap if needed. |
| `CACHE_MAX_AGE_SECONDS` | Tune cache headers for served files. |
| `CORS_ORIGINS` | Lock down origins for production frontends. |
| `ENABLE_CLEANER` | Keep true to remove stale files automatically. |
| `ADMIN_PASSWORD` | Password provided via header/form/query for `/admin`. |
| `ADMIN_LOCK_STEP_SECONDS` | Lock duration increment (seconds) after failed admin logins. |

## API Overview

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/upload` | Accepts multipart file upload (respecting the configured size limit) and returns metadata (`id`, `url`, `size`, `type`). |
| `GET` | `/{filename}` | Serves a stored file by slug filename and includes `Cache-Control` headers. |

Returned `url` values are relative (e.g. `/aB7xYzQ.jpg`), suitable for prefixing with your CDN/API host.

### Admin Dashboard
- Visit `/admin` with the header `X-Admin-Password: <ADMIN_PASSWORD>` (or include `password` in the query/form) to view uploads, downloads, cleanup counts, recent files, and trigger per-file or bulk deletions.
- After three failed attempts the admin login is locked; each lock adds `ADMIN_LOCK_STEP_SECONDS` (default 5 minutes) to the wait time.

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

## License

Released under the [MIT License](LICENSE).
