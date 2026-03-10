"""Google OAuth service for Gmail and Calendar integration."""

import json
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

from loguru import logger
from pydantic import BaseModel


class GoogleOAuthConfig(BaseModel):
    """Configuration for Google OAuth."""
    
    client_id: str = ""
    client_secret: str = ""
    redirect_uri: str = "http://localhost:8765/integrations/callback"


class OAuthService:
    """Service for handling OAuth flows with Google services."""
    
    # Gmail scopes
    GMAIL_SCOPES = [
        "https://www.googleapis.com/auth/gmail.readonly",
        "https://www.googleapis.com/auth/gmail.send",
        "https://www.googleapis.com/auth/gmail.compose",
    ]
    
    # Calendar scopes
    CALENDAR_SCOPES = [
        "https://www.googleapis.com/auth/calendar",
    ]
    
    # Combined scopes for unified Google auth
    ALL_GOOGLE_SCOPES = GMAIL_SCOPES + CALENDAR_SCOPES
    
    GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
    GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
    
    def __init__(
        self,
        workspace: Path,
        config: GoogleOAuthConfig | None = None,
    ):
        """Initialize OAuth service.
        
        Args:
            workspace: User workspace directory for storing credentials
            config: Google OAuth configuration
        """
        self.workspace = Path(workspace)
        self.config = config or GoogleOAuthConfig()
        
        # Pending OAuth states (state -> {user_id, service, scopes})
        self._pending_states: dict[str, dict[str, Any]] = {}
    
    def is_configured(self) -> bool:
        """Check if Google OAuth is configured."""
        return bool(self.config.client_id and self.config.client_secret)
    
    def get_user_credentials_path(self, user_id: str, service: str) -> Path:
        """Get path to user's credentials file.
        
        Args:
            user_id: The user's ID
            service: Service name (gmail, calendar)
            
        Returns:
            Path to credentials file
        """
        user_workspace = self.workspace / "users" / user_id
        return user_workspace / "integrations" / f"{service}_credentials.json"
    
    def is_service_connected(self, user_id: str, service: str) -> bool:
        """Check if a service is connected for a user.
        
        Args:
            user_id: The user's ID
            service: Service name (gmail, calendar)
            
        Returns:
            True if connected
        """
        creds_path = self.get_user_credentials_path(user_id, service)
        return creds_path.exists()
    
    def get_connection_status(self, user_id: str) -> dict[str, bool]:
        """Get connection status for all services.
        
        Args:
            user_id: The user's ID
            
        Returns:
            Dict of service -> connected status
        """
        return {
            "gmail": self.is_service_connected(user_id, "gmail"),
            "calendar": self.is_service_connected(user_id, "calendar"),
            "oauth_configured": self.is_configured(),
        }
    
    def generate_auth_url(
        self,
        user_id: str,
        service: str,
        state: str,
    ) -> str | None:
        """Generate Google OAuth authorization URL.
        
        Args:
            user_id: The user's ID
            service: Service name (gmail, calendar, all)
            state: Random state token for CSRF protection
            
        Returns:
            Authorization URL or None if not configured
        """
        if not self.is_configured():
            return None
        
        # Determine scopes based on service
        if service == "gmail":
            scopes = self.GMAIL_SCOPES
        elif service == "calendar":
            scopes = self.CALENDAR_SCOPES
        elif service == "all":
            scopes = self.ALL_GOOGLE_SCOPES
        else:
            logger.error(f"Unknown service: {service}")
            return None
        
        # Store pending state
        self._pending_states[state] = {
            "user_id": user_id,
            "service": service,
            "scopes": scopes,
        }
        
        # Build authorization URL
        params = {
            "client_id": self.config.client_id,
            "redirect_uri": self.config.redirect_uri,
            "response_type": "code",
            "scope": " ".join(scopes),
            "access_type": "offline",
            "prompt": "consent",
            "state": state,
        }
        
        return f"{self.GOOGLE_AUTH_URL}?{urlencode(params)}"
    
    async def exchange_code(
        self,
        code: str,
        state: str,
    ) -> dict[str, Any] | None:
        """Exchange authorization code for tokens.
        
        Args:
            code: Authorization code from callback
            state: State token from callback
            
        Returns:
            Result dict with success status and details
        """
        import httpx
        
        if state not in self._pending_states:
            logger.error(f"Invalid state: {state}")
            return {"success": False, "error": "Invalid state"}
        
        pending = self._pending_states.pop(state)
        user_id = pending["user_id"]
        service = pending["service"]
        scopes = pending["scopes"]
        
        try:
            # Exchange code for tokens
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.GOOGLE_TOKEN_URL,
                    data={
                        "client_id": self.config.client_id,
                        "client_secret": self.config.client_secret,
                        "code": code,
                        "grant_type": "authorization_code",
                        "redirect_uri": self.config.redirect_uri,
                    },
                )
                
                if response.status_code != 200:
                    logger.error(f"Token exchange failed: {response.text}")
                    return {
                        "success": False,
                        "error": f"Token exchange failed: {response.status_code}",
                    }
                
                tokens = response.json()
        
        except Exception as e:
            logger.error(f"Token exchange error: {e}")
            return {"success": False, "error": str(e)}
        
        # Build credentials object
        credentials = {
            "token": tokens.get("access_token"),
            "refresh_token": tokens.get("refresh_token"),
            "token_uri": self.GOOGLE_TOKEN_URL,
            "client_id": self.config.client_id,
            "client_secret": self.config.client_secret,
            "scopes": scopes,
        }
        
        # Save credentials for appropriate services
        services_saved = []
        
        if service == "gmail" or service == "all":
            self._save_credentials(user_id, "gmail", credentials)
            services_saved.append("gmail")
        
        if service == "calendar" or service == "all":
            self._save_credentials(user_id, "calendar", credentials)
            services_saved.append("calendar")
        
        return {
            "success": True,
            "user_id": user_id,
            "services": services_saved,
        }
    
    def _save_credentials(
        self,
        user_id: str,
        service: str,
        credentials: dict,
    ) -> None:
        """Save credentials to file.
        
        Args:
            user_id: The user's ID
            service: Service name
            credentials: Credentials dict
        """
        creds_path = self.get_user_credentials_path(user_id, service)
        creds_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(creds_path, "w", encoding="utf-8") as f:
            json.dump(credentials, f, indent=2)
        
        logger.info(f"Saved {service} credentials for user {user_id}")
    
    def disconnect_service(self, user_id: str, service: str) -> bool:
        """Disconnect a service by removing credentials.
        
        Args:
            user_id: The user's ID
            service: Service name
            
        Returns:
            True if disconnected successfully
        """
        creds_path = self.get_user_credentials_path(user_id, service)
        
        if creds_path.exists():
            creds_path.unlink()
            logger.info(f"Disconnected {service} for user {user_id}")
            return True
        
        return False
