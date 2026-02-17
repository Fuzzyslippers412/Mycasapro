"""
MyCasa Pro - Connector Registry
Discovers, registers, and manages connector plugins
"""
from typing import Dict, List, Optional, Type
import importlib
import logging

from .base import BaseConnector


logger = logging.getLogger("mycasa.connectors.registry")


class ConnectorRegistry:
    """
    Central registry for all available connectors.
    Handles discovery, registration, and lifecycle management.
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._connectors: Dict[str, BaseConnector] = {}
            cls._instance._connector_classes: Dict[str, Type[BaseConnector]] = {}
            cls._instance._enabled: Dict[str, Dict[str, bool]] = {}  # tenant_id -> connector_id -> enabled
        return cls._instance
    
    def register_class(self, connector_class: Type[BaseConnector]) -> None:
        """
        Register a connector class.
        Instance will be created lazily on first use.
        """
        connector_id = connector_class.connector_id
        if connector_id in self._connector_classes:
            logger.warning(f"Overwriting connector class: {connector_id}")
        
        self._connector_classes[connector_id] = connector_class
        logger.info(f"Registered connector class: {connector_id}")
    
    def register(self, connector: BaseConnector) -> None:
        """Register a connector instance"""
        connector_id = connector.connector_id
        if connector_id in self._connectors:
            logger.warning(f"Overwriting connector: {connector_id}")
        
        self._connectors[connector_id] = connector
        logger.info(f"Registered connector: {connector_id} v{connector.version}")
    
    def get(self, connector_id: str) -> Optional[BaseConnector]:
        """
        Get a connector instance by ID.
        Creates instance from class if not already instantiated.
        """
        if connector_id in self._connectors:
            return self._connectors[connector_id]
        
        if connector_id in self._connector_classes:
            # Lazy instantiation
            instance = self._connector_classes[connector_id]()
            self._connectors[connector_id] = instance
            return instance
        
        return None
    
    def get_all(self) -> List[BaseConnector]:
        """Get all registered connector instances"""
        # Ensure all classes are instantiated
        for connector_id in self._connector_classes:
            if connector_id not in self._connectors:
                self._connectors[connector_id] = self._connector_classes[connector_id]()
        
        return list(self._connectors.values())
    
    def list_available(self) -> List[Dict]:
        """List all available connectors with info"""
        connectors = []
        
        # From registered instances
        for connector in self._connectors.values():
            connectors.append(connector.get_info())
        
        # From registered classes not yet instantiated
        for connector_id, cls in self._connector_classes.items():
            if connector_id not in self._connectors:
                connectors.append({
                    "id": cls.connector_id,
                    "name": cls.display_name,
                    "description": cls.description,
                    "version": cls.version,
                    "icon": cls.icon,
                    "capabilities": {
                        "receive": cls.can_receive,
                        "send": cls.can_send,
                        "requires_auth": cls.requires_auth
                    }
                })
        
        return connectors
    
    def is_enabled(self, connector_id: str, tenant_id: str) -> bool:
        """Check if connector is enabled for a tenant"""
        tenant_enabled = self._enabled.get(tenant_id, {})
        return tenant_enabled.get(connector_id, False)
    
    async def enable(self, connector_id: str, tenant_id: str) -> bool:
        """Enable a connector for a tenant"""
        connector = self.get(connector_id)
        if not connector:
            logger.error(f"Connector not found: {connector_id}")
            return False
        
        if tenant_id not in self._enabled:
            self._enabled[tenant_id] = {}
        
        self._enabled[tenant_id][connector_id] = True
        
        try:
            await connector.on_enable(tenant_id)
        except Exception as e:
            logger.error(f"Error enabling connector {connector_id}: {e}")
        
        return True
    
    async def disable(self, connector_id: str, tenant_id: str) -> bool:
        """Disable a connector for a tenant"""
        connector = self.get(connector_id)
        if not connector:
            return False
        
        if tenant_id in self._enabled:
            self._enabled[tenant_id][connector_id] = False
        
        try:
            await connector.on_disable(tenant_id)
        except Exception as e:
            logger.error(f"Error disabling connector {connector_id}: {e}")
        
        return True
    
    def get_enabled_for_tenant(self, tenant_id: str) -> List[BaseConnector]:
        """Get all enabled connectors for a tenant"""
        enabled = []
        tenant_enabled = self._enabled.get(tenant_id, {})
        
        for connector_id, is_enabled in tenant_enabled.items():
            if is_enabled:
                connector = self.get(connector_id)
                if connector:
                    enabled.append(connector)
        
        return enabled
    
    def get_status_all(self, tenant_id: str) -> Dict[str, Dict]:
        """Get status of all connectors for a tenant"""
        status = {}
        
        for connector in self.get_all():
            connector_status = connector.get_status(tenant_id)
            last_sync = connector.get_last_sync(tenant_id)
            
            status[connector.connector_id] = {
                "info": connector.get_info(),
                "enabled": self.is_enabled(connector.connector_id, tenant_id),
                "status": connector_status.value,
                "last_sync": last_sync.isoformat() if last_sync else None
            }
        
        return status
    
    def discover_connectors(self, package_path: str = "connectors") -> int:
        """
        Auto-discover and register connectors from a package.
        
        Looks for modules with a `Connector` class that extends BaseConnector.
        
        Returns:
            Number of connectors discovered
        """
        discovered = 0
        
        # Built-in connectors to look for
        builtin_connectors = [
            "gmail",
            "whatsapp", 
            "calendar",
            "bank_import",
            "sms"
        ]
        
        for connector_name in builtin_connectors:
            try:
                module = importlib.import_module(f"{package_path}.{connector_name}")
                
                # Look for Connector class
                if hasattr(module, 'Connector'):
                    connector_class = getattr(module, 'Connector')
                    if issubclass(connector_class, BaseConnector):
                        self.register_class(connector_class)
                        discovered += 1
                        logger.info(f"Discovered connector: {connector_name}")
                
            except ImportError as e:
                logger.debug(f"Connector module not found: {connector_name} ({e})")
            except Exception as e:
                logger.warning(f"Error loading connector {connector_name}: {e}")
        
        return discovered


# ============ Module-level functions ============

_registry: ConnectorRegistry = None


def get_connector_registry() -> ConnectorRegistry:
    """Get the global connector registry"""
    global _registry
    if _registry is None:
        _registry = ConnectorRegistry()
    return _registry


def register_connector(connector: BaseConnector) -> None:
    """Register a connector with the global registry"""
    get_connector_registry().register(connector)


def get_connector(connector_id: str) -> Optional[BaseConnector]:
    """Get a connector by ID from the global registry"""
    return get_connector_registry().get(connector_id)


def list_connectors() -> List[Dict]:
    """List all available connectors"""
    return get_connector_registry().list_available()
