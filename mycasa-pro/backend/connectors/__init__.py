"""
MyCasa Pro Connectors
Gmail and WhatsApp integration (stubs + real implementations)
"""
from .gmail import GmailConnector
from .whatsapp import WhatsAppConnector

# Global connector instances
gmail_connector = GmailConnector()
whatsapp_connector = WhatsAppConnector()
