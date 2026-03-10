"""Pending action tracking for confirmation flow with auto-expiry."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class PendingAction:
    """
    Represents a pending tool action awaiting user confirmation.

    Includes auto-confirmation timer and expiry tracking.
    """
    tool_name: str
    tool_args: dict[str, Any]
    tool_call: Any  # The actual tool call object from the LLM
    messages: list[dict]  # Message context for resuming
    iteration: int
    tools_used: list[str]
    created_at: datetime = field(default_factory=datetime.now)
    auto_confirm_seconds: int = 30

    def is_expired(self) -> bool:
        """
        Check if the pending action has expired and should be auto-confirmed.

        Returns:
            True if the action has been pending longer than auto_confirm_seconds
        """
        elapsed = (datetime.now() - self.created_at).total_seconds()
        return elapsed >= self.auto_confirm_seconds

    def seconds_remaining(self) -> int:
        """
        Calculate how many seconds remain before auto-confirmation.

        Returns:
            Number of seconds remaining (0 if expired)
        """
        elapsed = (datetime.now() - self.created_at).total_seconds()
        remaining = self.auto_confirm_seconds - elapsed
        return max(0, int(remaining))

    def format_confirmation_message(self, base_message: str) -> str:
        """
        Wrap a base confirmation message with timer information.

        Args:
            base_message: The core confirmation message (without timer info)

        Returns:
            Formatted message with YES/NO prompt and timer
        """
        # Extract the action description from the base message
        # Most base messages follow pattern: "⚠️ CONFIRMATION REQUIRED\n\nI'm about to..."
        # We'll wrap it with our own format

        seconds = self.seconds_remaining()

        return (
            f"⚠️ I'm about to perform an irreversible action:\n\n"
            f"{base_message}\n\n"
            f"Reply YES to confirm or NO to cancel.\n"
            f"⏱️ Auto-confirming in {seconds} seconds..."
        )
