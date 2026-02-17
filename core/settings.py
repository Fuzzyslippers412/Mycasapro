"""
MyCasa Pro - Settings Registry
Hierarchical settings with export/import support
"""
from typing import Any, Dict, Optional, List
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from .tenant import get_current_tenant_or_none


class SettingScope(Enum):
    """Settings hierarchy levels"""
    DEFAULT = "default"      # Code defaults (lowest priority)
    GLOBAL = "global"        # Infrastructure-wide
    MANAGER = "manager"      # Per-manager config
    CONNECTOR = "connector"  # Per-connector config
    TENANT = "tenant"        # Per-tenant overrides (highest priority)


@dataclass
class SettingDefinition:
    """Definition of a setting with metadata"""
    key: str
    default_value: Any
    description: str = ""
    scope: SettingScope = SettingScope.DEFAULT
    namespace: str = "global"
    
    # Validation
    value_type: type = str
    required: bool = False
    encrypted: bool = False
    
    # UI hints
    display_name: str = ""
    input_type: str = "text"  # text, number, select, toggle, json
    options: List[Any] = None
    min_value: float = None
    max_value: float = None
    
    def __post_init__(self):
        if not self.display_name:
            self.display_name = self.key.replace('_', ' ').title()
        if self.options is None:
            self.options = []


@dataclass
class SettingValue:
    """Stored setting value"""
    key: str
    value: Any
    scope: SettingScope
    namespace: str
    tenant_id: Optional[str] = None
    encrypted: bool = False
    version: int = 1
    updated_at: datetime = field(default_factory=datetime.utcnow)


