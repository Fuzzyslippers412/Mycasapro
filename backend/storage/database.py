"""
MyCasa Pro Database Configuration
PostgreSQL for production, SQLite fallback for development
"""
import os
from pathlib import Path
from contextlib import contextmanager
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session

# Database configuration
# Use PostgreSQL in production, SQLite as fallback
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://localhost/mycasa_pro"  # Default to PostgreSQL
)

# Fallback to SQLite if PostgreSQL connection fails
USE_SQLITE_FALLBACK = False

# SQLite path (only used if falling back)
DATA_DIR = Path(__file__).parent.parent.parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
SQLITE_PATH = DATA_DIR / "mycasa.db"

# Try PostgreSQL first
try:
    from sqlalchemy import text
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,  # Verify connections before use
        pool_size=5,
        max_overflow=10,
        echo=False,
    )
    # Test connection
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    print(f"[DB] Connected to PostgreSQL: {DATABASE_URL.split('@')[-1] if '@' in DATABASE_URL else DATABASE_URL}")
except Exception as e:
    print(f"[DB] PostgreSQL connection failed: {e}")
    print(f"[DB] Falling back to SQLite: {SQLITE_PATH}")
    USE_SQLITE_FALLBACK = True
    DATABASE_URL = f"sqlite:///{SQLITE_PATH}"
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        echo=False,
    )
    
    # Enable SQLite optimizations
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()


# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@contextmanager
def get_db():
    """Get database session context manager"""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def get_db_session() -> Session:
    """Get a new database session (for dependency injection)"""
    return SessionLocal()


def init_db():
    """Initialize database tables"""
    from .models import Base
    Base.metadata.create_all(bind=engine, checkfirst=True)
    
    # Seed default SETTINGS ONLY (no fake tasks!)
    with get_db() as db:
        from .models import ManagerSettingsDB, BudgetPolicyDB
        
        # Create default manager settings if not exist
        managers = ["finance", "contractor", "maintenance", "mail", "janitor", "backup", "security"]
        for manager_id in managers:
            existing = db.query(ManagerSettingsDB).filter(ManagerSettingsDB.manager_id == manager_id).first()
            if not existing:
                db.add(ManagerSettingsDB(manager_id=manager_id, enabled=True, config="{}"))
        
        # Create default budgets if not exist
        budgets = [
            ("Monthly Spend", "monthly", 10000.0),
            ("Daily Spend", "daily", 150.0),
            ("System Cost", "system", 1000.0),
        ]
        for name, budget_type, limit in budgets:
            existing = db.query(BudgetPolicyDB).filter(BudgetPolicyDB.name == name).first()
            if not existing:
                db.add(BudgetPolicyDB(
                    name=name,
                    budget_type=budget_type,
                    limit_amount=limit,
                    current_spend=0,
                    is_active=True
                ))
        
        db.commit()
        print("[DB] Database initialized (no fake data seeded)")


def get_db_status() -> dict:
    """Get database status"""
    try:
        with get_db() as db:
            # Test query
            from sqlalchemy import text
            db.execute(text("SELECT 1"))
            
            # Get table counts
            from .models import (
                TaskDB, TransactionDB, EventDB, CostRecordDB,
                ContractorJobDB, InboxMessageDB
            )
            
            counts = {
                "tasks": db.query(TaskDB).count(),
                "transactions": db.query(TransactionDB).count(),
                "events": db.query(EventDB).count(),
                "cost_records": db.query(CostRecordDB).count(),
                "contractor_jobs": db.query(ContractorJobDB).count(),
                "inbox_messages": db.query(InboxMessageDB).count(),
            }
            
            db_type = "PostgreSQL" if not USE_SQLITE_FALLBACK else "SQLite"
            db_info = DATABASE_URL.split('@')[-1] if '@' in DATABASE_URL else DATABASE_URL
            
            return {
                "status": "connected",
                "database": db_type,
                "connection": db_info,
                "counts": counts
            }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }
