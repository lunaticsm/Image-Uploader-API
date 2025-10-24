from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import SQLModel, create_engine, Session, select
from urllib.parse import quote
from pathlib import Path
from app.config import DB_URL, UPLOAD_DIR, CORS_ORIGINS, DB_CONNECT_ARGS, ENABLE_CLEANER
from app.models import File as FileModel
from app.storage import save_file
from app.cleaner import start_cleaner
from starlette.exceptions import HTTPException as StarletteHTTPException

app = FastAPI(title="AlterBase CDN API", version="1.0")

# CORS
origins = [o.strip() for o in CORS_ORIGINS.split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

engine = create_engine(DB_URL, connect_args=DB_CONNECT_ARGS)
SQLModel.metadata.create_all(engine)
if ENABLE_CLEANER:
    start_cleaner(engine)  # background scheduler

_ERROR_PAGE_PATH = Path(__file__).resolve().parent / "templates" / "404.html"
_NOT_FOUND_HTML = _ERROR_PAGE_PATH.read_text(encoding="utf-8") if _ERROR_PAGE_PATH.is_file() else "<h1>404 - Not Found</h1>"

_HOME_PAGE_PATH = Path(__file__).resolve().parent / "templates" / "index.html"
_HOME_HTML = _HOME_PAGE_PATH.read_text(encoding="utf-8") if _HOME_PAGE_PATH.is_file() else "<h1>Welcome</h1>"

_API_PAGE_PATH = Path(__file__).resolve().parent / "templates" / "api.html"
_API_HTML = _API_PAGE_PATH.read_text(encoding="utf-8") if _API_PAGE_PATH.is_file() else "<h1>API</h1>"


@app.exception_handler(404)
async def not_found_handler(request: Request, exc: StarletteHTTPException):
    accept = request.headers.get("accept", "")
    if "text/html" in accept or "*/*" in accept or not accept:
        return HTMLResponse(content=_NOT_FOUND_HTML, status_code=404)
    detail = exc.detail if hasattr(exc, "detail") else "Not Found"
    return JSONResponse({"detail": detail}, status_code=404)

# --- Pages ---

@app.get("/", response_class=HTMLResponse)
async def home():
    return HTMLResponse(content=_HOME_HTML)


@app.get("/api-info", response_class=HTMLResponse)
async def api_info():
    return HTMLResponse(content=_API_HTML)

# --- Routes ---

@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing filename")
    data = await file.read()
    stored_name, size_bytes = save_file(data, file.filename, file.content_type or "application/octet-stream")
    file_id = stored_name.split(".")[0]

    with Session(engine) as session:
        rec = FileModel(
            id=file_id,
            original_name=file.filename,
            stored_name=stored_name,
            content_type=file.content_type or "application/octet-stream",
            size_bytes=size_bytes,
        )
        session.add(rec)
        session.commit()

    return {
        "id": file_id,
        "url": f"/{quote(stored_name)}",
        "size": size_bytes,
            "type": file.content_type,
        }

@app.get("/list")
def list_files():
    with Session(engine) as session:
        files = session.exec(select(FileModel).order_by(FileModel.created_at.desc())).all()
        return [
            {
                "id": f.id,
                "url": f"/{quote(f.stored_name)}",
                "name": f.original_name,
                "size": f.size_bytes,
                "created_at": f.created_at,
            } for f in files
        ]

@app.get("/{filename}")
def serve_file(filename: str):
    upload_root = Path(UPLOAD_DIR).resolve()
    try:
        path = (upload_root / filename).resolve()
        path.relative_to(upload_root)
    except (ValueError, RuntimeError):
        raise HTTPException(status_code=404, detail="Not found")
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Not found")
    return FileResponse(path)