class SettingsRegistry:
    """
    Central registry for all settings with hierarchical resolution.
    
    Priority (lowest to highest):
    1. Default (code) -> 2. Global -> 3. Manager/Connector -> 4. Tenant
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._definitions: Dict[str, SettingDefinition] = {}
            cls._instance._values: Dict[str, SettingValue] = {}
            cls._instance._register_defaults()
        return cls._instance
    
    def _register_defaults(self):
        """Register built-in default settings"""
        
        # ─── Global Settings ────────────────────────────────────────────
        self.define(SettingDefinition(
            key="app_name",
            default_value="MyCasa Pro",
            description="Application display name",
            scope=SettingScope.GLOBAL,
            namespace="global"
        ))
        
        self.define(SettingDefinition(
            key="app_version",
            default_value="1.0.0",
            description="Current version",
            scope=SettingScope.GLOBAL,
            namespace="global"
        ))
        
        self.define(SettingDefinition(
            key="multi_tenant_enabled",
            default_value=False,
            description="Enable multi-tenant mode",
            scope=SettingScope.GLOBAL,
            namespace="global",
            value_type=bool,
            input_type="toggle"
        ))
        
        # ─── Finance Manager Settings ───────────────────────────────────
        self.define(SettingDefinition(
            key="system_cost_budget",
            default_value=1000.0,
            description="Monthly system cost budget ($)",
            scope=SettingScope.MANAGER,
            namespace="finance",
            value_type=float,
            input_type="number",
            min_value=100,
            max_value=10000
        ))
        
        self.define(SettingDefinition(
            key="monthly_spend_limit",
            default_value=10000.0,
            description="Monthly household spend target ($)",
            scope=SettingScope.MANAGER,
            namespace="finance",
            value_type=float,
            input_type="number",
            min_value=1000
        ))
        
        self.define(SettingDefinition(
            key="daily_soft_cap",
            default_value=150.0,
            description="Daily spend soft cap ($)",
            scope=SettingScope.MANAGER,
            namespace="finance",
            value_type=float,
            input_type="number",
            min_value=10
        ))
        
        self.define(SettingDefinition(
            key="cost_warn_thresholds",
            default_value=[70, 85, 95],
            description="System cost warning thresholds (%)",
            scope=SettingScope.MANAGER,
            namespace="finance",
            value_type=list,
            input_type="json"
        ))
        
        # ─── Maintenance Manager Settings ───────────────────────────────
        self.define(SettingDefinition(
            key="task_reminder_days",
            default_value=3,
            description="Days before task due to send reminder",
            scope=SettingScope.MANAGER,
            namespace="maintenance",
            value_type=int,
            input_type="number",
            min_value=1,
            max_value=14
        ))
        
        # ─── Connector Settings (templates) ─────────────────────────────
        self.define(SettingDefinition(
            key="sync_interval_minutes",
            default_value=5,
            description="Sync interval in minutes",
            scope=SettingScope.CONNECTOR,
            namespace="connector_default",
            value_type=int,
            input_type="number",
            min_value=1,
            max_value=60
        ))
        
        self.define(SettingDefinition(
            key="retry_max_attempts",
            default_value=3,
            description="Max retry attempts on failure",
            scope=SettingScope.CONNECTOR,
            namespace="connector_default",
            value_type=int,
            input_type="number",
            min_value=1,
            max_value=10
        ))
    
    def define(self, definition: SettingDefinition) -> None:
        """Register a setting definition"""
        full_key = f"{definition.namespace}.{definition.key}"
        self._definitions[full_key] = definition
    
    def get_definition(self, key: str, namespace: str = "global") -> Optional[SettingDefinition]:
        """Get setting definition"""
        full_key = f"{namespace}.{key}"
        return self._definitions.get(full_key)
    
    def _make_value_key(self, key: str, namespace: str, scope: SettingScope, tenant_id: str = None) -> str:
        """Create storage key for a setting value"""
        parts = [scope.value, namespace, key]
        if tenant_id:
            parts.append(tenant_id)
        return ":".join(parts)
    
    def set(
        self, 
        key: str, 
        value: Any, 
        namespace: str = "global",
        scope: SettingScope = None,
        tenant_id: str = None
    ) -> None:
        """
        Set a setting value.
        
        If tenant_id is provided, creates tenant-specific override.
        If scope is not provided, uses the definition's default scope.
        """
        definition = self.get_definition(key, namespace)
        if definition and scope is None:
            scope = definition.scope
        if scope is None:
            scope = SettingScope.GLOBAL
        
        # Use current tenant if in tenant scope and not explicitly provided
        if tenant_id is None and scope == SettingScope.TENANT:
            tenant_id = get_current_tenant_or_none()
        
        value_key = self._make_value_key(key, namespace, scope, tenant_id)
        
        self._values[value_key] = SettingValue(
            key=key,
            value=value,
            scope=scope,
            namespace=namespace,
            tenant_id=tenant_id,
            encrypted=definition.encrypted if definition else False,
            version=(self._values[value_key].version + 1) if value_key in self._values else 1,
            updated_at=datetime.utcnow()
        )
    
    def get(
        self, 
        key: str, 
        namespace: str = "global",
        tenant_id: str = None,
        use_hierarchy: bool = True
    ) -> Any:
        """
        Get a setting value with hierarchical resolution.
        
        Resolution order (highest priority first):
        1. Tenant-specific value
        2. Scope-specific value (manager/connector)
        3. Global value
        4. Default value from definition
        """
        definition = self.get_definition(key, namespace)
        
        # Determine tenant
        if tenant_id is None:
            tenant_id = get_current_tenant_or_none()
        
        if use_hierarchy:
            # Try tenant-specific first
            if tenant_id:
                value_key = self._make_value_key(key, namespace, SettingScope.TENANT, tenant_id)
                if value_key in self._values:
                    return self._values[value_key].value
            
            # Try scope-specific (manager/connector)
            if definition:
                value_key = self._make_value_key(key, namespace, definition.scope)
                if value_key in self._values:
                    return self._values[value_key].value
            
            # Try global
            value_key = self._make_value_key(key, namespace, SettingScope.GLOBAL)
            if value_key in self._values:
                return self._values[value_key].value
        
        # Return default
        if definition:
            return definition.default_value
        
        return None
    
    def get_all(self, namespace: str = None, tenant_id: str = None) -> Dict[str, Any]:
        """Get all settings for a namespace (resolved)"""
        result = {}
        
        for full_key, definition in self._definitions.items():
            ns, key = full_key.split('.', 1)
            if namespace and ns != namespace:
                continue
            
            value = self.get(key, ns, tenant_id)
            if ns not in result:
                result[ns] = {}
            result[ns][key] = value
        
        return result
    
    def export_settings(self, tenant_id: str = None) -> Dict:
        """Export all settings to JSON-serializable dict"""
        export = {
            "version": self.get("app_version", "global"),
            "exported_at": datetime.utcnow().isoformat(),
            "tenant_id": tenant_id,
            "settings": {
                "global": {},
                "managers": {},
                "connectors": {}
            }
        }
        
        for full_key, definition in self._definitions.items():
            ns, key = full_key.split('.', 1)
            value = self.get(key, ns, tenant_id)
            
            if definition.scope == SettingScope.GLOBAL or definition.scope == SettingScope.DEFAULT:
                export["settings"]["global"][key] = value
            elif definition.scope == SettingScope.MANAGER:
                if ns not in export["settings"]["managers"]:
                    export["settings"]["managers"][ns] = {}
                export["settings"]["managers"][ns][key] = value
            elif definition.scope == SettingScope.CONNECTOR:
                if ns not in export["settings"]["connectors"]:
                    export["settings"]["connectors"][ns] = {}
                export["settings"]["connectors"][ns][key] = value
        
        return export
    
    def import_settings(self, data: Dict, tenant_id: str = None) -> Dict[str, Any]:
        """Import settings from exported dict"""
        imported = 0
        errors = []
        
        settings = data.get("settings", {})
        
        # Import global settings
        for key, value in settings.get("global", {}).items():
            try:
                self.set(key, value, "global", SettingScope.GLOBAL)
                imported += 1
            except Exception as e:
                errors.append(f"global.{key}: {str(e)}")
        
        # Import manager settings
        for ns, ns_settings in settings.get("managers", {}).items():
            for key, value in ns_settings.items():
                try:
                    self.set(key, value, ns, SettingScope.MANAGER, tenant_id)
                    imported += 1
                except Exception as e:
                    errors.append(f"{ns}.{key}: {str(e)}")
        
        # Import connector settings
        for ns, ns_settings in settings.get("connectors", {}).items():
            for key, value in ns_settings.items():
                try:
                    self.set(key, value, ns, SettingScope.CONNECTOR, tenant_id)
                    imported += 1
                except Exception as e:
                    errors.append(f"{ns}.{key}: {str(e)}")
        
        return {
            "imported": imported,
            "errors": errors,
            "success": len(errors) == 0
        }
    
    def get_schema(self, namespace: str = None) -> Dict:
        """Get JSON schema for settings (for UI generation)"""
        schema = {
            "type": "object",
            "properties": {},
            "namespaces": {}
        }
        
        for full_key, definition in self._definitions.items():
            ns, key = full_key.split('.', 1)
            if namespace and ns != namespace:
                continue
            
            if ns not in schema["namespaces"]:
                schema["namespaces"][ns] = {"properties": {}}
            
            prop = {
                "key": key,
                "title": definition.display_name,
                "description": definition.description,
                "type": definition.value_type.__name__,
                "default": definition.default_value,
                "inputType": definition.input_type,
                "required": definition.required,
                "encrypted": definition.encrypted
            }
            
            if definition.options:
                prop["enum"] = definition.options
            if definition.min_value is not None:
                prop["minimum"] = definition.min_value
            if definition.max_value is not None:
                prop["maximum"] = definition.max_value
            
            schema["namespaces"][ns]["properties"][key] = prop
        
        return schema


# ============ Module-level convenience functions ============

_registry: SettingsRegistry = None

def get_settings_registry() -> SettingsRegistry:
    """Get the global settings registry"""
    global _registry
    if _registry is None:
        _registry = SettingsRegistry()
    return _registry


def get_setting(key: str, namespace: str = "global", default: Any = None) -> Any:
    """Get a setting value"""
    value = get_settings_registry().get(key, namespace)
    return value if value is not None else default


def set_setting(key: str, value: Any, namespace: str = "global", **kwargs) -> None:
    """Set a setting value"""
    get_settings_registry().set(key, value, namespace, **kwargs)


def export_settings(tenant_id: str = None) -> Dict:
    """Export settings to dict"""
    return get_settings_registry().export_settings(tenant_id)


def import_settings(data: Dict, tenant_id: str = None) -> Dict:
    """Import settings from dict"""
    return get_settings_registry().import_settings(data, tenant_id)
