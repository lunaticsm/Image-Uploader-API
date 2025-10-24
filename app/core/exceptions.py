from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.templates import render_template


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(404)
    async def not_found_handler(request: Request, exc: StarletteHTTPException):
        accept = request.headers.get("accept", "")
        detail = exc.detail if hasattr(exc, "detail") else "Not Found"
        if "application/json" in accept and "text/html" not in accept:
            return JSONResponse({"detail": detail}, status_code=404)
        detail_text = (
            detail
            if detail not in (None, "", "Not found", "Not Found")
            else "The resource you were looking for isn't here. It may have been removed or its link is outdated."
        )
        html = render_template("errors/404.html", {"detail": detail_text})
        return HTMLResponse(content=html, status_code=404)
