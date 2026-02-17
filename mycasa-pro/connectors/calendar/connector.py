"""
Google Calendar Connector for MyCasa Pro
OAuth2-based Calendar integration for scheduling.

This connector enables:
- Fetching calendar events
- Creating/updating events
- Managing multiple calendars
- Syncing to unified inbox for reminders
"""
import subprocess
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from pathlib import Path
import logging

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from connectors.base import (
    BaseConnector,
    ConnectorStatus,
    ConnectorCredentials,
    ConnectorEvent,
    SendError,
)


logger = logging.getLogger("mycasa.connectors.calendar")


class CalendarConnector(BaseConnector):
    """
    Google Calendar connector using the `gog` CLI tool.
    
    Leverages the gog CLI for Calendar operations, which handles OAuth
    and provides a clean interface to Google Calendar API.
    """
    
    connector_id = "google_calendar"
    display_name = "Google Calendar"
    description = "Connect to Google Calendar for scheduling and reminders"
    version = "1.0.0"
    icon = "📅"
    
    can_receive = True
    can_send = True  # Can create events
    requires_auth = True
    
    def __init__(self):
        super().__init__()
        self._gog_available = self._check_gog()
    
    def _check_gog(self) -> bool:
        """Check if gog CLI is available"""
        try:
            result = subprocess.run(
                ["gog", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False
    
    async def authenticate(self, tenant_id: str, credentials: Dict[str, Any]) -> ConnectorCredentials:
        """
        Authenticate with Google Calendar via gog CLI.
        """
        if not self._gog_available:
            raise Exception("gog CLI not installed. Install from: https://github.com/doitintl/gog")
        
        # Check if already authenticated
        try:
            result = subprocess.run(
                ["gog", "calendar", "list"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                return ConnectorCredentials(
                    connector_id=self.connector_id,
                    tenant_id=tenant_id,
                    credentials={"via": "gog_cli"}
                )
        except Exception as e:
            logger.error(f"Calendar auth check failed: {e}")
        
        raise Exception("Calendar not authenticated. Run: gog auth login")
    
    async def refresh_auth(self, tenant_id: str, credentials: ConnectorCredentials) -> ConnectorCredentials:
        """gog handles token refresh automatically"""
        return credentials
    
    async def health_check(self, tenant_id: str) -> ConnectorStatus:
        """Check Calendar connection health"""
        if not self._gog_available:
            self.set_status(tenant_id, ConnectorStatus.FAILED)
            return ConnectorStatus.FAILED
        
        try:
            result = subprocess.run(
                ["gog", "calendar", "list"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                self.set_status(tenant_id, ConnectorStatus.HEALTHY)
                return ConnectorStatus.HEALTHY
        except Exception as e:
            logger.warning(f"Calendar health check failed: {e}")
        
        self.set_status(tenant_id, ConnectorStatus.FAILED)
        return ConnectorStatus.FAILED
    
    async def sync(
        self,
        tenant_id: str,
        since: datetime = None,
        limit: int = 50
    ) -> List[ConnectorEvent]:
        """
        Sync upcoming calendar events.
        
        Returns ConnectorEvents for the unified inbox (upcoming reminders).
        """
        if not self._gog_available:
            return []
        
        events = []
        
        try:
            # Get events for next 7 days
            from_date = datetime.now().isoformat()
            to_date = (datetime.now() + timedelta(days=7)).isoformat()
            
            result = subprocess.run(
                [
                    "gog", "calendar", "events", "primary",
                    "--from", from_date,
                    "--to", to_date,
                    "--json"
                ],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                logger.error(f"Calendar sync failed: {result.stderr}")
                return []
            
            cal_events = json.loads(result.stdout) if result.stdout else []
            
            for evt in cal_events:
                # Parse start time
                start = evt.get("start", {})
                start_time = start.get("dateTime") or start.get("date")
                
                if start_time:
                    try:
                        timestamp = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
                    except ValueError:
                        timestamp = datetime.utcnow()
                else:
                    timestamp = datetime.utcnow()
                
                # Create ConnectorEvent
                event = ConnectorEvent(
                    event_id=f"calendar_{evt.get('id', '')}",
                    connector_id=self.connector_id,
                    tenant_id=tenant_id,
                    event_type="calendar",
                    source_id=evt.get("id", ""),
                    subject=evt.get("summary", "Untitled Event"),
                    body=evt.get("description", ""),
                    preview=evt.get("summary", "")[:100],
                    timestamp=timestamp,
                    domain="calendar",
                )
                
                # Check if event needs attention (within 24 hours)
                hours_until = (timestamp - datetime.now(timestamp.tzinfo or None)).total_seconds() / 3600
                if 0 < hours_until < 24:
                    event.urgency = "high"
                    event.is_actionable = True
                    event.required_action = "Upcoming event"
                
                events.append(event)
                
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Calendar response: {e}")
        except Exception as e:
            logger.error(f"Calendar sync error: {e}")
        
        return events
    
    async def send(
        self,
        tenant_id: str,
        payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create a calendar event.
        
        Payload format:
        {
            "title": "Event title",
            "start": "2026-01-30T10:00:00",
            "end": "2026-01-30T11:00:00",
            "description": "Event description" (optional),
            "location": "Event location" (optional),
            "attendees": ["email1@example.com"] (optional),
        }
        """
        if not self._gog_available:
            raise SendError("gog CLI not available")
        
        title = payload.get("title")
        start = payload.get("start")
        end = payload.get("end")
        
        if not title or not start or not end:
            raise SendError("Missing required fields: title, start, end")
        
        try:
            # Build gog calendar create command
            cmd = [
                "gog", "calendar", "event", "create", "primary",
                "--summary", title,
                "--start", start,
                "--end", end
            ]
            
            if payload.get("description"):
                cmd.extend(["--description", payload["description"]])
            if payload.get("location"):
                cmd.extend(["--location", payload["location"]])
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                return {
                    "success": True,
                    "title": title,
                    "start": start,
                    "end": end,
                }
            else:
                raise SendError(f"Failed to create event: {result.stderr}")
                
        except subprocess.TimeoutExpired:
            raise SendError("Event creation timed out")
        except Exception as e:
            raise SendError(f"Create failed: {e}")
    
    async def get_upcoming_events(
        self,
        tenant_id: str,
        days: int = 7,
        calendar_id: str = "primary"
    ) -> List[Dict[str, Any]]:
        """
        Get upcoming events as structured data.
        
        Args:
            tenant_id: Tenant ID
            days: Number of days ahead to look
            calendar_id: Calendar ID (default: primary)
        
        Returns:
            List of event dictionaries
        """
        if not self._gog_available:
            return []
        
        try:
            from_date = datetime.now().isoformat()
            to_date = (datetime.now() + timedelta(days=days)).isoformat()
            
            result = subprocess.run(
                [
                    "gog", "calendar", "events", calendar_id,
                    "--from", from_date,
                    "--to", to_date,
                    "--json"
                ],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                return json.loads(result.stdout) if result.stdout else []
        except Exception as e:
            logger.error(f"Failed to get upcoming events: {e}")
        
        return []
    
    def get_auth_schema(self) -> Dict[str, Any]:
        """Calendar OAuth schema"""
        return {
            "type": "object",
            "properties": {
                "note": {
                    "type": "string",
                    "description": "Google Calendar uses OAuth via gog CLI. Run 'gog auth login' to authenticate.",
                    "readOnly": True
                }
            },
            "description": "Calendar authentication is handled by the gog CLI. Run 'gog auth login' to start OAuth flow."
        }
    
    def get_settings_schema(self) -> Dict[str, Any]:
        """Calendar connector settings"""
        return {
            "type": "object",
            "properties": {
                "calendars": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Calendar IDs to sync (default: primary)",
                    "default": ["primary"]
                },
                "reminder_hours": {
                    "type": "integer",
                    "description": "Hours before event to create reminder",
                    "default": 24,
                    "minimum": 1
                },
                "sync_frequency_minutes": {
                    "type": "integer",
                    "description": "How often to sync events (minutes)",
                    "default": 30,
                    "minimum": 10
                }
            }
        }


# Singleton instance
_calendar_connector: Optional[CalendarConnector] = None


def get_calendar_connector() -> CalendarConnector:
    """Get singleton Calendar connector instance"""
    global _calendar_connector
    if _calendar_connector is None:
        _calendar_connector = CalendarConnector()
    return _calendar_connector
