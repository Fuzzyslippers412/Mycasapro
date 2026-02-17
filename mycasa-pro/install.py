#!/usr/bin/env python3
"""
MyCasa Pro - Installation Script
One-click setup for the MyCasa Pro super skill
"""
import os
import sys
import json
import shutil
from pathlib import Path
from datetime import datetime


# ═══════════════════════════════════════════════════════════════════════════════
# Configuration
# ═══════════════════════════════════════════════════════════════════════════════

APP_NAME = "MyCasa Pro"
APP_VERSION = "1.0.0"
MIN_PYTHON = (3, 11)

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "mycasa_pro.db"


# ═══════════════════════════════════════════════════════════════════════════════
# Utilities
# ═══════════════════════════════════════════════════════════════════════════════

def print_banner():
    print("""
╔═══════════════════════════════════════════════════════════════════╗
║                                                                   ║
║   🏠  MyCasa Pro - AI-Driven Home Operating System               ║
║                                                                   ║
║   Installation Script v{version}                                     ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
    """.format(version=APP_VERSION))


def print_step(step: int, total: int, message: str):
    print(f"\n[{step}/{total}] {message}")


def print_success(message: str):
    print(f"    ✅ {message}")


def print_error(message: str):
    print(f"    ❌ {message}")


def print_warning(message: str):
    print(f"    ⚠️  {message}")


def print_info(message: str):
    print(f"    ℹ️  {message}")


# ═══════════════════════════════════════════════════════════════════════════════
# Validation
# ═══════════════════════════════════════════════════════════════════════════════

def check_python_version() -> bool:
    """Verify Python version meets minimum requirement"""
    current = sys.version_info[:2]
    if current < MIN_PYTHON:
        print_error(f"Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]}+ required (found {current[0]}.{current[1]})")
        return False
    print_success(f"Python {current[0]}.{current[1]} ✓")
    return True


def check_dependencies() -> bool:
    """Check required packages are available"""
    required = [
        ("sqlalchemy", "SQLAlchemy"),
        ("streamlit", "Streamlit"),
        ("fastapi", "FastAPI"),
    ]
    
    missing = []
    for module_name, display_name in required:
        try:
            __import__(module_name)
            print_success(f"{display_name} ✓")
        except ImportError:
            missing.append(display_name)
            print_error(f"{display_name} not found")
    
    if missing:
        print_info(f"Install missing: pip install {' '.join(m.lower() for m in missing)}")
        return False
    
    return True


def check_disk_space() -> bool:
    """Verify sufficient disk space"""
    try:
        import shutil
        total, used, free = shutil.disk_usage(BASE_DIR)
        free_mb = free // (1024 * 1024)
        
        if free_mb < 512:
            print_error(f"Insufficient disk space: {free_mb}MB free (need 512MB)")
            return False
        
        print_success(f"Disk space: {free_mb}MB available ✓")
        return True
    except Exception as e:
        print_warning(f"Could not check disk space: {e}")
        return True  # Non-fatal


# ═══════════════════════════════════════════════════════════════════════════════
# Setup
# ═══════════════════════════════════════════════════════════════════════════════

def create_data_directory() -> bool:
    """Create data directory for database and files"""
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        print_success(f"Data directory: {DATA_DIR}")
        
        # Create subdirectories
        (DATA_DIR / "backups").mkdir(exist_ok=True)
        (DATA_DIR / "exports").mkdir(exist_ok=True)
        (DATA_DIR / "uploads").mkdir(exist_ok=True)
        print_success("Subdirectories created")
        
        return True
    except Exception as e:
        print_error(f"Failed to create data directory: {e}")
        return False


def initialize_database() -> bool:
    """Initialize SQLite database with schema"""
    try:
        # Add parent to path for imports
        sys.path.insert(0, str(BASE_DIR))
        
        from database import init_db
        init_db()
        
        print_success(f"Database initialized: {DB_PATH}")
        return True
    except Exception as e:
        print_error(f"Database initialization failed: {e}")
        return False


def run_migrations() -> bool:
    """Run any pending database migrations"""
    try:
        # For now, init_db handles schema
        # Alembic migrations will be added later
        print_success("Migrations complete (schema up to date)")
        return True
    except Exception as e:
        print_error(f"Migration failed: {e}")
        return False


