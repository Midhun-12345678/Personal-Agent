"""
Personal Agent - Main entry point
Starts the FastAPI WebSocket server + Agent Loop together
"""

import asyncio
import json
import os
from pathlib import Path
from typing import Callable, Awaitable

from loguru import logger

from nanobot.agent.loop import AgentLoop
from nanobot.config.loader import apply_env_overrides
from nanobot.auth.middleware import AuthManager
from nanobot.bus.queue import MessageBus
from nanobot.channels.web_server import WebServer
from nanobot.integrations.oauth import GoogleOAuthConfig
from nanobot.providers.litellm_provider import LiteLLMProvider
from nanobot.session.manager import SessionManager


def get_config_path() -> Path:
    """Get the default configuration file path."""
    workspace_base = os.environ.get("NANOBOT_WORKSPACE", str(Path.home() / ".personal-agent"))
    return Path(workspace_base) / "config.json"


def get_workspace_path() -> Path:
    """Get the default workspace path."""
    workspace_base = os.environ.get("NANOBOT_WORKSPACE", str(Path.home() / ".personal-agent"))
    return Path(workspace_base) / "workspace"


def get_example_config_path() -> Path:
    """Get the example config file path (in repo root)."""
    return Path(__file__).parent.parent / "config.example.json"


def load_config(config_path: Path | None = None) -> dict:
    """Load configuration from JSON file.
    
    Priority: config.json → config.example.json → env overrides
    """
    path = config_path or get_config_path()
    example_path = get_example_config_path()
    
    # Try config.json first, then fall back to config.example.json
    config_file = None
    if path.exists():
        config_file = path
    elif example_path.exists():
        config_file = example_path
        logger.info(f"Using example config from {example_path}")
    
    if not config_file:
        logger.warning(f"No config file found, using defaults with env overrides")
        return apply_env_overrides({})
    
    try:
        with open(config_file, encoding="utf-8") as f:
            config = json.load(f)
        return apply_env_overrides(config)
    except (json.JSONDecodeError, IOError) as e:
        logger.error(f"Failed to load config: {e}")
        return apply_env_overrides({})


