"""
MyCasa Pro API - Settings Routes
Typed settings management with validation.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime
import os

router = APIRouter(prefix="/settings", tags=["Settings"])


# ============ SCHEMAS ============

class SettingsUpdateRequest(BaseModel):
    """Generic settings update request"""
    updates: Dict[str, Any]


class SystemSettingsUpdate(BaseModel):
    """System settings update"""
    monthly_cost_cap: Optional[float] = None
    daily_spend_limit: Optional[float] = None
    approval_threshold: Optional[float] = None
    auto_refresh: Optional[bool] = None
    timezone: Optional[str] = None
    household_name: Optional[str] = None
    llm_provider: Optional[str] = None
    llm_base_url: Optional[str] = None
    llm_model: Optional[str] = None
    llm_api_key: Optional[str] = None
    llm_auth_type: Optional[str] = None


class AgentSettingsUpdate(BaseModel):
    """Agent settings update"""
    enabled: Optional[bool] = None
    # Additional fields added dynamically based on agent type


class NotificationSettingsUpdate(BaseModel):
    """Notification settings update"""
    in_app: Optional[bool] = None
    push: Optional[bool] = None
    email: Optional[bool] = None
    alert_email: Optional[str] = None
    whatsapp: Optional[bool] = None
    alert_phone: Optional[str] = None
    urgent_only: Optional[bool] = None
    daily_summary: Optional[bool] = None
    weekly_report: Optional[bool] = None


class SecuritySettingsUpdate(BaseModel):
    """Security agent settings update"""
    audit_logging: Optional[bool] = None
    threat_monitoring: Optional[bool] = None
    credential_rotation_days: Optional[int] = None


class MailSettingsUpdate(BaseModel):
    """Mail/Inbox agent settings update"""
    gmail_enabled: Optional[bool] = None
    whatsapp_enabled: Optional[bool] = None
    sync_interval_minutes: Optional[int] = None
    auto_triage: Optional[bool] = None
    allow_agent_replies: Optional[bool] = None
    allow_whatsapp_replies: Optional[bool] = None
    allow_email_replies: Optional[bool] = None
    whatsapp_allowlist: Optional[List[str]] = None
    whatsapp_contacts: Optional[List[Dict[str, Any]]] = None


# ============ ROUTES ============

@router.get("")
async def get_all_settings():
    """Get all settings"""
    from core.settings_typed import get_settings_store
    
    store = get_settings_store()
    settings = store.get()
    
    payload = settings.model_dump()
    if "system" in payload:
        payload["system"] = _mask_system_settings(payload["system"])
    return payload


@router.get("/system")
async def get_system_settings():
    """Get system settings"""
    from core.settings_typed import get_settings_store
    
    store = get_settings_store()
    settings = store.get()
    
    return _mask_system_settings(settings.system.model_dump())


@router.put("/system")
async def update_system_settings(update: SystemSettingsUpdate):
    """Update system settings"""
    from core.settings_typed import get_settings_store
    
    store = get_settings_store()
    settings = store.get()
    
    # Apply updates
    update_dict = update.model_dump(exclude_none=True)
    if "llm_api_key" in update_dict and update_dict["llm_api_key"] == "":
        update_dict["llm_api_key"] = None
    for key, value in update_dict.items():
        if hasattr(settings.system, key):
            setattr(settings.system, key, value)

    if update_dict.get("llm_auth_type") and update_dict.get("llm_auth_type") != "qwen-oauth":
        if hasattr(settings.system, "llm_oauth"):
            settings.system.llm_oauth = None
    if update_dict.get("llm_auth_type") == "qwen-oauth":
        update_dict["llm_api_key"] = None
        if hasattr(settings.system, "llm_api_key"):
            settings.system.llm_api_key = None
        try:
            from core.qwen_oauth import DEFAULT_QWEN_RESOURCE_URL, _normalize_resource_url
            from core.llm_client import QWEN_OAUTH_DEFAULT_MODEL, QWEN_OAUTH_FALLBACK_MODELS
            oauth = getattr(settings.system, "llm_oauth", None) or {}
            resource_url = (
                oauth.get("resource_url")
                or update_dict.get("llm_base_url")
                or settings.system.llm_base_url
                or DEFAULT_QWEN_RESOURCE_URL
            )
            normalized_url = _normalize_resource_url(resource_url)
            settings.system.llm_provider = "openai-compatible"
            settings.system.llm_base_url = normalized_url
            update_dict["llm_provider"] = "openai-compatible"
            update_dict["llm_base_url"] = normalized_url
            current_model = update_dict.get("llm_model") or settings.system.llm_model or ""
            if current_model not in QWEN_OAUTH_FALLBACK_MODELS:
                settings.system.llm_model = QWEN_OAUTH_DEFAULT_MODEL
                update_dict["llm_model"] = QWEN_OAUTH_DEFAULT_MODEL
        except Exception:
            pass
    
    store.save(settings)

    if any(k.startswith("llm_") for k in update_dict.keys()):
        if update_dict.get("llm_provider"):
            os.environ["LLM_PROVIDER"] = update_dict["llm_provider"]
        if update_dict.get("llm_base_url"):
            os.environ["LLM_BASE_URL"] = update_dict["llm_base_url"]
        if update_dict.get("llm_model"):
            os.environ["LLM_MODEL"] = update_dict["llm_model"]
        if update_dict.get("llm_auth_type"):
            os.environ["LLM_AUTH_TYPE"] = update_dict["llm_auth_type"]
        if "llm_api_key" in update_dict:
            if update_dict.get("llm_auth_type") == "qwen-oauth":
                os.environ.pop("LLM_API_KEY", None)
            elif update_dict["llm_api_key"]:
                os.environ["LLM_API_KEY"] = update_dict["llm_api_key"]
            else:
                os.environ.pop("LLM_API_KEY", None)
        from core.llm_client import reset_llm_client
        reset_llm_client()

    return {"success": True, "settings": _mask_system_settings(settings.system.model_dump())}


@router.get("/notifications")
async def get_notification_settings():
    """Get notification settings"""
    from core.settings_typed import get_settings_store

    store = get_settings_store()
    settings = store.get()
    return settings.notifications.model_dump()


@router.put("/notifications")
async def update_notification_settings(update: NotificationSettingsUpdate):
    """Update notification settings"""
    from core.settings_typed import get_settings_store

    store = get_settings_store()
    settings = store.get()

    update_dict = update.model_dump(exclude_none=True)
    for key, value in update_dict.items():
        if hasattr(settings.notifications, key):
            setattr(settings.notifications, key, value)

    store.save(settings)
    return {"success": True, "settings": settings.notifications.model_dump()}


@router.get("/agent/mail")
async def get_mail_agent_settings():
    """Get mail agent settings"""
    from core.settings_typed import get_settings_store

    store = get_settings_store()
    settings = store.get()
    return settings.agents.mail.model_dump()


@router.put("/agent/mail")
async def update_mail_agent_settings(update: MailSettingsUpdate):
    """Update mail agent settings"""
    from core.settings_typed import get_settings_store

    def normalize_phone(value: str) -> str:
        if not value:
            return ""
        digits = "".join(c for c in value if c.isdigit())
        return digits

    store = get_settings_store()
    settings = store.get()

    update_dict = update.model_dump(exclude_none=True)
    for key, value in update_dict.items():
        if hasattr(settings.agents.mail, key):
            setattr(settings.agents.mail, key, value)

    # Normalize allowlist/contacts if provided
    if update_dict.get("whatsapp_allowlist") is not None:
        normalized = [normalize_phone(v) for v in update_dict["whatsapp_allowlist"] or []]
        normalized = [v for v in normalized if v]
        settings.agents.mail.whatsapp_allowlist = sorted(set(normalized))

    if update_dict.get("whatsapp_contacts") is not None:
        contacts = []
        allowlist = set(settings.agents.mail.whatsapp_allowlist or [])
        for contact in update_dict["whatsapp_contacts"] or []:
            name = (contact or {}).get("name") or ""
            phone_raw = (contact or {}).get("phone") or ""
            phone = normalize_phone(phone_raw)
            if not phone:
                continue
            contacts.append({"name": name, "phone": phone})
            allowlist.add(phone)
        settings.agents.mail.whatsapp_contacts = contacts
        settings.agents.mail.whatsapp_allowlist = sorted(allowlist)

    store.save(settings)
    return {"success": True, "settings": settings.agents.mail.model_dump()}

@router.get("/agent/security")
async def get_security_agent_settings():
    """Get security agent settings"""
    from core.settings_typed import get_settings_store

    store = get_settings_store()
    settings = store.get()
    return settings.agents.security.model_dump()


@router.put("/agent/security")
async def update_security_agent_settings(update: SecuritySettingsUpdate):
    """Update security agent settings"""
    from core.settings_typed import get_settings_store

    store = get_settings_store()
    settings = store.get()

    update_dict = update.model_dump(exclude_none=True)
    for key, value in update_dict.items():
        if hasattr(settings.agents.security, key):
            setattr(settings.agents.security, key, value)

    store.save(settings)
    return {"success": True, "settings": settings.agents.security.model_dump()}


def _mask_system_settings(data: Dict[str, Any]) -> Dict[str, Any]:
    masked = dict(data)
    api_key = masked.get("llm_api_key")
    if masked.get("llm_auth_type") == "qwen-oauth":
        api_key = None
        masked["llm_api_key"] = None
    if api_key:
        masked["llm_api_key"] = f"{api_key[:4]}...{api_key[-4:]}"
        masked["llm_api_key_set"] = True
    else:
        masked["llm_api_key_set"] = False
    oauth = masked.pop("llm_oauth", None) or {}
    if oauth.get("access_token"):
        masked["llm_oauth_connected"] = True
        masked["llm_oauth_expires_at"] = oauth.get("expiry_date")
        masked["llm_oauth_resource_url"] = oauth.get("resource_url")
    else:
        masked["llm_oauth_connected"] = False
        masked["llm_oauth_expires_at"] = None
        masked["llm_oauth_resource_url"] = None
    # Runtime status (client initialized and ready)
    runtime = _get_llm_runtime_status()
    masked["llm_runtime_ready"] = runtime.get("ready")
    masked["llm_runtime_provider"] = runtime.get("provider")
    masked["llm_runtime_model"] = runtime.get("model")
    masked["llm_runtime_base_url"] = runtime.get("base_url")
    masked["llm_runtime_auth_type"] = runtime.get("auth_type")
    masked["llm_runtime_error"] = runtime.get("error")
    return masked


def _get_llm_runtime_status() -> Dict[str, Any]:
    try:
        from core.llm_client import get_llm_client
        llm = get_llm_client()
        ready = llm.is_available()
        error = None
        if not ready:
            if llm.auth_type == "qwen-oauth":
                error = "Qwen OAuth not connected."
            elif not llm.api_key:
                error = "Missing API key."
            else:
                error = "LLM client not initialized."
        return {
            "ready": bool(ready),
            "provider": llm.provider,
            "model": llm.model,
            "base_url": llm.base_url,
            "auth_type": llm.auth_type,
            "error": error,
        }
    except Exception as exc:
        return {
            "ready": False,
            "provider": None,
            "model": None,
            "base_url": None,
            "auth_type": None,
            "error": str(exc),
        }


@router.get("/agent/{agent_name}")
async def get_agent_settings(agent_name: str):
    """Get settings for a specific agent"""
    from core.settings_typed import get_settings_store
    
    store = get_settings_store()
    settings = store.get()
    
    agent_settings = getattr(settings.agents, agent_name, None)
    if agent_settings is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "AGENT_NOT_FOUND", "message": f"Unknown agent: {agent_name}"}
        )
    
    return agent_settings.model_dump()


@router.put("/agent/{agent_name}")
async def update_agent_settings(agent_name: str, updates: Dict[str, Any]):
    """Update settings for a specific agent"""
    from core.settings_typed import get_settings_store
    
    store = get_settings_store()
    settings = store.get()
    
    agent_settings = getattr(settings.agents, agent_name, None)
    if agent_settings is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "AGENT_NOT_FOUND", "message": f"Unknown agent: {agent_name}"}
        )
    
    # Get the current settings as dict
    current = agent_settings.model_dump()
    
    # Merge updates
    current.update(updates)
    
    # Validate and create new settings object
    try:
        # Get the appropriate settings class
        settings_class = type(agent_settings)
        new_agent_settings = settings_class(**current)
        
        # For finance, run additional validation
        if agent_name == "finance" and hasattr(new_agent_settings, 'validate_config'):
            errors = new_agent_settings.validate_config()
            if errors:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "code": "VALIDATION_ERROR",
                        "message": "Invalid configuration",
                        "errors": errors,
                    }
                )
        
        # Apply
        setattr(settings.agents, agent_name, new_agent_settings)
        store.save(settings)
        
        return {"success": True, "settings": new_agent_settings.model_dump()}
        
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "VALIDATION_ERROR",
                "message": str(e),
            }
        )


@router.get("/agents/enabled")
async def get_enabled_agents():
    """Get which agents are enabled"""
    from core.settings_typed import get_settings_store
    
    store = get_settings_store()
    settings = store.get()
    
    return settings.get_enabled_agents()


@router.put("/agents/enabled")
async def set_enabled_agents(enabled: Dict[str, bool]):
    """Bulk enable/disable agents"""
    from core.settings_typed import get_settings_store
    
    store = get_settings_store()
    settings = store.get()
    
    for agent_name, is_enabled in enabled.items():
        agent_settings = getattr(settings.agents, agent_name, None)
        if agent_settings:
            agent_settings.enabled = is_enabled
    
    store.save(settings)
    
    return {"success": True, "agents_enabled": settings.get_enabled_agents()}


# ============ COST CAP ENFORCEMENT ============

@router.get("/cost-status")
async def get_cost_status():
    """
    Get current cost status vs caps.
    Used by Finance agent to check before operations.
    """
    from core.settings_typed import get_settings_store
    
    store = get_settings_store()
    settings = store.get()
    
    # Get current costs from telemetry
    try:
        from api.routes.telemetry import _get_entries
        from datetime import datetime
        
        # Today's cost
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_entries = _get_entries(since=today_start, limit=10000)
        today_cost = sum(e.cost_estimate or 0 for e in today_entries)
        
        # Month's cost
        month_start = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        month_entries = _get_entries(since=month_start, limit=10000)
        month_cost = sum(e.cost_estimate or 0 for e in month_entries)
        
    except Exception as e:
        today_cost = 0
        month_cost = 0
    
    monthly_cap = settings.system.monthly_cost_cap
    daily_cap = settings.system.daily_spend_limit
    
    return {
        "today": {
            "cost": round(today_cost, 4),
            "cap": daily_cap,
            "remaining": round(daily_cap - today_cost, 4),
            "pct_used": round((today_cost / daily_cap) * 100, 1) if daily_cap > 0 else 0,
        },
        "month": {
            "cost": round(month_cost, 4),
            "cap": monthly_cap,
            "remaining": round(monthly_cap - month_cost, 4),
            "pct_used": round((month_cost / monthly_cap) * 100, 1) if monthly_cap > 0 else 0,
        },
        "alerts": {
            "approaching_daily_cap": today_cost > daily_cap * 0.8,
            "approaching_monthly_cap": month_cost > monthly_cap * 0.8,
            "exceeded_daily_cap": today_cost > daily_cap,
            "exceeded_monthly_cap": month_cost > monthly_cap,
        }
    }


@router.get("/finance/recommendation-config")
async def get_finance_recommendation_config():
    """
    Get Finance agent recommendation configuration.
    Includes style, framing, and disclaimer.
    """
    from core.settings_typed import get_settings_store
    
    store = get_settings_store()
    settings = store.get()
    finance = settings.agents.finance
    
    return {
        "recommendation_style": finance.recommendation_style.value,
        "risk_tolerance": finance.risk_tolerance.value,
        "investment_style": finance.investment_style.value,
        "target_annual_return": finance.target_annual_return,
        "max_single_position_pct": finance.max_single_position_pct,
        "min_holding_days": finance.min_holding_days,
        "framing": finance.get_recommendation_framing(),
        "disclaimer": finance.get_disclaimer(),
        "spending_caps": {
            "daily": finance.daily_spend_cap,
            "monthly": finance.monthly_spend_cap,
        },
        "primary_income_source": finance.primary_income_source,
    }


# ============ SETUP WIZARD ============

class WizardData(BaseModel):
    """
    Setup wizard data - per ARCHITECTURE.md spec.
    
    Steps:
    1. Welcome (Tenant Setup) - name, timezone, locale
    2. Income Source - primary funding source (required)
    3. Budgets - system cost cap, spend guardrails
    4. Connectors - Gmail, WhatsApp, etc. (optional)
    5. Notifications - how to receive alerts
    6. Complete - summary
    """
    # Step 1: Tenant Setup
    householdName: str = ""
    timezone: str = "America/Los_Angeles"
    locale: str = "en-US"
    
    # Step 2: Income Source (required)
    primaryIncomeSource: str = ""
    incomeFrequency: str = "monthly"
    
    # Step 3: Budgets
    monthlyBudget: float = 10000
    systemCostCap: float = 1000
    approvalThreshold: float = 500
    investmentStyle: str = "moderate"
    
    # Step 4: Connectors (optional)
    enableGmail: bool = False
    gmailAccount: str = ""
    googleAuthenticated: bool = False
    googleAccountEmail: str = ""
    googleCredentialsConfigured: bool = False
    enableWhatsapp: bool = False
    whatsappNumber: str = ""
    whatsappLinked: bool = False
    enableCalendar: bool = False
    whatsappContacts: List[Dict[str, Any]] = []
    
    # Step 4b: Contractors (optional)
    contractors: List[Dict[str, Any]] = []
    
    # Step 5: Notifications
    enableInApp: bool = True
    enablePush: bool = False
    enableEmail: bool = False
    alertEmail: str = ""


@router.get("/wizard")
async def get_wizard_settings():
    """
    Get current wizard settings.
    Returns the saved wizard data so users can see/edit their previous entries.
    """
    from core.settings_typed import get_settings_store
    
    try:
        store = get_settings_store()
        settings = store.get()
        
        # Build WizardData from current settings
        return {
            "success": True,
            "data": {
                # Step 1: Tenant Setup
                "householdName": settings.system.household_name,
                "timezone": settings.system.timezone,
                "locale": getattr(settings.system, 'locale', 'en-US'),
                
                # Step 2: Income Source
                "primaryIncomeSource": getattr(settings.agents.finance, 'primary_income_source', ''),
                "incomeFrequency": getattr(settings.agents.finance, 'income_frequency', 'monthly'),
                
                # Step 3: Budgets
                "monthlyBudget": settings.agents.finance.monthly_spend_cap,
                "systemCostCap": settings.system.monthly_cost_cap,
                "approvalThreshold": settings.system.approval_threshold,
                "investmentStyle": getattr(settings.agents.finance, 'investment_style', 'moderate'),
                
                # Step 4: Connectors (read from connector status if available)
                "enableGmail": False,
                "gmailAccount": "",
                "enableWhatsapp": False,
                "whatsappNumber": "",
                "whatsappContacts": [
                    {"id": f"wa_{idx}", "name": getattr(c, "name", ""), "phone": getattr(c, "phone", "")}
                    for idx, c in enumerate(getattr(settings.agents.mail, "whatsapp_contacts", []) or [])
                ],
                "enableCalendar": False,
                
                # Step 5: Notifications
                "enableInApp": settings.notifications.in_app,
                "enablePush": settings.notifications.push,
                "enableEmail": settings.notifications.email,
                "alertEmail": getattr(settings.notifications, 'alert_email', ''),
            }
        }
    except Exception as e:
        return {
            "success": False,
            "message": str(e),
            "data": None
        }


@router.post("/wizard")
async def save_wizard_settings(data: WizardData):
    """
    Save setup wizard settings.
    Called when the user completes the setup wizard.
    Per ARCHITECTURE.md spec:
    1. Tenant Setup (name, timezone, locale)
    2. Income Source (required)
    3. Budgets
    4. Connectors (optional)
    5. Notifications
    """
    from core.settings_typed import get_settings_store
    
    try:
        store = get_settings_store()
        settings = store.get()
        
        # Step 1: Tenant Setup
        settings.system.household_name = data.householdName
        settings.system.timezone = data.timezone
        if hasattr(settings.system, 'locale'):
            settings.system.locale = data.locale
        
        # Step 2: Income Source - store in finance settings
        if hasattr(settings.agents.finance, 'primary_income_source'):
            settings.agents.finance.primary_income_source = data.primaryIncomeSource
        if hasattr(settings.agents.finance, 'income_frequency'):
            settings.agents.finance.income_frequency = data.incomeFrequency
        
        # Step 3: Budgets
        settings.system.monthly_cost_cap = data.systemCostCap
        settings.system.approval_threshold = data.approvalThreshold
        settings.agents.finance.monthly_spend_cap = data.monthlyBudget
        settings.agents.finance.daily_spend_cap = data.monthlyBudget / 30

        # Step 4: Connectors
        settings.agents.mail.gmail_enabled = data.enableGmail
        settings.agents.mail.whatsapp_enabled = data.enableWhatsapp

        # Store WhatsApp contacts + allowlist
        def normalize_phone(value: str) -> str:
            return "".join(c for c in (value or "") if c.isdigit())

        contacts = []
        allowlist = set()
        for contact in data.whatsappContacts or []:
            name = (contact or {}).get("name") or ""
            phone = normalize_phone((contact or {}).get("phone") or "")
            if not phone:
                continue
            contacts.append({"name": name, "phone": phone})
            allowlist.add(phone)
        settings.agents.mail.whatsapp_contacts = contacts
        settings.agents.mail.whatsapp_allowlist = sorted(allowlist)
        
        # Map investment style
        style_map = {
            "conservative": "conservative",
            "moderate": "moderate", 
            "aggressive": "aggressive",
        }
        if data.investmentStyle in style_map:
            settings.agents.finance.investment_style = style_map[data.investmentStyle]
        
        # Note: Agent enable/disable is done in Settings page, not wizard (per spec)
        
        # Step 5: Notification settings
        settings.notifications.in_app = data.enableInApp
        settings.notifications.push = data.enablePush
        settings.notifications.email = data.enableEmail
        if data.alertEmail:
            settings.notifications.alert_email = data.alertEmail
        
        # Save
        store.save(settings)
        
        return {
            "success": True,
            "message": "Setup wizard settings saved successfully",
            "settings_applied": {
                "household": data.householdName,
                "timezone": data.timezone,
                "locale": data.locale,
                "income_source": data.primaryIncomeSource,
                "income_frequency": data.incomeFrequency,
                "monthly_budget": data.monthlyBudget,
                "system_cost_cap": data.systemCostCap,
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": str(e)
        }


@router.get("/wizard/status")
async def get_wizard_status():
    """
    Check if setup wizard has been completed.
    """
    from pathlib import Path
    import json
    
    # Check for setup marker file
    setup_file = Path(__file__).parent.parent.parent / "data" / "setup_complete.json"
    
    if setup_file.exists():
        try:
            data = json.loads(setup_file.read_text())
            return {
                "completed": True,
                "completed_at": data.get("completed_at"),
                "skipped": data.get("skipped", False)
            }
        except Exception:
            pass
    
    return {
        "completed": False,
        "completed_at": None,
        "skipped": False
    }


@router.post("/wizard/complete")
async def mark_wizard_complete(skipped: bool = False):
    """
    Mark the setup wizard as complete.
    """
    from pathlib import Path
    import json
    
    setup_file = Path(__file__).parent.parent.parent / "data" / "setup_complete.json"
    setup_file.parent.mkdir(parents=True, exist_ok=True)
    
    data = {
        "completed": True,
        "completed_at": datetime.now().isoformat(),
        "skipped": skipped
    }
    
    setup_file.write_text(json.dumps(data, indent=2))
    
    return {"success": True, "data": data}
