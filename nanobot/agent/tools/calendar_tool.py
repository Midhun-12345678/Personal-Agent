"""Calendar tool: Create, read, update and delete Google Calendar events."""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from loguru import logger

from nanobot.agent.tools.base import Tool


class CalendarTool(Tool):
    """Create, read, update and delete Google Calendar events on behalf of the user."""

    name = "calendar"
    description = "Create, read, update and delete Google Calendar events on behalf of the user"
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["list", "create", "delete"],
                "description": "Action to perform"
            },
            "days_ahead": {
                "type": "integer",
                "description": "Number of days ahead to list events (for action='list')",
                "minimum": 1,
                "maximum": 365
            },
            "title": {
                "type": "string",
                "description": "Event title (for action='create')"
            },
            "start": {
                "type": "string",
                "description": "Start time in ISO format (for action='create')"
            },
            "end": {
                "type": "string",
                "description": "End time in ISO format (for action='create')"
            },
            "description": {
                "type": "string",
                "description": "Event description (for action='create')"
            },
            "location": {
                "type": "string",
                "description": "Event location (for action='create')"
            },
            "event_id": {
                "type": "string",
                "description": "Event ID (for action='delete')"
            }
        },
        "required": ["action"]
    }

    SCOPES = ["https://www.googleapis.com/auth/calendar"]

    def __init__(self, user_workspace: Path):
        """Initialize Calendar tool.
        
        Args:
            user_workspace: User's workspace directory for credentials
        """
        self.user_workspace = Path(user_workspace)
        self.credentials_path = self.user_workspace / "integrations" / "calendar_credentials.json"
        self._service = None

    def _get_service(self):
        """Get authenticated Calendar service."""
        if self._service:
            return self._service

        if not self.credentials_path.exists():
            return None

        try:
            from google.oauth2.credentials import Credentials
            from googleapiclient.discovery import build

            creds = Credentials.from_authorized_user_file(
                str(self.credentials_path), self.SCOPES
            )
            
            # Refresh if expired
            if creds.expired and creds.refresh_token:
                from google.auth.transport.requests import Request
                creds.refresh(Request())
                # Save refreshed credentials
                self.credentials_path.write_text(creds.to_json())

            self._service = build("calendar", "v3", credentials=creds)
            return self._service

        except Exception as e:
            logger.error("Calendar auth failed: {}", e)
            return None

    async def execute(self, action: str, **kwargs: Any) -> str:
        service = self._get_service()
        
        if service is None:
            return json.dumps({
                "error": "Google Calendar not connected",
                "message": f"Please connect your Google Calendar first. Save your OAuth credentials to: {self.credentials_path}",
                "setup_instructions": [
                    "1. Go to Google Cloud Console and create OAuth credentials",
                    "2. Download the credentials and complete the OAuth flow",
                    "3. Save the resulting credentials.json to the path above"
                ]
            }, indent=2)

        try:
            if action == "list":
                return await self._list_events(service, **kwargs)
            elif action == "create":
                return await self._create_event(service, **kwargs)
            elif action == "delete":
                return await self._delete_event(service, **kwargs)
            else:
                return json.dumps({"error": f"Unknown action: {action}"})
        except Exception as e:
            logger.error("Calendar {} failed: {}", action, e)
            return json.dumps({"error": str(e)})

    async def _list_events(self, service, days_ahead: int = 7, **kwargs) -> str:
        """List upcoming events."""
        now = datetime.utcnow()
        time_min = now.isoformat() + "Z"
        time_max = (now + timedelta(days=days_ahead)).isoformat() + "Z"

        events_result = service.events().list(
            calendarId="primary",
            timeMin=time_min,
            timeMax=time_max,
            maxResults=50,
            singleEvents=True,
            orderBy="startTime"
        ).execute()

        events = events_result.get("items", [])
        
        if not events:
            return json.dumps({
                "events": [],
                "message": f"No events found in the next {days_ahead} days"
            })

        event_list = []
        for event in events:
            start = event["start"].get("dateTime", event["start"].get("date"))
            end = event["end"].get("dateTime", event["end"].get("date"))
            
            event_list.append({
                "id": event["id"],
                "title": event.get("summary", "(No title)"),
                "start": start,
                "end": end,
                "location": event.get("location", ""),
                "description": (event.get("description", "") or "")[:500]
            })

        return json.dumps({
            "events": event_list,
            "count": len(event_list),
            "period": f"Next {days_ahead} days"
        }, indent=2)

    async def _create_event(
        self,
        service,
        title: str = "",
        start: str = "",
        end: str = "",
        description: str = "",
        location: str = "",
        **kwargs
    ) -> str:
        """Create a calendar event."""
        if not title:
            return json.dumps({"error": "title is required for create action"})
        if not start:
            return json.dumps({"error": "start is required for create action"})
        if not end:
            return json.dumps({"error": "end is required for create action"})

        # Validate ISO format
        try:
            start_dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
            end_dt = datetime.fromisoformat(end.replace("Z", "+00:00"))
        except ValueError as e:
            return json.dumps({"error": f"Invalid datetime format: {e}"})

        # Check for time conflicts
        conflict = await self._check_time_conflict(service, start, end)
        if conflict:
            return json.dumps({
                "conflict": True,
                "error": f"CONFLICT: You already have \"{conflict['title']}\" from {conflict['start']} to {conflict['end']}.",
                "message": "This event overlaps with an existing event. Please choose a different time or confirm to create anyway.",
                "conflicting_event": conflict
            }, indent=2)

        event = {
            "summary": title,
            "start": {"dateTime": start, "timeZone": "UTC"},
            "end": {"dateTime": end, "timeZone": "UTC"},
        }

        if description:
            event["description"] = description
        if location:
            event["location"] = location

        result = service.events().insert(
            calendarId="primary",
            body=event
        ).execute()

        return json.dumps({
            "success": True,
            "event_id": result.get("id", ""),
            "link": result.get("htmlLink", ""),
            "message": f"Event '{title}' created successfully"
        }, indent=2)

    async def _check_time_conflict(self, service, start: str, end: str) -> dict | None:
        """
        Check if the proposed time conflicts with existing calendar events.

        Args:
            service: The Google Calendar service
            start: ISO format start time
            end: ISO format end time

        Returns:
            Dict with conflicting event details if found, None otherwise
        """
        try:
            # Query for events in the same time window
            events_result = service.events().list(
                calendarId="primary",
                timeMin=start,
                timeMax=end,
                singleEvents=True,
                orderBy="startTime"
            ).execute()

            events = events_result.get("items", [])

            if events:
                # Return the first conflicting event
                event = events[0]
                return {
                    "id": event.get("id"),
                    "title": event.get("summary", "(No title)"),
                    "start": event["start"].get("dateTime", event["start"].get("date")),
                    "end": event["end"].get("dateTime", event["end"].get("date")),
                }

            return None

        except Exception as e:
            logger.error("Error checking calendar conflicts: {}", e)
            return None

    async def _delete_event(self, service, event_id: str = "", **kwargs) -> str:
        """Delete a calendar event."""
        if not event_id:
            return json.dumps({"error": "event_id is required for delete action"})

        service.events().delete(
            calendarId="primary",
            eventId=event_id
        ).execute()

        return json.dumps({
            "success": True,
            "message": f"Event {event_id} deleted successfully"
        }, indent=2)
