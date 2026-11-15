"""Database session and connection management for RERA Insight.

Supports PostgreSQL via psycopg/psycopg2/asyncpg or SQLite fallback.
Provides declarative Base, engine, session factory, and FastAPI get_db dependency.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session

from app.core.config import settings

Base = declarative_base()

# Resolve project root and default SQLite database path
PROJECT_ROOT = Path(__file__).resolve().parents[3]
default_sqlite_path = (PROJECT_ROOT / "rera_insight.db").resolve()
default_sqlite_url = f"sqlite:///{default_sqlite_path.as_posix()}"

# Determine database connection URL
db_url = settings.DATABASE_URL
connect_args = {}

if db_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}
    path_part = db_url.replace("sqlite:///", "")
    if not os.path.isabs(path_part):
        db_url = f"sqlite:///{(PROJECT_ROOT / path_part.lstrip('./')).resolve().as_posix()}"

# If URL is postgresql+asyncpg, convert to standard postgresql for sync engine
if "asyncpg" in db_url:
    db_url = db_url.replace("postgresql+asyncpg://", "postgresql://")

try:
    engine = create_engine(
        db_url,
        echo=(settings.LOG_LEVEL == "DEBUG"),
        pool_pre_ping=True,
        connect_args=connect_args,
    )
    # Test connection
    with engine.connect() as conn:
        pass
except Exception:
    # Graceful fallback to local SQLite database in project root
    engine = create_engine(
        default_sqlite_url,
        echo=(settings.LOG_LEVEL == "DEBUG"),
        pool_pre_ping=True,
        connect_args={"check_same_thread": False},
    )

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a database session and ensures it closes."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def init_db():
    """Create all tables in the database if they don't exist."""
    import app.models.models  # Ensure models are imported
    Base.metadata.create_all(bind=engine)
