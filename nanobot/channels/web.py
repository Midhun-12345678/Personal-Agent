"""WebSocket-based channel for web frontend communication."""

import asyncio
import json
import logging
from datetime import datetime
from typing import Optional, TYPE_CHECKING

from fastapi import WebSocket, WebSocketDisconnect

from ..auth.middleware import require_auth, AuthManager
from ..bus.events import InboundMessage

if TYPE_CHECKING:
    from ..bus.queue import MessageBus

logger = logging.getLogger(__name__)


class WebChannel:
    """WebSocket channel for real-time web frontend communication."""

    name = "web"

    def __init__(self, config: dict):
        """Initialize the web channel.

        Args:
            config: Channel configuration containing:
                - auth_manager: Optional AuthManager instance
                - users_file: Path to users.json (if no auth_manager provided)
        """
        self.config = config
        self._connections: dict[str, WebSocket] = {}  # user_id -> websocket
        self._keepalive_tasks: dict[str, asyncio.Task] = {}  # user_id -> keepalive task
        self._message_queue: asyncio.Queue = asyncio.Queue()
        self._pending_messages: dict[str, list[dict]] = {}  # user_id -> queued messages for reconnection
        self._running = False
        self._message_bus: Optional["MessageBus"] = None

        # Initialize auth manager
        if "auth_manager" in config:
            self._auth_manager = config["auth_manager"]
        else:
            from pathlib import Path
            users_file = config.get("users_file", "~/.nanobot")
            self._auth_manager = AuthManager(Path(users_file).expanduser())

    async def connect(self, websocket: WebSocket, token: str) -> Optional[str]:
        """Handle a new WebSocket connection.

        Args:
            websocket: The WebSocket connection
            token: Authentication token

        Returns:
            user_id if authenticated, None otherwise
        """
        # Authenticate the token
        try:
            user_context = require_auth(self._auth_manager, token)
        except PermissionError:
            logger.warning("WebSocket connection rejected: invalid token")
            await websocket.close(code=4001, reason="Invalid token")
            return None

        user_id = user_context.user_id
        await websocket.accept()

        # Store connection (overwrites previous connection for same user)
        if user_id in self._connections:
            try:
                await self._connections[user_id].close(
                    code=4002, reason="New connection opened"
                )
            except Exception:
                pass

        self._connections[user_id] = websocket
        logger.info(f"WebSocket connected: user_id={user_id}")
        
        # Send welcome message immediately after connection
        await websocket.send_text(json.dumps({
            "type": "connected",
            "user_id": user_id
        }))
        
        # Deliver any queued messages from while user was disconnected
        if user_id in self._pending_messages:
            queued = self._pending_messages.pop(user_id)
            logger.info(f"Delivering {len(queued)} queued messages to {user_id}")
            for msg in queued:
                try:
                    await websocket.send_json(msg)
                except Exception as e:
                    logger.error(f"Failed to deliver queued message: {e}")
        
        # Start keepalive task
        self._keepalive_tasks[user_id] = asyncio.create_task(
            self._keepalive(websocket, user_id)
        )
        
        return user_id

    async def _keepalive(self, websocket: WebSocket, user_id: str) -> None:
        """Send periodic pings to keep the connection alive."""
        try:
            while user_id in self._connections:
                await asyncio.sleep(20)
                if user_id not in self._connections:
                    break
                try:
                    await websocket.send_text(json.dumps({"type": "ping"}))
                except Exception:
                    break
        except asyncio.CancelledError:
            pass

    async def disconnect(self, user_id: str) -> None:
        """Handle WebSocket disconnection.

        Args:
            user_id: The disconnected user's ID
        """
        # Cancel keepalive task
        if user_id in self._keepalive_tasks:
            self._keepalive_tasks[user_id].cancel()
            del self._keepalive_tasks[user_id]
            
        if user_id in self._connections:
            del self._connections[user_id]
            logger.info(f"WebSocket disconnected: user_id={user_id}")

    async def handle_message(self, websocket: WebSocket, user_id: str) -> None:
        """Handle incoming messages from a WebSocket connection.

        Args:
            websocket: The WebSocket connection
            user_id: The authenticated user's ID
        """
        try:
            while True:
                data = await websocket.receive_text()
                try:
                    message = json.loads(data)
                except json.JSONDecodeError:
                    await self._send_error(websocket, "Invalid JSON")
                    continue

                msg_type = message.get("type", "message")

                if msg_type == "ping":
                    await websocket.send_json({"type": "pong"})
                elif msg_type == "message":
                    content = message.get("content", "")
                    if content:
                        # Publish to message bus if available
                        if self._message_bus:
                            inbound = InboundMessage(
                                channel="web",
                                sender_id=user_id,
                                chat_id=user_id,  # For web, chat_id = user_id
                                content=content,
                                timestamp=datetime.now(),
                                metadata=message.get("metadata", {}),
                            )
                            await self._message_bus.publish_inbound(inbound)
                        else:
                            # Fallback to local queue
                            await self._message_queue.put({
                                "user_id": user_id,
                                "content": content,
                                "metadata": message.get("metadata", {})
                            })
                        logger.debug(f"Message queued from {user_id}: {content[:50]}...")
                else:
                    await self._send_error(websocket, f"Unknown message type: {msg_type}")

        except WebSocketDisconnect:
            await self.disconnect(user_id)
        except Exception as e:
            logger.error(f"Error handling WebSocket message: {e}")
            await self.disconnect(user_id)

    async def _send_error(self, websocket: WebSocket, error: str) -> None:
        """Send an error message to the client.

        Args:
            websocket: The WebSocket connection
            error: Error message
        """
        try:
            await websocket.send_json({
                "type": "error",
                "error": error
            })
        except Exception:
            pass

    async def send_message(
        self,
        user_id: str,
        content: str,
        msg_type: str = "message",
        metadata: Optional[dict] = None
    ) -> bool:
        """Send a message to a connected user.

        Args:
            user_id: Target user ID
            content: Message content
            msg_type: Message type (default: "message")
            metadata: Optional metadata

        Returns:
            True if sent successfully, False otherwise
        """
        logger.info(f"[WebChannel] Sending to user_id={user_id}, type={msg_type}, connected={list(self._connections.keys())}")
        
        # Build message data
        message_data = {
            "type": msg_type,
            "content": content,
        }
        # Include file-specific fields if this is a file message
        if msg_type == "file" and metadata:
            message_data["filename"] = metadata.get("filename", "")
            message_data["download_url"] = metadata.get("download_url", "")
        else:
            message_data["metadata"] = metadata or {}
        
        websocket = self._connections.get(user_id)
        if not websocket:
            # Queue message for delivery when user reconnects
            logger.warning(f"[WebChannel] User {user_id} not connected, queuing message")
            if user_id not in self._pending_messages:
                self._pending_messages[user_id] = []
            self._pending_messages[user_id].append(message_data)
            return False

        try:
            await websocket.send_json(message_data)
            logger.info(f"[WebChannel] Message sent successfully to {user_id}")
            return True
        except Exception as e:
            logger.error(f"Error sending message to {user_id}: {e}")
            await self.disconnect(user_id)
            return False

    async def broadcast_to_user(self, user_id: str, event: str, data: dict) -> bool:
        """Broadcast an event to a specific user.

        Args:
            user_id: Target user ID
            event: Event name
            data: Event data

        Returns:
            True if sent successfully, False otherwise
        """
        return await self.send_message(
            user_id,
            content="",
            msg_type=event,
            metadata=data
        )

    async def get_next_message(self) -> dict:
        """Get the next message from the queue.

        Returns:
            Message dict with user_id, content, and metadata
        """
        return await self._message_queue.get()

    def is_user_connected(self, user_id: str) -> bool:
        """Check if a user is currently connected.

        Args:
            user_id: User ID to check

        Returns:
            True if connected, False otherwise
        """
        return user_id in self._connections

    def get_connected_users(self) -> list[str]:
        """Get list of connected user IDs.

        Returns:
            List of user IDs
        """
        return list(self._connections.keys())

    def set_message_bus(self, bus: "MessageBus") -> None:
        """Set the message bus for inbound message routing.

        Args:
            bus: MessageBus instance to publish inbound messages to
        """
        self._message_bus = bus

    async def start(self) -> None:
        """Start the channel (no-op for WebSocket, server handles this)."""
        self._running = True
        logger.info("WebChannel started")

    async def stop(self) -> None:
        """Stop the channel and close all connections."""
        self._running = False

        # Cancel all keepalive tasks
        for task in self._keepalive_tasks.values():
            task.cancel()
        self._keepalive_tasks.clear()

        # Close all connections
        for user_id, websocket in list(self._connections.items()):
            try:
                await websocket.close(code=1001, reason="Server shutting down")
            except Exception:
                pass

        self._connections.clear()
        logger.info("WebChannel stopped")