def seed_defaults() -> bool:
    """Seed default settings and data"""
    try:
        sys.path.insert(0, str(BASE_DIR))
        
        # Initialize settings registry (loads defaults)
        from core.settings import get_settings_registry
        registry = get_settings_registry()
        
        print_success("Default settings loaded")
        
        # Create default tenant
        from core.tenant import ensure_default_tenant
        tenant = ensure_default_tenant()
        print_success(f"Default tenant created: {tenant.name}")
        
        return True
    except Exception as e:
        print_error(f"Failed to seed defaults: {e}")
        return False


def register_with_clawdbot() -> bool:
    """Register skill with Clawdbot (if available)"""
    try:
        # Check if running under Clawdbot
        clawdbot_home = os.environ.get("CLAWDBOT_HOME")
        if not clawdbot_home:
            print_info("Clawdbot not detected (standalone mode)")
            return True
        
        # Register skill
        skills_dir = Path(clawdbot_home) / "skills"
        skill_link = skills_dir / "mycasa-pro"
        
        if not skill_link.exists():
            skill_link.symlink_to(BASE_DIR)
            print_success("Registered with Clawdbot")
        else:
            print_success("Already registered with Clawdbot")
        
        return True
    except Exception as e:
        print_warning(f"Could not register with Clawdbot: {e}")
        return True  # Non-fatal


def write_install_marker() -> bool:
    """Write installation marker file"""
    try:
        marker = DATA_DIR / ".installed"
        marker.write_text(json.dumps({
            "version": APP_VERSION,
            "installed_at": datetime.utcnow().isoformat(),
            "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        }, indent=2))
        return True
    except Exception:
        return True  # Non-fatal


# ═══════════════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════════════

def install() -> bool:
    """Run full installation"""
    print_banner()
    
    total_steps = 7
    
    # Step 1: Validate Python
    print_step(1, total_steps, "Checking Python version...")
    if not check_python_version():
        return False
    
    # Step 2: Check dependencies
    print_step(2, total_steps, "Checking dependencies...")
    if not check_dependencies():
        print_info("Run: pip install -r requirements.txt")
        return False
    
    # Step 3: Check disk space
    print_step(3, total_steps, "Checking disk space...")
    check_disk_space()  # Non-fatal
    
    # Step 4: Create data directory
    print_step(4, total_steps, "Creating data directory...")
    if not create_data_directory():
        return False
    
    # Step 5: Initialize database
    print_step(5, total_steps, "Initializing database...")
    if not initialize_database():
        return False
    
    # Step 6: Seed defaults
    print_step(6, total_steps, "Seeding default configuration...")
    if not seed_defaults():
        return False
    
    # Step 7: Register with Clawdbot
    print_step(7, total_steps, "Registering with Clawdbot...")
    register_with_clawdbot()
    
    # Write marker
    write_install_marker()
    
    # Success!
    print("""
╔═══════════════════════════════════════════════════════════════════╗
║                                                                   ║
║   ✅  Installation Complete!                                      ║
║                                                                   ║
║   Next steps:                                                     ║
║                                                                   ║
║   1. Start the backend (FastAPI):                                 ║
║      python -m uvicorn api.main:app --host 127.0.0.1 --port 6709   ║
║                                                                   ║
║   2. Start the frontend (Next.js):                                ║
║      cd frontend && npm install && npm run dev                    ║
║                                                                   ║
║   3. Open http://localhost:3000                                   ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
    """)
    
    return True


def uninstall() -> bool:
    """Remove MyCasa Pro data (keeps code)"""
    print_banner()
    print("\n⚠️  This will delete all MyCasa Pro data!\n")
    
    confirm = input("Type 'DELETE' to confirm: ")
    if confirm != "DELETE":
        print("Cancelled.")
        return False
    
    if DATA_DIR.exists():
        shutil.rmtree(DATA_DIR)
        print_success("Data directory removed")
    
    print("\n✅ Uninstall complete. Code remains intact.\n")
    return True


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="MyCasa Pro Installer")
    parser.add_argument("command", nargs="?", default="install", 
                       choices=["install", "uninstall", "check"])
    
    args = parser.parse_args()
    
    if args.command == "install":
        success = install()
        sys.exit(0 if success else 1)
    
    elif args.command == "uninstall":
        success = uninstall()
        sys.exit(0 if success else 1)
    
    elif args.command == "check":
        print_banner()
        print("\nRunning checks...\n")
        check_python_version()
        check_dependencies()
        check_disk_space()
        
        if DB_PATH.exists():
            print_success(f"Database exists: {DB_PATH}")
        else:
            print_warning("Database not initialized")
        
        sys.exit(0)


if __name__ == "__main__":
    main()
