"""
MyCasa Pro - Connector Marketplace API
======================================

Endpoints for managing connectors (integrations).
Inspired by LobeHub's MCP Marketplace - easy discovery, install, configure.

Connectors:
- WhatsApp (messaging)
- Gmail (email via gog CLI)
- Calendar (Google Calendar via gog CLI)
- Bank Import (CSV/OFX transactions)
- SMS (future)
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from enum import Enum
import os

router = APIRouter(prefix="/connectors", tags=["Connectors"])


class ConnectorStatus(str, Enum):
    """Connector status states"""
    NOT_INSTALLED = "not_installed"
    INSTALLED = "installed"
    CONFIGURED = "configured"
    CONNECTED = "connected"
    ERROR = "error"


class ConnectorCategory(str, Enum):
    """Connector categories"""
    MESSAGING = "messaging"
    EMAIL = "email"
    CALENDAR = "calendar"
    FINANCE = "finance"
    SMART_HOME = "smart_home"
    SECURITY = "security"


class ConnectorInfo(BaseModel):
    """Information about a connector"""
    id: str
    name: str
    description: str
    category: ConnectorCategory
    icon: str  # Emoji or icon name
    status: ConnectorStatus
    config_required: List[str] = []
    config_values: Dict[str, Any] = {}
    health: Optional[str] = None
    last_sync: Optional[str] = None
    stats: Dict[str, Any] = {}


# ============ CONNECTOR REGISTRY ============

CONNECTOR_REGISTRY: Dict[str, Dict[str, Any]] = {
    "whatsapp": {
        "id": "whatsapp",
        "name": "WhatsApp",
        "description": "Send and receive WhatsApp messages via local wacli",
        "category": ConnectorCategory.MESSAGING,
        "icon": "📱",
        "config_required": [],  # Managed by local wacli auth
        "docs": "Uses wacli auth. Run: `wacli auth`",
    },
    "gmail": {
        "id": "gmail",
        "name": "Gmail",
        "description": "Read and send emails via Google Workspace (gog CLI)",
        "category": ConnectorCategory.EMAIL,
        "icon": "📧",
        "config_required": ["account"],
        "docs": "Requires gog CLI auth: `gog auth login`",
    },
    "calendar": {
        "id": "calendar",
        "name": "Google Calendar",
        "description": "View and manage calendar events (gog CLI)",
        "category": ConnectorCategory.CALENDAR,
        "icon": "📅",
        "config_required": ["calendar_id"],
        "docs": "Uses gog CLI. Auth shared with Gmail.",
    },
    "bank_import": {
        "id": "bank_import",
        "name": "Bank Import",
        "description": "Import transactions from CSV/OFX bank exports",
        "category": ConnectorCategory.FINANCE,
        "icon": "🏦",
        "config_required": ["import_path"],
        "docs": "Upload CSV/OFX files to import transactions.",
    },
    "apple_notes": {
        "id": "apple_notes",
        "name": "Apple Notes",
        "description": "Sync with Apple Notes via memo CLI",
        "category": ConnectorCategory.MESSAGING,
        "icon": "📝",
        "config_required": [],
        "docs": "Requires memo CLI: `brew install zeitlings/tap/memo`",
    },
    "home_assistant": {
        "id": "home_assistant",
        "name": "Home Assistant",
        "description": "Smart home control via Home Assistant API",
        "category": ConnectorCategory.SMART_HOME,
        "icon": "🏠",
        "config_required": ["ha_url", "ha_token"],
        "docs": "Requires Home Assistant long-lived access token.",
    },
    "ring": {
        "id": "ring",
        "name": "Ring Doorbell",
        "description": "Ring doorbell and camera integration",
        "category": ConnectorCategory.SECURITY,
        "icon": "🔔",
        "config_required": ["ring_email", "ring_password"],
        "docs": "Ring account credentials for API access.",
    },
}


# ============ HELPER FUNCTIONS ============

def _get_connector_status(connector_id: str) -> Dict[str, Any]:
    """Get the current status of a connector"""
    status_info = {
        "status": ConnectorStatus.NOT_INSTALLED,
        "health": None,
        "last_sync": None,
        "stats": {},
        "config_values": {},
    }
    
    if connector_id == "whatsapp":
        # Check WhatsApp via local wacli
        try:
            from connectors.whatsapp import WhatsAppConnector
            wa = WhatsAppConnector()
            contacts = wa.get_all_contacts()
            status_info["status"] = ConnectorStatus.CONNECTED
            status_info["health"] = "healthy"
            status_info["stats"] = {"contacts_loaded": len(contacts)}
            status_info["config_values"] = {"via": "wacli"}
        except Exception as e:
            status_info["status"] = ConnectorStatus.ERROR
            status_info["health"] = str(e)
    
    elif connector_id == "gmail":
        # Check if gog is configured
        import subprocess
        try:
            result = subprocess.run(
                ["gog", "gmail", "labels", "--max", "1"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                status_info["status"] = ConnectorStatus.CONNECTED
                status_info["health"] = "healthy"
                account = os.getenv("MYCASA_GMAIL_ACCOUNT")
                if account:
                    status_info["config_values"] = {"account": account}
            else:
                status_info["status"] = ConnectorStatus.INSTALLED
                status_info["health"] = "needs auth"
        except FileNotFoundError:
            status_info["status"] = ConnectorStatus.NOT_INSTALLED
        except Exception as e:
            status_info["status"] = ConnectorStatus.ERROR
            status_info["health"] = str(e)
    
    elif connector_id == "calendar":
        # Same as Gmail (shared auth)
        import subprocess
        try:
            result = subprocess.run(
                ["gog", "calendar", "events", "primary", "--max", "1"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                status_info["status"] = ConnectorStatus.CONNECTED
                status_info["health"] = "healthy"
            else:
                status_info["status"] = ConnectorStatus.INSTALLED
        except FileNotFoundError:
            status_info["status"] = ConnectorStatus.NOT_INSTALLED
        except Exception:
            status_info["status"] = ConnectorStatus.ERROR
    
    elif connector_id == "apple_notes":
        # Check if memo CLI exists
        import subprocess
        try:
            result = subprocess.run(["which", "memo"], capture_output=True, text=True)
            if result.returncode == 0:
                status_info["status"] = ConnectorStatus.CONNECTED
                status_info["health"] = "healthy"
            else:
                status_info["status"] = ConnectorStatus.NOT_INSTALLED
        except Exception:
            status_info["status"] = ConnectorStatus.NOT_INSTALLED
    
    else:
        # Default: not configured
        status_info["status"] = ConnectorStatus.NOT_INSTALLED
    
    return status_info


# ============ ENDPOINTS ============

@router.get("/marketplace")
async def list_connectors() -> Dict[str, Any]:
    """
    List all available connectors with their status.
    The connector marketplace - discover and manage integrations.
    """
    connectors = []
    
    for connector_id, info in CONNECTOR_REGISTRY.items():
        status_info = _get_connector_status(connector_id)
        
        connectors.append(ConnectorInfo(
            id=info["id"],
            name=info["name"],
            description=info["description"],
            category=info["category"],
            icon=info["icon"],
            status=status_info["status"],
            config_required=info["config_required"],
            config_values=status_info.get("config_values", {}),
            health=status_info.get("health"),
            last_sync=status_info.get("last_sync"),
            stats=status_info.get("stats", {}),
        ))
    
    # Group by category
    by_category = {}
    for c in connectors:
        cat = c.category.value
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(c.model_dump())
    
    # Count stats
    connected = sum(1 for c in connectors if c.status == ConnectorStatus.CONNECTED)
    installed = sum(1 for c in connectors if c.status in [ConnectorStatus.INSTALLED, ConnectorStatus.CONFIGURED, ConnectorStatus.CONNECTED])
    
    return {
        "connectors": [c.model_dump() for c in connectors],
        "by_category": by_category,
        "stats": {
            "total": len(connectors),
            "connected": connected,
            "installed": installed,
        }
    }


@router.get("/marketplace/{connector_id}")
async def get_connector(connector_id: str) -> Dict[str, Any]:
    """Get detailed info about a specific connector"""
    if connector_id not in CONNECTOR_REGISTRY:
        raise HTTPException(status_code=404, detail=f"Connector not found: {connector_id}")
    
    info = CONNECTOR_REGISTRY[connector_id]
    status_info = _get_connector_status(connector_id)
    
    return {
        "connector": ConnectorInfo(
            id=info["id"],
            name=info["name"],
            description=info["description"],
            category=info["category"],
            icon=info["icon"],
            status=status_info["status"],
            config_required=info["config_required"],
            config_values=status_info.get("config_values", {}),
            health=status_info.get("health"),
            last_sync=status_info.get("last_sync"),
            stats=status_info.get("stats", {}),
        ).model_dump(),
        "docs": info.get("docs", ""),
    }


@router.post("/marketplace/{connector_id}/configure")
async def configure_connector(
    connector_id: str,
    config: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Configure a connector with the provided settings.
    """
    if connector_id not in CONNECTOR_REGISTRY:
        raise HTTPException(status_code=404, detail=f"Connector not found: {connector_id}")
    
    info = CONNECTOR_REGISTRY[connector_id]
    
    # Validate required config
    missing = [f for f in info["config_required"] if f not in config]
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"Missing required config: {', '.join(missing)}"
        )
    
    # TODO: Actually save config to settings
    # For now, just acknowledge
    
    return {
        "success": True,
        "connector_id": connector_id,
        "message": f"{info['name']} configuration saved",
        "config_keys": list(config.keys()),
    }


