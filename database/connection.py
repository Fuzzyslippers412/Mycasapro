"""
Database connection utilities for FastAPI dependencies.
"""
from typing import AsyncGenerator

from sqlalchemy.orm import Session

from database import get_session


async def get_db() -> AsyncGenerator[Session, None]:
    """FastAPI dependency that provides a database session."""
    db = get_session()
    try:
        yield db
    finally:
        db.close()
