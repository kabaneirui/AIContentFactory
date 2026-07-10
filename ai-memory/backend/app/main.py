import logging

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

import app.middleware.account_isolation  # noqa: F401 — register ORM isolation hooks
from app.api.router import api_router
from app.config import get_settings
from app.database import get_db
from app.logging_config import setup_logging
from app.middleware.account_isolation import AccountIsolationMiddleware

setup_logging()
logger = logging.getLogger(__name__)
settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="AI Memory — 个人账号内容大脑",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(AccountIsolationMiddleware)
app.include_router(api_router)


@app.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)) -> dict:
    db_status = "ok"
    try:
        await db.execute(text("SELECT 1"))
    except Exception as exc:
        logger.warning("Health check database probe failed: %s", exc)
        db_status = "error"

    return {
        "status": "ok" if db_status == "ok" else "degraded",
        "service": settings.app_name,
        "database": db_status,
    }
