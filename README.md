# Image Uploader API

FastAPI-powered micro CDN for storing and serving uploaded assets. Files are written to disk, indexed with SQLModel, and delivered with CDN-friendly cache headers plus live usage stats on the landing page.

## Features
- Public upload and listing endpoints with compact base62 slugs (Telegraph/ImgBB style URLs).
- 10&nbsp;MB per-file upload cap with friendly error responses.
- In-memory rate limiting (per-client/minute) to prevent abuse.
- Automatic cleanup job that prunes files after the configured retention window.
- Live metrics (uploads, downloads, cleanups) exposed on the home page (now powered by a React SPA).
- Password-protected admin dashboard to inspect uploads, storage usage, and prune files with lockout protection.
- SQLite by default, with environment overrides for production databases.
- Optional MEGA cloud backup so every upload is mirrored to remote storage before cleanup.

## Live Demo
- Try the hosted instance at [https://cdn.alterbase.web.id](https://cdn.alterbase.web.id) to see the animated metrics, HTML landing page, and API guide in action.

## Getting Started

### Prerequisites
- Python 3.12+
- Node.js 18+
- npm 9+
- A MEGA account if you plan to enable cloud mirroring

```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

Optional environment variables (copy `.env-sample` to `.env` and adjust as needed):

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
| `MEGA_BACKUP_ENABLED` | `false` | Enable (`true`) to store a copy of each upload in MEGA. |
| `MEGA_EMAIL` | (empty) | MEGA account email used for API authentication. |
| `MEGA_PASSWORD` | (empty) | MEGA account password. Use an app-specific password if available. |
| `MEGA_FOLDER_NAME` | (empty) | Optional folder (created automatically) to store uploaded files inside your MEGA drive. |

Run the API (after building the frontend):

```bash
./run.sh
# or
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2 --proxy-headers
```

The React UI lives at `/app` (with routes for the landing page, API guide, and admin dashboard). Static assets for the SPA are served from `/frontend`.

### Frontend (React)

The new UI is built with Vite + React. To run it locally:

```bash
cd frontend
npm install
npm run dev
```

During deployment (or before launching FastAPI), build the SPA:

```bash
cd frontend
npm install  # first time only
npm run build
```

The Dockerfile already runs the build step so the `/frontend/dist` output is available to the API server.
If you are deploying manually, ensure you run the build command above whenever you tweak the frontend.

### Docker

The Dockerfile uses a multi-stage build: the React SPA is compiled in a Node builder image and copied into the slim Python runtime, so the final image stays lightweight.

Build and run with Docker:

```bash
docker build -t image-uploader .
docker run --rm -p 8000:8000 --env-file .env -v $(pwd)/uploads:/app/uploads image-uploader
```

Make sure your `.env` (or `--env-file`) contains the MEGA credentials if you plan to enable remote backups. Customize `DB_URL`, `UPLOAD_DIR`, etc. via the `--env-file` or individual `-e` flags. The frontend build is handled inside the Docker image, so no local Node installation is required for container deployments.

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
| `POST` | `/upload-permanent` | Accepts multipart file upload with API key authentication and returns metadata (`id`, `url`, `size`, `type`, `permanent`). Permanent files are not subject to automatic cleanup. |
| `GET` | `/{filename}` | Serves a stored file by slug filename and includes `Cache-Control` headers. |

Returned `url` values are relative (e.g. `/aB7xYzQ.jpg`), suitable for prefixing with your CDN/API host.

### API Key Authentication

For permanent file uploads, you need to provide a valid API key in one of these ways:
- Header: `X-API-Key: your-api-key`
- Query parameter: `?api_key=your-api-key`

Set the `API_KEY` environment variable to configure the server's expected API key.

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

## MEGA Backup Integration

The application now mirrors uploads to [MEGA](https://mega.io/) instead of Google Drive. To enable the backup job:

1. Create or use an existing MEGA account dedicated to your application (set up an app password if two-factor auth is enabled).
2. Copy `.env-sample` to `.env` and set `MEGA_BACKUP_ENABLED=true`, `MEGA_EMAIL`, and `MEGA_PASSWORD`.
3. Optionally provide `MEGA_FOLDER_NAME` to store backups inside a dedicated folder. The folder is created automatically the first time the app starts.

Once enabled, every successful upload is copied to MEGA. The cleaner only removes expired files after they have been uploaded successfully, and deletions also remove the remote copy so your cloud storage stays tidy. Startup will fail fast if MEGA credentials are invalid so misconfigurations are caught before serving traffic.


## License

Released under the [MIT License](LICENSE).
