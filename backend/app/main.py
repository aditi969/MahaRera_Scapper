"""RERA INSIGHT - Maharashtra Real Estate Data Intelligence Platform.

Main FastAPI application entrypoint.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Ensure both project root and backend directory are on sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = Path(__file__).resolve().parents[1]

for p in (str(PROJECT_ROOT), str(BACKEND_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.api.routes.analytics import router as analytics_router
from app.api.routes.data_quality import router as data_quality_router
from app.api.routes.projects import router as projects_router
from app.api.routes.scraper import router as scraper_router
from app.api.routes.websocket import router as ws_router
from app.core.config import settings
from app.database.session import get_db, init_db
from app.models.models import Project


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database tables on startup
    init_db()
    yield


app = FastAPI(
    title="RERA INSIGHT",
    description="Maharashtra Real Estate Data Intelligence Platform API",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ],
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1)(:[0-9]+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(projects_router, prefix="/api")
app.include_router(analytics_router, prefix="/api")
app.include_router(data_quality_router, prefix="/api")
app.include_router(scraper_router, prefix="/api")
app.include_router(ws_router)


@app.get("/api/health", tags=["System"])
def health_check(db: Session = Depends(get_db)):
    """System health check and database connectivity verification."""
    total_projects = db.query(Project).count()
    return {
        "status": "healthy",
        "app_name": "RERA Insight",
        "version": "1.0.0",
        "database": "connected",
        "total_projects": total_projects,
        "timestamp": datetime.now().isoformat(),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)

