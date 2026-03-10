"""NotifyFile tool for notifying users about created files."""

from typing import Any, Awaitable, Callable

from nanobot.agent.tools.base import Tool
from nanobot.bus.events import OutboundMessage


class NotifyFileTool(Tool):
    """Tool to notify users about created files with download links."""

    def __init__(
        self,
        send_callback: Callable[[OutboundMessage], Awaitable[None]] | None = None,
        user_id: str = "",
        channel: str = "web",
    ):
        self._send_callback = send_callback
        self._user_id = user_id  # Workspace owner (for file paths)
        self._chat_id = user_id  # Message routing (may differ from user_id)
        self._channel = channel

    def set_context(self, channel: str, chat_id: str, message_id: str | None = None) -> None:
        """Set the current message context. Updates channel and chat_id for routing."""
        self._channel = channel
        self._chat_id = chat_id
        # Note: user_id is set at construction time and should not be overwritten
        # because it must match the workspace where files are written

    def set_send_callback(self, callback: Callable[[OutboundMessage], Awaitable[None]]) -> None:
        """Set the callback for sending messages."""
        self._send_callback = callback

    @property
    def name(self) -> str:
        return "notify_file"

    @property
    def description(self) -> str:
        return (
            "Notify the user about a file you created so they can download it. "
            "ALWAYS call this immediately after using write_file to create a file for the user."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "filename": {
                    "type": "string",
                    "description": "The filename (just the name, not full path)"
                },
                "description": {
                    "type": "string",
                    "description": "One line describing what the file contains"
                }
            },
            "required": ["filename", "description"]
        }

    async def execute(self, filename: str, description: str, **kwargs: Any) -> str:
        """Notify the user about a created file."""
        if not self._send_callback:
            return "Error: No send callback configured"

        if not self._user_id:
            return "Error: No user context set"

        # Build the download URL using user_id (workspace owner)
        download_url = f"/files/{self._user_id}/{filename}"

        # Send the file notification to chat_id (message routing)
        await self._send_callback(OutboundMessage(
            channel=self._channel,
            chat_id=self._chat_id,
            content=f"I've created **{filename}** — {description}",
            metadata={
                "type": "file",
                "filename": filename,
                "download_url": download_url
            }
        ))

        return f"User notified about file: {filename}"
