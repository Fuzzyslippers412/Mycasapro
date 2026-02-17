"""
MyCasa Pro API - Clawdbot/Moltbot Preferences Import
Import existing Clawdbot configuration into MyCasa Pro.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from pathlib import Path
import json

router = APIRouter(prefix="/clawdbot-import", tags=["Clawdbot Import"])

# Clawdbot config paths
CLAWDBOT_DIR = Path.home() / ".clawdbot"
CLAWDBOT_CONFIG = CLAWDBOT_DIR / "clawdbot.json"
CLAWD_WORKSPACE = Path.home() / "clawd"


class ClawdbotPreferences(BaseModel):
    """Importable preferences from Clawdbot"""
    detected: bool
    config_path: Optional[str] = None
    
    # UI
    assistant_name: Optional[str] = None
    response_prefix: Optional[str] = None
    
    # Model
    primary_model: Optional[str] = None
    available_models: List[str] = []
    
    # Contacts (from TOOLS.md)
    contacts: List[Dict[str, str]] = []
    
    # WhatsApp
    whatsapp_enabled: bool = False
    whatsapp_allow_from: List[str] = []
    
    # Skills
    enabled_skills: List[str] = []
    
    # Workspace
    workspace_path: Optional[str] = None
    
    # Timezone (from USER.md)
    timezone: Optional[str] = None


class ImportRequest(BaseModel):
    """What to import from Clawdbot"""
    import_contacts: bool = True
    import_model: bool = True
    import_skills: bool = False
    import_whatsapp: bool = True


class ImportResult(BaseModel):
    """Result of import operation"""
    success: bool
    imported: Dict[str, Any]
    warnings: List[str] = []


@router.get("/detect", response_model=ClawdbotPreferences)
async def detect_clawdbot():
    """
    Detect if Clawdbot is installed and return importable preferences.
    """
    prefs = ClawdbotPreferences(detected=False)
    
    if not CLAWDBOT_CONFIG.exists():
        return prefs
    
    prefs.detected = True
    prefs.config_path = str(CLAWDBOT_CONFIG)
    
    try:
        config = json.loads(CLAWDBOT_CONFIG.read_text())
        
        # UI settings
        ui = config.get("ui", {})
        prefs.assistant_name = ui.get("assistant", {}).get("name")
        
        # Messages
        messages = config.get("messages", {})
        prefs.response_prefix = messages.get("responsePrefix")
        
        # Model settings
        agents = config.get("agents", {}).get("defaults", {})
        model_config = agents.get("model", {})
        prefs.primary_model = model_config.get("primary")
        
        # Available models
        models = agents.get("models", {})
        prefs.available_models = list(models.keys())
        
        # WhatsApp
        whatsapp = config.get("channels", {}).get("whatsapp", {})
        prefs.whatsapp_enabled = config.get("plugins", {}).get("entries", {}).get("whatsapp", {}).get("enabled", False)
        prefs.whatsapp_allow_from = whatsapp.get("allowFrom", [])
        
        # Skills
        skills = config.get("skills", {}).get("entries", {})
        prefs.enabled_skills = list(skills.keys())
        
        # Workspace
        prefs.workspace_path = agents.get("workspace")
        
    except Exception as e:
        print(f"[CLAWDBOT_IMPORT] Error parsing config: {e}")
    
    # Parse contacts from TOOLS.md
    tools_path = CLAWD_WORKSPACE / "TOOLS.md"
    if tools_path.exists():
        try:
            content = tools_path.read_text()
            prefs.contacts = _parse_contacts(content)
        except Exception:
            pass
    
    # Parse timezone from USER.md
    user_path = CLAWD_WORKSPACE / "USER.md"
    if user_path.exists():
        try:
            content = user_path.read_text()
            for line in content.split("\n"):
                if "Timezone" in line and ":" in line:
                    prefs.timezone = line.split(":")[-1].strip()
                    break
        except Exception:
            pass
    
    return prefs


def _parse_contacts(tools_content: str) -> List[Dict[str, str]]:
    """Parse contacts table from TOOLS.md"""
    contacts = []
    in_contacts = False
    
    for line in tools_content.split("\n"):
        if "| Name" in line and "Phone" in line:
            in_contacts = True
            continue
        if in_contacts and line.startswith("|"):
            if "---" in line:
                continue
            parts = [p.strip() for p in line.split("|")]
            if len(parts) >= 5:
                name = parts[1]
                relation = parts[2]
                phone = parts[3]
                jid = parts[4] if len(parts) > 4 else ""
                if name and phone and name != "Name":
                    contacts.append({
                        "name": name,
                        "relation": relation,
                        "phone": phone,
                        "jid": jid
                    })
        elif in_contacts and not line.startswith("|"):
            in_contacts = False
    
    return contacts


@router.post("/import", response_model=ImportResult)
async def import_preferences(request: ImportRequest):
    """
    Import selected preferences from Clawdbot into MyCasa Pro.
    """
    prefs = await detect_clawdbot()
    
    if not prefs.detected:
        raise HTTPException(status_code=404, detail="Clawdbot not detected")
    
    imported = {}
    warnings = []
    
    # Import contacts
    if request.import_contacts and prefs.contacts:
        imported["contacts"] = prefs.contacts
        imported["contact_count"] = len(prefs.contacts)
    
    # Import model preference
    if request.import_model and prefs.primary_model:
        imported["primary_model"] = prefs.primary_model
        imported["available_models"] = prefs.available_models
    
    # Import WhatsApp settings
    if request.import_whatsapp and prefs.whatsapp_enabled:
        imported["whatsapp_enabled"] = True
        imported["whatsapp_contacts"] = prefs.whatsapp_allow_from
    
    # Import skills
    if request.import_skills and prefs.enabled_skills:
        imported["skills"] = prefs.enabled_skills
        warnings.append("Skills may need to be configured separately in MyCasa Pro")
    
    # Additional settings
    if prefs.timezone:
        imported["timezone"] = prefs.timezone
    
    if prefs.assistant_name:
        imported["assistant_name"] = prefs.assistant_name
    
    return ImportResult(
        success=True,
        imported=imported,
        warnings=warnings
    )


@router.get("/status")
async def get_import_status():
    """
    Quick check if Clawdbot is available for import.
    """
    return {
        "clawdbot_installed": CLAWDBOT_CONFIG.exists(),
        "workspace_exists": CLAWD_WORKSPACE.exists(),
        "config_path": str(CLAWDBOT_CONFIG) if CLAWDBOT_CONFIG.exists() else None,
    }
