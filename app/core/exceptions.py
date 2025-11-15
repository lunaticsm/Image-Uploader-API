from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.templates import render_template

FRONTEND_INDEX = Path(__file__).resolve().parents[2] / "frontend" / "dist" / "index.html"
SPA_REDIRECT_HTML = """<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <title>Redirecting…</title>
    <meta http-equiv="refresh" content="0; url=/app/404" />
    <script>
      window.location.replace("/app/404");
    </script>
  </head>
  <body style="font-family: sans-serif; background: #05070f; color: #f8fafc; text-align: center; padding: 3rem;">
    <p>Routing you to the AlterBase CDN app…</p>
    <noscript>
      JavaScript is required for the dashboard. <a href="/app/404">Continue to the Not Found page</a>.
    </noscript>
  </body>
</html>
"""


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(404)
    async def not_found_handler(request: Request, exc: StarletteHTTPException):
        accept = request.headers.get("accept", "")
        detail = exc.detail if hasattr(exc, "detail") else "Not Found"
        if "application/json" in accept and "text/html" not in accept:
            return JSONResponse({"detail": detail}, status_code=404)
        if FRONTEND_INDEX.exists() and ("text/html" in accept or "application/json" not in accept):
            # Surface the React SPA's NotFound route while keeping a 404 status code
            return HTMLResponse(content=SPA_REDIRECT_HTML, status_code=404)
        detail_text = (
            detail
            if detail not in (None, "", "Not found", "Not Found")
            else "The resource you were looking for isn't here. It may have been removed or its link is outdated."
        )
        html = render_template("errors/404.html", {"detail": detail_text})
        return HTMLResponse(content=html, status_code=404)
