from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import get_settings
from app.core.logging import setup_logging
from app.database.session import check_db_connection

setup_logging()
settings = get_settings()

app = FastAPI(title=settings.app_name, debug=settings.debug)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router)


@app.get("/health")
def health():
    db_ok = False
    try:
        db_ok = check_db_connection()
    except Exception as exc:  # noqa: BLE001
        return {"status": "degraded", "database": False, "error": str(exc)}
    return {"status": "ok", "database": db_ok}


@app.get("/")
def root():
    return {"app": settings.app_name, "docs": "/docs"}