class Application:
    """
    Main application that orchestrates all components.
    
    Manages:
    - WebServer for HTTP/WebSocket API
    - AuthManager for user authentication
    - MessageBus for channel-agent communication
    - Per-user AgentLoop instances
    """

    def __init__(self, config_path: Path | None = None):
        """
        Initialize the application.
        
        Args:
            config_path: Path to config.json. Defaults to ~/.personal-agent/config.json
        """
        self.config = load_config(config_path)
        self.workspace = get_workspace_path()
        self.workspace.mkdir(parents=True, exist_ok=True)
        
        # Initialize core components
        self.auth_manager = AuthManager(self.workspace)
        self.message_bus = MessageBus()
        self.session_manager = SessionManager(self.workspace)
        
        # Per-user agent loops
        self.agent_loops: dict[str, AgentLoop] = {}
        self._agent_tasks: dict[str, asyncio.Task] = {}
        
        # Web server (initialized in start())
        self._server: WebServer | None = None
        self._server_task: asyncio.Task | None = None
        self._outbound_task: asyncio.Task | None = None
        
        # Extract config values
        self._model = self.config.get("agents", {}).get("defaults", {}).get(
            "model", "claude-sonnet-4-20250514"
        )
        self._provider_name = self.config.get("agents", {}).get("defaults", {}).get(
            "provider", "anthropic"
        )

    def _create_provider(self) -> LiteLLMProvider:
        """Create LLM provider from config."""
        providers_config = self.config.get("providers", {})
        provider_config = providers_config.get(self._provider_name, {})
        
        api_key = provider_config.get("apiKey") or provider_config.get("api_key")
        api_base = provider_config.get("apiBase") or provider_config.get("api_base")
        
        return LiteLLMProvider(
            api_key=api_key,
            api_base=api_base,
            default_model=self._model,
            provider_name=self._provider_name,
        )

    async def get_or_create_agent_loop(self, user_id: str) -> AgentLoop:
        """
        Get or create an agent loop for a user.
        
        Args:
            user_id: The user's unique identifier
            
        Returns:
            AgentLoop instance for the user
        """
        if user_id in self.agent_loops:
            return self.agent_loops[user_id]
        
        logger.info(f"Creating agent loop for user: {user_id}")
        
        provider = self._create_provider()
        
        # Extract web search config
        web_config = self.config.get("tools", {}).get("web", {}).get("search", {})
        
        loop = AgentLoop(
            bus=self.message_bus,
            provider=provider,
            workspace=self.workspace,
            user_id=user_id,
            model=self._model,
            session_manager=self.session_manager,
            brave_api_key=web_config.get("apiKey") or None,
            serp_api_key=web_config.get("serpApiKey") or None,
            web_proxy=self.config.get("tools", {}).get("web", {}).get("proxy"),
        )
        
        self.agent_loops[user_id] = loop
        
        # Start the agent loop in background
        task = asyncio.create_task(loop.run())
        self._agent_tasks[user_id] = task
        
        return loop

    async def on_user_connected(self, user_id: str) -> None:
        """
        Called when a user connects via WebSocket.
        
        Args:
            user_id: The connected user's ID
        """
        await self.get_or_create_agent_loop(user_id)
        logger.info(f"User {user_id} connected, agent loop ready")

    async def _route_outbound_messages(self) -> None:
        """Background task to route outbound messages to WebSocket connections."""
        while True:
            try:
                msg = await self.message_bus.consume_outbound()
                user_id = msg.chat_id

                # Check if this is a tool hint message (tool_start/tool_done/plan)
                is_tool_hint = msg.metadata and msg.metadata.get("_tool_hint")

                # Skip regular progress messages, but allow tool hints through
                if msg.metadata and msg.metadata.get("_progress") and not is_tool_hint:
                    logger.debug(f"Skipping progress message for {user_id}")
                    continue

                logger.debug(f"Routing outbound to {user_id}, channel={msg.channel}")

                # Route to web channel if applicable
                if msg.channel == "web" and self._server:
                    # For tool hints, send the content as-is (it's already JSON)
                    if is_tool_hint:
                        # Parse JSON content and send directly
                        try:
                            tool_data = json.loads(msg.content)
                            await self._server.channel.send_message(
                                user_id=user_id,
                                content=msg.content,
                                msg_type=tool_data.get("type", "message"),
                                metadata=msg.metadata,
                            )
                        except json.JSONDecodeError:
                            # Fallback if JSON parsing fails
                            await self._server.channel.send_message(
                                user_id=user_id,
                                content=msg.content,
                                msg_type="message",
                                metadata=msg.metadata,
                            )
                    else:
                        # Check if this is a file notification
                        msg_type = "response"
                        if msg.metadata and msg.metadata.get("type") == "file":
                            msg_type = "file"

                        await self._server.channel.send_message(
                            user_id=user_id,
                            content=msg.content,
                            msg_type=msg_type,
                            metadata=msg.metadata,
                        )
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error routing outbound message: {e}")
                await asyncio.sleep(0.1)
                continue

    def _get_google_oauth_config(self) -> GoogleOAuthConfig | None:
        """Get Google OAuth config from config file."""
        integrations = self.config.get("integrations", {})
        google = integrations.get("google", {})
        
        client_id = google.get("clientId") or google.get("client_id", "")
        client_secret = google.get("clientSecret") or google.get("client_secret", "")
        redirect_uri = google.get("redirectUri") or google.get("redirect_uri", "")
        
        if not client_id:
            return None
        
        config = GoogleOAuthConfig(
            client_id=client_id,
            client_secret=client_secret,
        )
        if redirect_uri:
            config.redirect_uri = redirect_uri
        
        return config

    async def start(self, host: str = "0.0.0.0", port: int = 8765) -> None:
        """
        Start the application.
        
        Args:
            host: Host to bind to
            port: Port to listen on
        """
        # Get server config
        server_config = self.config.get("server", {})
        host = server_config.get("host", host)
        port = server_config.get("port", port)
        
        # Get Google OAuth config
        google_oauth_config = self._get_google_oauth_config()
        
        # Create web server with our auth manager
        self._server = WebServer(
            host=host,
            port=port,
            auth_manager=self.auth_manager,
            workspace=self.workspace,
            google_oauth_config=google_oauth_config,
        )
        
        # Set connection callback
        self._server.set_on_connect_callback(self.on_user_connected)
        
        # Set message bus on channel for inbound routing
        self._server.channel.set_message_bus(self.message_bus)
        
        # Start outbound message router
        self._outbound_task = asyncio.create_task(self._route_outbound_messages())
        
        logger.info(f"Starting Personal Agent on http://{host}:{port}")
        logger.info(f"WebSocket endpoint: ws://{host}:{port}/ws/{{token}}")
        if google_oauth_config:
            logger.info("Google OAuth configured for Gmail/Calendar integrations")
        logger.info("Press Ctrl+C to stop")
        
        # Start server (blocking)
        await self._server.start_async()

    async def stop(self) -> None:
        """Stop the application gracefully."""
        logger.info("Shutting down...")
        
        # Cancel outbound router
        if self._outbound_task:
            self._outbound_task.cancel()
            try:
                await self._outbound_task
            except asyncio.CancelledError:
                pass
        
        # Stop all agent loops
        for user_id, loop in self.agent_loops.items():
            loop.stop()
            await loop.close_mcp()
        
        # Cancel agent tasks
        for task in self._agent_tasks.values():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        
        # Stop web server channel
        if self._server:
            await self._server.channel.stop()
        
        logger.info("Shutdown complete")


def run() -> None:
    """Entry point for the personal-agent command."""
    import sys
    
    async def main():
        app = Application()
        try:
            await app.start()
        except KeyboardInterrupt:
            await app.stop()
        except Exception as e:
            logger.error(f"Fatal error: {e}")
            await app.stop()
            sys.exit(1)
    
    asyncio.run(main())


if __name__ == "__main__":
    run()