@router.post("/marketplace/{connector_id}/test")
async def test_connector(connector_id: str) -> Dict[str, Any]:
    """
    Test a connector's connection.
    """
    if connector_id not in CONNECTOR_REGISTRY:
        raise HTTPException(status_code=404, detail=f"Connector not found: {connector_id}")
    
    status_info = _get_connector_status(connector_id)
    
    return {
        "connector_id": connector_id,
        "status": status_info["status"],
        "health": status_info.get("health"),
        "test_passed": status_info["status"] == ConnectorStatus.CONNECTED,
    }


@router.get("/health")
async def connectors_health() -> Dict[str, Any]:
    """
    Quick health check of all connectors.
    """
    health = {}
    
    for connector_id in CONNECTOR_REGISTRY:
        status_info = _get_connector_status(connector_id)
        health[connector_id] = {
            "status": status_info["status"],
            "healthy": status_info["status"] == ConnectorStatus.CONNECTED,
        }
    
    all_healthy = all(h["healthy"] for h in health.values())
    connected_count = sum(1 for h in health.values() if h["healthy"])
    
    return {
        "overall": "healthy" if connected_count > 0 else "no_connectors",
        "connected": connected_count,
        "total": len(health),
        "connectors": health,
    }


# ============ WHATSAPP SPECIFIC ENDPOINTS ============

