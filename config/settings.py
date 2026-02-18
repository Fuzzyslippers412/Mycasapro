"""
MyCasa Pro Configuration
"""
import os
from pathlib import Path

# Tenant Configuration
# Default tenant ID - can be overridden via MYCASA_TENANT_ID env var
DEFAULT_TENANT_ID = os.environ.get("MYCASA_TENANT_ID", "tenkiang_household")

# Paths
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = Path(os.environ.get("MYCASA_DATA_DIR", str(BASE_DIR / "data")))
DATA_DIR.mkdir(exist_ok=True)
BACKUP_DIR = DATA_DIR / "backups"
BACKUP_DIR.mkdir(exist_ok=True)

# SecondBrain Vault Path (MyCasa-local by default)
LEGACY_VAULT_BASE = Path.home() / "moltbot" / "vaults"
VAULT_BASE = DATA_DIR / "vaults"
if os.environ.get("MYCASA_USE_LEGACY_VAULT") == "1":
    VAULT_BASE = LEGACY_VAULT_BASE
VAULT_BASE.mkdir(parents=True, exist_ok=True)
VAULT_PATH = VAULT_BASE / DEFAULT_TENANT_ID / "secondbrain"
VAULT_PATH.mkdir(parents=True, exist_ok=True)


def get_vault_path(tenant_id: str = None) -> Path:
    """Get the vault path for a tenant"""
    tid = tenant_id or DEFAULT_TENANT_ID
    path = VAULT_BASE / tid / "secondbrain"
    path.mkdir(parents=True, exist_ok=True)
    return path

# Database Configuration
# Set MYCASA_DATABASE_URL env var for PostgreSQL, otherwise uses SQLite
# PostgreSQL: postgresql://user:pass@localhost:5432/mycasa
# SQLite: sqlite:///path/to/mycasa.db
DATABASE_URL = os.environ.get(
    "MYCASA_DATABASE_URL",
    f"sqlite:///{DATA_DIR}/mycasa.db"
)

# State file for system on/off persistence
STATE_FILE = DATA_DIR / "system_state.json"

# Portfolio Configuration (from TOOLS.md - synced 2026-01-28)
PORTFOLIO = {
    "name": "Lamido Main",
    "holdings": [
        {"ticker": "GOOGL", "shares": 1500.32, "type": "Tech"},
        {"ticker": "NVDA", "shares": 2295.01, "type": "Tech/AI"},
        {"ticker": "OUNZ", "shares": 2775, "type": "Gold"},
        {"ticker": "IBIT", "shares": 2850, "type": "BTC ETF"},
        {"ticker": "FBTC", "shares": 2000, "type": "BTC ETF"},
        {"ticker": "BABA", "shares": 730, "type": "China Tech"},
        {"ticker": "SCHD", "shares": 1150, "type": "Dividend ETF"},
        {"ticker": "V", "shares": 150, "type": "Payments"},
        {"ticker": "GPN", "shares": 350, "type": "Payments"},
    ],
    "cash": {"JPM": 26939}  # Cash holdings
}

# Contacts (from TOOLS.md)
CONTACTS = {
    "erika": {"name": "Erika Tenkiang", "relation": "Wife", "phone": "+12675474854"},
    "jessie": {"name": "Jessie Tenkiang", "relation": "Mother", "phone": "+13027501982"},
    "rakia": {"name": "Rakia Balde", "relation": "House Assistant", "phone": "+33782826145"},
    "juan": {"name": "Juan", "relation": "Contractor", "phone": "+12534312046", "notes": "Spanish"},
}

# Alert Thresholds
ALERTS = {
    "position_move_pct": 5.0,
    "earnings_days_ahead": 14,
    "vix_threshold": 25,
    "bill_due_days_ahead": 7,
}

# Theme
THEME = {
    "primary_color": "#6366f1",  # Indigo
    "secondary_color": "#8b5cf6",  # Purple
    "success_color": "#22c55e",
    "warning_color": "#f59e0b",
    "danger_color": "#ef4444",
    "background": "#0f0f0f",
    "surface": "#1a1a1a",
    "card": "#242424",
    "text": "#ffffff",
    "text_muted": "#a1a1aa",
}
