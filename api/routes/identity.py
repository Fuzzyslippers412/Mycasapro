"""
Tenant Identity API
===================

Manage tenant identity files (SOUL/USER/SECURITY/TOOLS/HEARTBEAT/MEMORY).
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, Dict, Any

from auth.dependencies import require_auth
from config.settings import DEFAULT_TENANT_ID
from core.tenant_identity import TenantIdentityManager, TEMPLATE_DIR

router = APIRouter(prefix="/identity", tags=["Identity"])


class IdentityUpdate(BaseModel):
    soul: Optional[str] = None
    user: Optional[str] = None
    security: Optional[str] = None
    tools: Optional[str] = None
    heartbeat: Optional[str] = None
    memory: Optional[str] = None


class IdentityRestore(BaseModel):
    files: Optional[list[str]] = None


@router.get("")
async def get_identity(_: dict = Depends(require_auth)) -> Dict[str, Any]:
    """Get identity files and status for the current tenant."""
    manager = TenantIdentityManager(DEFAULT_TENANT_ID)
    manager.ensure_identity_structure()
    status = manager.get_identity_status()
    identity = {}
    try:
        identity = manager.load_identity_package()
    except Exception:
        # Return status even if required files are missing
        pass
    return {
        "tenant_id": DEFAULT_TENANT_ID,
        "status": status,
        "identity": identity,
    }


@router.put("")
async def update_identity(payload: IdentityUpdate, _: dict = Depends(require_auth)) -> Dict[str, Any]:
    """Update identity files for the current tenant."""
    manager = TenantIdentityManager(DEFAULT_TENANT_ID)
    manager.ensure_identity_structure()
    updates = payload.dict(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No identity fields provided")

    file_map = {
        "soul": "SOUL.md",
        "user": "USER.md",
        "security": "SECURITY.md",
        "tools": "TOOLS.md",
        "heartbeat": "HEARTBEAT.md",
        "memory": "MEMORY.md",
    }

    for key, content in updates.items():
        filename = file_map.get(key)
        if not filename:
            continue
        target = manager.tenant_dir / filename
        target.write_text(content or "", encoding="utf-8")

    status = manager.get_identity_status()
    identity = manager.load_identity_package()
    return {
        "tenant_id": DEFAULT_TENANT_ID,
        "status": status,
        "identity": identity,
    }


@router.get("/templates")
async def get_identity_templates(_: dict = Depends(require_auth)) -> Dict[str, Any]:
    """Get template contents for identity files."""
    file_map = {
        "soul": "SOUL.md",
        "user": "USER.md",
        "security": "SECURITY.md",
        "tools": "TOOLS.md",
        "heartbeat": "HEARTBEAT.md",
        "memory": "MEMORY.md",
    }
    templates: Dict[str, Any] = {}
    for key, filename in file_map.items():
        path = TEMPLATE_DIR / filename
        templates[key] = path.read_text(encoding="utf-8") if path.exists() else ""
    return {"templates": templates}


@router.post("/restore")
async def restore_identity_templates(
    payload: IdentityRestore, _: dict = Depends(require_auth)
) -> Dict[str, Any]:
    """Restore identity files from templates."""
    manager = TenantIdentityManager(DEFAULT_TENANT_ID)
    manager.ensure_identity_structure()

    file_map = {
        "soul": "SOUL.md",
        "user": "USER.md",
        "security": "SECURITY.md",
        "tools": "TOOLS.md",
        "heartbeat": "HEARTBEAT.md",
        "memory": "MEMORY.md",
    }
    targets = payload.files or list(file_map.keys())

    for key in targets:
        filename = file_map.get(key)
        if not filename:
            continue
        template_path = TEMPLATE_DIR / filename
        if template_path.exists():
            (manager.tenant_dir / filename).write_text(
                template_path.read_text(encoding="utf-8"),
                encoding="utf-8",
            )

    status = manager.get_identity_status()
    identity = manager.load_identity_package()
    return {
        "tenant_id": DEFAULT_TENANT_ID,
        "status": status,
        "identity": identity,
    }