@router.get("/whatsapp/status")
async def get_whatsapp_status():
    """Get WhatsApp connection status via wacli"""
    import subprocess
    allowlist_count = 0
    try:
        from core.settings_typed import get_settings_store
        settings = get_settings_store().get()
        allowlist = set()
        for number in getattr(settings.agents.mail, "whatsapp_allowlist", []) or []:
            digits = "".join(c for c in str(number) if c.isdigit())
            if digits:
                allowlist.add(digits)
        for contact in getattr(settings.agents.mail, "whatsapp_contacts", []) or []:
            try:
                phone = getattr(contact, "phone", "") or ""
            except Exception:
                phone = (contact or {}).get("phone") or ""
            digits = "".join(c for c in str(phone) if c.isdigit())
            if digits:
                allowlist.add(digits)
        allowlist_count = len(allowlist)
    except Exception:
        allowlist_count = 0
    
    try:
        result = subprocess.run(
            ["wacli", "auth", "status", "--json"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            import json
            status_data = json.loads(result.stdout)
            # wacli returns { success: true, data: { authenticated: true }, error: null }
            data = status_data.get("data", status_data)  # Handle both formats
            is_authenticated = data.get("authenticated", False)
            return {
                "connected": is_authenticated,
                "phone": data.get("phone", None),
                "status": "connected" if is_authenticated else "disconnected",
                "allowlist_count": allowlist_count,
            }
    except FileNotFoundError:
        return {
            "connected": False,
            "phone": None,
            "status": "not_installed",
            "allowlist_count": allowlist_count,
            "error": "wacli not installed. Run: npm install -g @nicholasoxford/wacli"
        }
    except Exception as e:
        pass
    
    return {
        "connected": False,
        "phone": None,
        "status": "unknown",
        "allowlist_count": allowlist_count,
        "error": "Could not check status"
    }


@router.get("/whatsapp/qr")
async def get_whatsapp_qr():
    """
    Generate WhatsApp QR code for linking.
    Checks wacli status first, provides manual instructions if needed.
    """
    import subprocess
    
    try:
        # First check if already authenticated via wacli
        status_result = subprocess.run(
            ["wacli", "auth", "status", "--json"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if status_result.returncode == 0:
            import json
            try:
                status_data = json.loads(status_result.stdout)
                # wacli returns { success: true, data: { authenticated: true }, error: null }
                data = status_data.get("data", status_data)  # Handle both formats
                if data.get("authenticated"):
                    return {
                        "success": True,
                        "already_connected": True,
                        "phone": data.get("phone"),
                        "message": "WhatsApp is already connected via wacli"
                    }
            except Exception as e:
                pass
        
        # wacli not authenticated - provide instructions
        # QR generation requires interactive terminal, so we give instructions
        return {
            "success": False,
            "needs_manual_setup": True,
            "error": "WhatsApp requires terminal setup",
            "instructions": [
                "1. Open Terminal",
                "2. Install wacli: npm install -g @nicholasoxford/wacli",
                "3. Run: wacli auth",
                "4. Scan QR code with WhatsApp",
                "5. Return here and click 'Check Again'"
            ],
            "hint": "Run 'npm install -g @nicholasoxford/wacli && wacli auth' in terminal"
        }
            
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": "Timeout checking status",
            "hint": "Try running 'wacli auth status' in terminal"
        }
    except FileNotFoundError:
        return {
            "success": False,
            "needs_manual_setup": True,
            "error": "wacli not installed",
            "instructions": [
                "1. Open Terminal",
                "2. Install wacli: npm install -g @nicholasoxford/wacli",
                "3. Run: wacli auth",
                "4. Scan QR code with WhatsApp",
                "5. Return here and click 'Check Again'"
            ],
            "hint": "Install with: npm install -g @nicholasoxford/wacli"
        }
