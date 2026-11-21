"""Database session and connection management for RERA Insight.

Supports PostgreSQL via psycopg/psycopg2/asyncpg or SQLite fallback.
Provides declarative Base, engine, session factory, and FastAPI get_db dependency.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker, Session

from app.core.config import settings

Base = declarative_base()

# Determine database connection URL
db_url = settings.DATABASE_URL

# If URL is postgresql+asyncpg, convert to standard postgresql for sync engine
if "asyncpg" in db_url:
    db_url = db_url.replace("postgresql+asyncpg://", "postgresql://")

# Connect strictly to PostgreSQL as the single source of truth
try:
    engine = create_engine(
        db_url,
        echo=(settings.LOG_LEVEL == "DEBUG"),
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
    )
    with engine.connect() as conn:
        conn.execute(text("SELECT 1;"))
except Exception as _db_err:
    import logging
    logging.getLogger("uvicorn.error").error(
        f"❌ FATAL: Could not connect to PostgreSQL database ({db_url}): {_db_err}. "
        f"Application requires PostgreSQL as the single source of truth."
    )
    raise RuntimeError(
        f"PostgreSQL connection failed: {_db_err}. "
        f"Please verify PostgreSQL is running and credentials in .env are correct."
    ) from _db_err

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
