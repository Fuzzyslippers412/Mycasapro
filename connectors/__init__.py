"""
MyCasa Pro - Connector Layer
Pluggable adapters for external services
"""
from .base import (
    BaseConnector,
    ConnectorStatus,
    ConnectorEvent,
    ConnectorCredentials,
    SendError,
)
from .registry import (
    ConnectorRegistry,
    get_connector_registry,
    register_connector,
    get_connector
)

# Import connectors for auto-registration
from .whatsapp.connector import WhatsAppConnector, get_whatsapp_connector
from .gmail.connector import GmailConnector, get_gmail_connector
from .calendar.connector import CalendarConnector, get_calendar_connector

__all__ = [
    'BaseConnector',
    'ConnectorStatus',
    'ConnectorEvent',
    'ConnectorCredentials',
    'SendError',
    'ConnectorRegistry',
    'get_connector_registry',
    'register_connector',
    'get_connector',
    'WhatsAppConnector',
    'get_whatsapp_connector',
    'GmailConnector',
    'get_gmail_connector',
    'CalendarConnector',
    'get_calendar_connector',
]
