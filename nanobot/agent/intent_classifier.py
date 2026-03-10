"""Intent classification for tool calls to determine if user confirmation is needed."""

from typing import Any


class IntentClassifier:
    """
    Classifies tool calls as reversible, irreversible, or ambiguous.

    Determines whether a tool call requires user confirmation before execution.
    """

    def classify(self, user_message: str, tool_name: str, tool_args: dict[str, Any]) -> str:
        """
        Classify a tool call based on its reversibility.

        Args:
            user_message: The original user message (for context)
            tool_name: Name of the tool being called
            tool_args: Arguments being passed to the tool

        Returns:
            One of: "reversible", "irreversible", "ambiguous"
        """
        # Irreversible actions that cannot be undone
        if tool_name == "gmail":
            action = tool_args.get("action", "")
            if action == "send":
                return "irreversible"
            # Read and search are safe
            return "reversible"

        if tool_name == "exec":
            command = tool_args.get("command", "").lower()
            # Check for destructive operations
            dangerous_patterns = ["rm ", "delete", "del ", "rmdir", "format", "DROP TABLE", "truncate"]
            if any(pattern in command for pattern in dangerous_patterns):
                return "irreversible"
            return "ambiguous"  # Other commands might be risky

        if tool_name == "calendar":
            action = tool_args.get("action", "")
            if action == "delete":
                return "irreversible"
            # Create and list are safe
            return "reversible"

        if tool_name == "cron":
            action = tool_args.get("action", "")
            if action == "delete":
                return "irreversible"
            return "reversible"

        # Clearly reversible/safe operations
        safe_tools = [
            "write_file",     # User can delete or revert
            "read_file",      # Read-only
            "edit_file",      # User can undo edits
            "list_dir",       # Read-only
            "web_search",     # Read-only
            "web_fetch",      # Read-only
            "message",        # Just sends messages to user
        ]

        if tool_name in safe_tools:
            return "reversible"

        # Everything else is ambiguous
        return "ambiguous"

    def requires_confirmation(self, classification: str) -> bool:
        """
        Determine if a classification requires user confirmation.

        Args:
            classification: The classification result from classify()

        Returns:
            True if confirmation is required, False otherwise
        """
        return classification == "irreversible"

    def get_confirmation_message(self, tool_name: str, tool_args: dict[str, Any]) -> str:
        """
        Generate a confirmation message for the user.

        Args:
            tool_name: Name of the tool being called
            tool_args: Arguments being passed to the tool

        Returns:
            A formatted confirmation message
        """
        if tool_name == "gmail" and tool_args.get("action") == "send":
            to = tool_args.get("to", "unknown")
            subject = tool_args.get("subject", "(no subject)")
            body = tool_args.get("body", "")
            body_preview = body[:100] + "..." if len(body) > 100 else body

            return (
                f"⚠️ CONFIRMATION REQUIRED\n\n"
                f"I'm about to send an email:\n"
                f"  To: {to}\n"
                f"  Subject: {subject}\n"
                f"  Body: {body_preview}\n\n"
                f"This action cannot be undone. Reply 'yes' or 'confirm' to proceed, or 'no' or 'cancel' to abort."
            )

        if tool_name == "exec":
            command = tool_args.get("command", "")
            return (
                f"⚠️ CONFIRMATION REQUIRED\n\n"
                f"I'm about to execute a potentially destructive command:\n"
                f"  {command}\n\n"
                f"This action cannot be undone. Reply 'yes' or 'confirm' to proceed, or 'no' or 'cancel' to abort."
            )

        if tool_name == "calendar" and tool_args.get("action") == "delete":
            event_id = tool_args.get("event_id", "unknown")
            return (
                f"⚠️ CONFIRMATION REQUIRED\n\n"
                f"I'm about to delete a calendar event:\n"
                f"  Event ID: {event_id}\n\n"
                f"This action cannot be undone. Reply 'yes' or 'confirm' to proceed, or 'no' or 'cancel' to abort."
            )

        if tool_name == "cron" and tool_args.get("action") == "delete":
            task_id = tool_args.get("task_id", "unknown")
            return (
                f"⚠️ CONFIRMATION REQUIRED\n\n"
                f"I'm about to delete a scheduled task:\n"
                f"  Task ID: {task_id}\n\n"
                f"This action cannot be undone. Reply 'yes' or 'confirm' to proceed, or 'no' or 'cancel' to abort."
            )

        # Generic fallback
        return (
            f"⚠️ CONFIRMATION REQUIRED\n\n"
            f"I'm about to execute: {tool_name}\n"
            f"This action cannot be undone. Reply 'yes' or 'confirm' to proceed, or 'no' or 'cancel' to abort."
        )
