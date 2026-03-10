"""Gmail tool: Read, search, send, and draft emails via Gmail API."""

import base64
import json
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any

from loguru import logger

from nanobot.agent.tools.base import Tool


class GmailTool(Tool):
    """Read, search, send, and draft emails via Gmail on behalf of the user."""

    name = "gmail"
    description = "Read, search, send, and draft emails via Gmail on behalf of the user"
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["search", "read", "send", "draft"],
                "description": "Action to perform"
            },
            "query": {
                "type": "string",
                "description": "Search query (for action='search')"
            },
            "max_results": {
                "type": "integer",
                "description": "Maximum results to return (for action='search')",
                "minimum": 1,
                "maximum": 20
            },
            "email_id": {
                "type": "string",
                "description": "Email ID to read (for action='read')"
            },
            "to": {
                "type": "string",
                "description": "Recipient email address (for action='send' or 'draft')"
            },
            "subject": {
                "type": "string",
                "description": "Email subject (for action='send' or 'draft')"
            },
            "body": {
                "type": "string",
                "description": "Email body content (for action='send' or 'draft')"
            }
        },
        "required": ["action"]
    }

    SCOPES = [
        "https://www.googleapis.com/auth/gmail.readonly",
        "https://www.googleapis.com/auth/gmail.send",
        "https://www.googleapis.com/auth/gmail.compose",
    ]

    def __init__(self, user_workspace: Path):
        """Initialize Gmail tool.
        
        Args:
            user_workspace: User's workspace directory for credentials
        """
        self.user_workspace = Path(user_workspace)
        self.credentials_path = self.user_workspace / "integrations" / "gmail_credentials.json"
        self._service = None

    def _get_service(self):
        """Get authenticated Gmail service."""
        if self._service:
            return self._service

        logger.debug(f"GmailTool checking credentials at: {self.credentials_path}")
        logger.debug(f"Credentials file exists: {self.credentials_path.exists()}")
        logger.debug(f"User workspace: {self.user_workspace}")
        
        if not self.credentials_path.exists():
            logger.warning(f"Gmail credentials not found at {self.credentials_path}")
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

            self._service = build("gmail", "v1", credentials=creds)
            return self._service

        except Exception as e:
            logger.error("Gmail auth failed: {}", e)
            return None

    async def execute(self, action: str, **kwargs: Any) -> str:
        service = self._get_service()
        
        if service is None:
            return json.dumps({
                "error": "Gmail not connected",
                "message": f"Please connect your Gmail account first. Save your OAuth credentials to: {self.credentials_path}",
                "setup_instructions": [
                    "1. Go to Google Cloud Console and create OAuth credentials",
                    "2. Download the credentials and complete the OAuth flow",
                    "3. Save the resulting credentials.json to the path above"
                ]
            }, indent=2)

        try:
            if action == "search":
                return await self._search(service, **kwargs)
            elif action == "read":
                return await self._read(service, **kwargs)
            elif action == "send":
                return await self._send(service, **kwargs)
            elif action == "draft":
                return await self._draft(service, **kwargs)
            else:
                return json.dumps({"error": f"Unknown action: {action}"})
        except Exception as e:
            logger.error("Gmail {} failed: {}", action, e)
            return json.dumps({"error": str(e)})

    async def _search(self, service, query: str = "", max_results: int = 5, **kwargs) -> str:
        """Search emails."""
        if not query:
            return json.dumps({"error": "query is required for search action"})

        results = service.users().messages().list(
            userId="me",
            q=query,
            maxResults=max_results
        ).execute()

        messages = results.get("messages", [])
        if not messages:
            return json.dumps({"results": [], "message": "No emails found"})

        email_list = []
        for msg in messages:
            msg_data = service.users().messages().get(
                userId="me",
                id=msg["id"],
                format="metadata",
                metadataHeaders=["Subject", "From", "Date"]
            ).execute()

            headers = {h["name"]: h["value"] for h in msg_data.get("payload", {}).get("headers", [])}
            email_list.append({
                "id": msg["id"],
                "subject": headers.get("Subject", "(no subject)"),
                "from": headers.get("From", ""),
                "date": headers.get("Date", ""),
                "snippet": msg_data.get("snippet", "")[:200]
            })

        return json.dumps({"results": email_list}, indent=2)

    async def _read(self, service, email_id: str = "", **kwargs) -> str:
        """Read a specific email."""
        if not email_id:
            return json.dumps({"error": "email_id is required for read action"})

        msg = service.users().messages().get(
            userId="me",
            id=email_id,
            format="full"
        ).execute()

        headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
        
        # Extract body
        body = ""
        payload = msg.get("payload", {})
        
        if "body" in payload and payload["body"].get("data"):
            body = base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8")
        elif "parts" in payload:
            for part in payload["parts"]:
                if part.get("mimeType") == "text/plain" and part.get("body", {}).get("data"):
                    body = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8")
                    break
                elif part.get("mimeType") == "text/html" and part.get("body", {}).get("data"):
                    body = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8")

        return json.dumps({
            "id": email_id,
            "subject": headers.get("Subject", "(no subject)"),
            "from": headers.get("From", ""),
            "to": headers.get("To", ""),
            "date": headers.get("Date", ""),
            "body": body[:10000]  # Limit body size
        }, indent=2)

    async def _send(self, service, to: str = "", subject: str = "", body: str = "", **kwargs) -> str:
        """Send an email."""
        if not to:
            return json.dumps({"error": "to is required for send action"})
        if not subject:
            return json.dumps({"error": "subject is required for send action"})
        if not body:
            return json.dumps({"error": "body is required for send action"})

        message = MIMEText(body)
        message["to"] = to
        message["subject"] = subject
        
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
        
        result = service.users().messages().send(
            userId="me",
            body={"raw": raw}
        ).execute()

        return json.dumps({
            "success": True,
            "message_id": result.get("id", ""),
            "message": f"Email sent to {to}"
        }, indent=2)

    async def _draft(self, service, to: str = "", subject: str = "", body: str = "", **kwargs) -> str:
        """Create a draft email."""
        if not to:
            return json.dumps({"error": "to is required for draft action"})
        if not subject:
            return json.dumps({"error": "subject is required for draft action"})
        if not body:
            return json.dumps({"error": "body is required for draft action"})

        message = MIMEText(body)
        message["to"] = to
        message["subject"] = subject
        
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
        
        result = service.users().drafts().create(
            userId="me",
            body={"message": {"raw": raw}}
        ).execute()

        return json.dumps({
            "success": True,
            "draft_id": result.get("id", ""),
            "message": f"Draft created for {to}"
        }, indent=2)
