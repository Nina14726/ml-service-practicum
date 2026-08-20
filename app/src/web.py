from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse
from fastapi.templating import Jinja2Templates

router = APIRouter()

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
static_dir = BASE_DIR / "static"


@router.get("/web")
def web_app(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@router.get("/web/static/style.css", include_in_schema=False)
def web_styles() -> FileResponse:
    return FileResponse(static_dir / "style.css", media_type="text/css")


@router.get("/web/static/app.js", include_in_schema=False)
def web_scripts() -> FileResponse:
    return FileResponse(static_dir / "app.js", media_type="application/javascript")


@router.get("/web/static/auth-ui.js", include_in_schema=False)
def auth_ui_scripts() -> FileResponse:
    return FileResponse(static_dir / "auth-ui.js", media_type="application/javascript")


@router.get("/web/static/clipboard.js", include_in_schema=False)
def clipboard_scripts() -> FileResponse:
    return FileResponse(static_dir / "clipboard.js", media_type="application/javascript")


@router.get("/web/static/history-ui.js", include_in_schema=False)
def history_ui_scripts() -> FileResponse:
    return FileResponse(static_dir / "history-ui.js", media_type="application/javascript")
