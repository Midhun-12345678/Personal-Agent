"""FastAPI WebSocket server for the web channel."""

import logging
import secrets
from pathlib import Path
from typing import Awaitable, Callable, Optional

from fastapi import FastAPI, WebSocket, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from pydantic import BaseModel

from .web import WebChannel
from ..auth.middleware import AuthManager
from ..integrations.oauth import OAuthService, GoogleOAuthConfig

logger = logging.getLogger(__name__)


class RegisterRequest(BaseModel):
    """User registration request."""
    display_name: str
    password: str | None = None


class LoginRequest(BaseModel):
    """User login request."""
    display_name: str
    password: str


class RegisterResponse(BaseModel):
    """User registration response."""
    user_id: str
    token: str


class WebServer:
    """FastAPI server for WebSocket communication."""

    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 8765,
        users_file: Optional[str] = None,
        cors_origins: Optional[list[str]] = None,
        auth_manager: Optional[AuthManager] = None,
        workspace: Optional[Path] = None,
        google_oauth_config: Optional[GoogleOAuthConfig] = None,
    ):
        """Initialize the web server.

        Args:
            host: Host to bind to
            port: Port to listen on
            users_file: Path to users.json file
            cors_origins: List of allowed CORS origins
            auth_manager: Optional external AuthManager instance
            workspace: User workspace directory
            google_oauth_config: Google OAuth configuration
        """
        self.host = host
        self.port = port
        self.workspace = workspace or Path.home() / ".personal-agent" / "workspace"

        # Initialize auth manager (use provided or create new)
        if auth_manager:
            self._auth_manager = auth_manager
        else:
            users_path = Path(users_file).expanduser() if users_file else Path.home() / ".nanobot"
            self._auth_manager = AuthManager(users_path)
        
        # Initialize OAuth service
        self._oauth_service = OAuthService(
            workspace=self.workspace,
            config=google_oauth_config,
        )
        
        # Connection callback
        self._on_connect_callback: Optional[Callable[[str], Awaitable[None]]] = None

        # Initialize web channel
        self._channel = WebChannel({
            "auth_manager": self._auth_manager
        })

        # Create FastAPI app
        self.app = FastAPI(
            title="Personal Agent WebSocket Server",
            version="0.1.0"
        )

        # Configure CORS - allow all origins for cross-domain deployment
        origins = cors_origins or ["*"]
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        # Register routes
        self._register_routes()

    def _register_routes(self) -> None:
        """Register API routes."""

        @self.app.get("/health")
        async def health_check():
            """Health check endpoint."""
            return {
                "status": "ok",
                "connected_users": len(self._channel.get_connected_users())
            }

        @self.app.post("/register", response_model=RegisterResponse)
        async def register_user(request: RegisterRequest):
            """Register a new user and get auth token."""
            try:
                # Check if user already exists
                if self._auth_manager.user_exists(request.display_name):
                    raise HTTPException(status_code=409, detail="User already exists. Please login instead.")
                
                user_context = self._auth_manager.register_user(
                    request.display_name,
                    password=request.password
                )
                return RegisterResponse(
                    user_id=user_context.user_id,
                    token=user_context.token
                )
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e))

        @self.app.post("/login", response_model=RegisterResponse)
        async def login_user(request: LoginRequest):
            """Login an existing user."""
            user_context = self._auth_manager.login(request.display_name, request.password)
            if not user_context:
                raise HTTPException(status_code=401, detail="Invalid username or password")
            return RegisterResponse(
                user_id=user_context.user_id,
                token=user_context.token
            )

        @self.app.get("/user/exists")
        async def check_user_exists(name: str = Query(...)):
            """Check if a user exists by name."""
            exists = self._auth_manager.user_exists(name)
            return {"exists": exists}

        @self.app.websocket("/ws/{token}")
        async def websocket_endpoint(websocket: WebSocket, token: str):
            """WebSocket endpoint for real-time communication."""
            user_id = await self._channel.connect(websocket, token)
            if user_id:
                # Notify application of new connection
                if self._on_connect_callback:
                    await self._on_connect_callback(user_id)
                await self._channel.handle_message(websocket, user_id)

        # ------------------------------------------------------------------
        # Integration / OAuth Routes
        # ------------------------------------------------------------------

        @self.app.get("/integrations/status")
        async def get_integrations_status(token: str = Query(...)):
            """Get integration connection status for the authenticated user."""
            user_ctx = self._auth_manager.authenticate(token)
            if not user_ctx:
                raise HTTPException(status_code=401, detail="Invalid token")
            
            status = self._oauth_service.get_connection_status(user_ctx.user_id)
            return status

        @self.app.get("/integrations/connect/{service}")
        async def connect_integration(
            service: str,
            token: str = Query(...),
        ):
            """Start OAuth flow for a service (gmail, calendar, or all)."""
            user_ctx = self._auth_manager.authenticate(token)
            if not user_ctx:
                raise HTTPException(status_code=401, detail="Invalid token")
            
            if service not in ("gmail", "calendar", "all"):
                raise HTTPException(status_code=400, detail="Invalid service")
            
            if not self._oauth_service.is_configured():
                raise HTTPException(
                    status_code=503,
                    detail="Google OAuth not configured. Add client_id and client_secret to config."
                )
            
            # Generate state token
            state = secrets.token_urlsafe(32)
            
            auth_url = self._oauth_service.generate_auth_url(
                user_id=user_ctx.user_id,
                service=service,
                state=state,
            )
            
            if not auth_url:
                raise HTTPException(status_code=500, detail="Failed to generate auth URL")
            
            return {"auth_url": auth_url}

        @self.app.get("/integrations/callback")
        async def oauth_callback(
            code: str = Query(None),
            state: str = Query(None),
            error: str = Query(None),
        ):
            """Handle OAuth callback from Google."""
            if error:
                return HTMLResponse(content=f"""
                    <html>
                    <head><title>Connection Failed</title></head>
                    <body style="font-family: system-ui; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; background: #fef2f2;">
                        <div style="text-align: center; padding: 40px; background: white; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                            <h1 style="color: #dc2626; margin-bottom: 16px;">Connection Failed</h1>
                            <p style="color: #6b7280;">{error}</p>
                            <p style="margin-top: 24px;"><a href="javascript:window.close()" style="color: #3b82f6;">Close this window</a></p>
                        </div>
                    </body>
                    </html>
                """, status_code=400)
            
            if not code or not state:
                raise HTTPException(status_code=400, detail="Missing code or state")
            
            result = await self._oauth_service.exchange_code(code, state)
            
            if not result or not result.get("success"):
                error_msg = result.get("error", "Unknown error") if result else "Exchange failed"
                return HTMLResponse(content=f"""
                    <html>
                    <head><title>Connection Failed</title></head>
                    <body style="font-family: system-ui; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; background: #fef2f2;">
                        <div style="text-align: center; padding: 40px; background: white; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                            <h1 style="color: #dc2626; margin-bottom: 16px;">Connection Failed</h1>
                            <p style="color: #6b7280;">{error_msg}</p>
                            <p style="margin-top: 24px;"><a href="javascript:window.close()" style="color: #3b82f6;">Close this window</a></p>
                        </div>
                    </body>
                    </html>
                """, status_code=400)
            
            services = ", ".join(result.get("services", []))
            return HTMLResponse(content=f"""
                <html>
                <head><title>Connected Successfully</title></head>
                <body style="font-family: system-ui; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; background: #f0fdf4;">
                    <div style="text-align: center; padding: 40px; background: white; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                        <h1 style="color: #16a34a; margin-bottom: 16px;">Connected!</h1>
                        <p style="color: #6b7280;">Successfully connected: <strong>{services}</strong></p>
                        <p style="margin-top: 24px;"><a href="javascript:window.close()" style="color: #3b82f6;">Close this window</a></p>
                        <script>
                            // Notify opener and close
                            if (window.opener) {{
                                window.opener.postMessage({{ type: 'oauth_success', services: {result.get('services', [])} }}, '*');
                            }}
                            setTimeout(() => window.close(), 2000);
                        </script>
                    </div>
                </body>
                </html>
            """)

        @self.app.delete("/integrations/disconnect/{service}")
        async def disconnect_integration(
            service: str,
            token: str = Query(...),
        ):
            """Disconnect a service."""
            user_ctx = self._auth_manager.authenticate(token)
            if not user_ctx:
                raise HTTPException(status_code=401, detail="Invalid token")
            
            if service not in ("gmail", "calendar"):
                raise HTTPException(status_code=400, detail="Invalid service")
            
            success = self._oauth_service.disconnect_service(user_ctx.user_id, service)
            return {"success": success}

        # ------------------------------------------------------------------
        # File Download Routes
        # ------------------------------------------------------------------

        @self.app.get("/files/{user_id}")
        async def list_files(user_id: str, token: str = Query(...)):
            """List files for a user."""
            user_ctx = self._auth_manager.authenticate(token)
            if not user_ctx or user_ctx.user_id != user_id:
                raise HTTPException(status_code=403, detail="Forbidden")
            
            file_dir = self.workspace / "users" / user_id
            if not file_dir.exists():
                return {"files": []}
            
            files = [f.name for f in file_dir.iterdir() if f.is_file()]
            return {"files": files}

        @self.app.get("/files/{user_id}/{filename}")
        async def download_file(user_id: str, filename: str, token: str = Query(...)):
            """Download a file."""
            user_ctx = self._auth_manager.authenticate(token)
            if not user_ctx or user_ctx.user_id != user_id:
                raise HTTPException(status_code=403, detail="Forbidden")
            
            file_path = self.workspace / "users" / user_id / filename
            if not file_path.exists():
                raise HTTPException(status_code=404, detail="File not found")
            
            return FileResponse(
                path=file_path,
                filename=filename,
                media_type="application/octet-stream"
            )

        @self.app.delete("/session/{token}")
        async def clear_session(token: str):
            """Nuclear: clear a user's session JSONL file."""
            user_ctx = self._auth_manager.authenticate(token)
            if not user_ctx:
                raise HTTPException(status_code=401, detail="Invalid token")

            session_file = self.workspace / "users" / user_ctx.user_id / "session.jsonl"
            try:
                if session_file.exists():
                    session_file.unlink()
            except Exception as e:
                logger.warning("Failed to clear session file for user %s: %s", user_ctx.user_id, e)
                raise HTTPException(status_code=500, detail="Failed to clear session file")

            return {"cleared": True}

        # ------------------------------------------------------------------
        # Usage Dashboard Routes
        # ------------------------------------------------------------------

        @self.app.get("/dashboard")
        async def get_dashboard(token: str = Query(...)):
            """Get usage dashboard for the authenticated user."""
            user_ctx = self._auth_manager.authenticate(token)
            if not user_ctx:
                raise HTTPException(status_code=401, detail="Invalid token")

            try:
                from ..agent.usage_logger import UsageLogger

                usage_logger = UsageLogger(self.workspace, user_ctx.user_id)
                summary = usage_logger.get_summary(days=7)
                dashboard = usage_logger.format_dashboard(summary)

                return {"dashboard": dashboard, "summary": summary}
            except Exception as e:
                logger.error(f"Dashboard error: {e}")
                return {"dashboard": "Stats unavailable", "summary": {}}

        @self.app.get("/dashboard/summary")
        async def get_dashboard_summary(
            token: str = Query(...),
            days: int = Query(7, ge=1, le=90)
        ):
            """Get usage summary statistics for the authenticated user."""
            user_ctx = self._auth_manager.authenticate(token)
            if not user_ctx:
                raise HTTPException(status_code=401, detail="Invalid token")

            try:
                from ..agent.usage_logger import UsageLogger

                usage_logger = UsageLogger(self.workspace, user_ctx.user_id)
                summary = usage_logger.get_summary(days=days)

                return summary
            except Exception as e:
                logger.error(f"Dashboard summary error: {e}")
                return {}

    @property
    def channel(self) -> WebChannel:
        """Get the web channel instance."""
        return self._channel

    @property
    def auth_manager(self) -> AuthManager:
        """Get the auth manager instance."""
        return self._auth_manager

    def set_on_connect_callback(
        self, callback: Callable[[str], Awaitable[None]]
    ) -> None:
        """Set callback to be called when a user connects.
        
        Args:
            callback: Async function that takes user_id as argument
        """
        self._on_connect_callback = callback

    def run(self) -> None:
        """Run the server (blocking)."""
        import uvicorn
        uvicorn.run(self.app, host=self.host, port=self.port)

    async def start_async(self) -> None:
        """Start the server asynchronously."""
        import uvicorn
        config = uvicorn.Config(self.app, host=self.host, port=self.port)
        server = uvicorn.Server(config)
        await server.serve()


def create_app(
    users_file: Optional[str] = None,
    cors_origins: Optional[list[str]] = None
) -> FastAPI:
    """Create a FastAPI app instance for deployment.

    Args:
        users_file: Path to users.json file
        cors_origins: List of allowed CORS origins

    Returns:
        Configured FastAPI application
    """
    server = WebServer(users_file=users_file, cors_origins=cors_origins)
    return server.app
