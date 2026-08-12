from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.api.router import api_router
from app.core.config import get_settings
from app.core.logging import setup_logging
from app.core.rate_limit import limiter
from app.database.session import check_db_connection

setup_logging()
settings = get_settings()

app = FastAPI(title=settings.app_name, debug=settings.debug)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

_cors_kwargs: dict = {
    "allow_origins": settings.cors_origin_list,
    "allow_credentials": False,
    "allow_methods": ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    "allow_headers": ["Authorization", "Content-Type"],
}
if settings.cors_origin_regex:
    _cors_kwargs["allow_origin_regex"] = settings.cors_origin_regex

app.add_middleware(CORSMiddleware, **_cors_kwargs)
app.include_router(api_router)


@app.get("/health")
def health():
    db_ok = False
    try:
        db_ok = check_db_connection()
    except Exception as exc:  # noqa: BLE001
        return {"status": "degraded", "database": False, "error": str(exc)}
    return {"status": "ok", "database": db_ok}


def _frontend_dist() -> Path | None:
    if not settings.serve_frontend:
        return None
    path = Path(settings.frontend_dist)
    if not path.is_absolute():
        # Resolve relative to backend/ working directory or this package's parents
        candidates = [
            Path.cwd() / path,
            Path(__file__).resolve().parents[1] / path,  # backend/ + ../frontend/dist
            Path(__file__).resolve().parents[2] / "frontend" / "dist",  # repo root
        ]
        for c in candidates:
            if (c / "index.html").is_file():
                return c.resolve()
        return None
    return path if (path / "index.html").is_file() else None


_FRONTEND = _frontend_dist()


_NO_CACHE = {
    "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
    "Pragma": "no-cache",
}


def _spa_index() -> FileResponse:
    return FileResponse(_FRONTEND / "index.html", headers=_NO_CACHE)


@app.get("/")
def root():
    if _FRONTEND is not None:
        return _spa_index()
    return {"app": settings.app_name, "docs": "/docs"}


if _FRONTEND is not None:
    assets_dir = _FRONTEND / "assets"
    if assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="frontend-assets")

    _API_PREFIXES = (
        "api/",
        "ws/",
        "docs",
        "redoc",
        "openapi.json",
        "health",
        "assets/",
    )

    @app.get("/{full_path:path}")
    def spa_fallback(full_path: str):
        if full_path.startswith(_API_PREFIXES) or full_path in {
            "docs",
            "redoc",
            "openapi.json",
            "health",
        }:
            raise HTTPException(status_code=404)
        candidate = _FRONTEND / full_path
        if candidate.is_file():
            return FileResponse(candidate)
        return _spa_index()
