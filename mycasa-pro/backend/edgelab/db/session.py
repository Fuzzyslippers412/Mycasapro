"""Database session management for Edge Lab - SQLite Compatible"""

import os
from pathlib import Path
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from .models import Base

# Use MyCasa's SQLite database
_default_db = Path(__file__).parent.parent.parent.parent / "data" / "mycasa.db"
DATABASE_URL = os.environ.get(
    "EDGELAB_DATABASE_URL",
    f"sqlite:///{_default_db}"
)

_engine = None
_SessionLocal = None


def get_engine():
    """Get or create database engine"""
    global _engine
    if _engine is None:
        _engine = create_engine(
            DATABASE_URL,
            connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
        )
    return _engine


def get_session_factory():
    """Get or create session factory"""
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(
            bind=get_engine(),
            autocommit=False,
            autoflush=False,
        )
    return _SessionLocal


@contextmanager
def get_session() -> Generator[Session, None, None]:
    """Context manager for database sessions"""
    SessionLocal = get_session_factory()
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db(drop_existing: bool = False):
    """Initialize EdgeLab tables in the database"""
    engine = get_engine()
    
    if drop_existing:
        # Only drop edgelab tables
        Base.metadata.drop_all(bind=engine)
    
    # Create all EdgeLab tables
    Base.metadata.create_all(bind=engine)
    
    return True
