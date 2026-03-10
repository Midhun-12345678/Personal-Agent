"""Error recovery system for tool execution failures."""

import re
from datetime import datetime, timedelta
from typing import Any

from loguru import logger


class ErrorRecovery:
    """Handles structured error recovery for tool execution failures."""

    def classify_error(self, error_message: str, tool_name: str) -> str:
        """
        Classify an error into recovery categories.

        Args:
            error_message: The error message from tool execution
            tool_name: Name of the tool that failed

        Returns:
            One of: "retryable", "conflict", "auth_required", "fatal"
        """
        error_lower = error_message.lower()

        # Authentication/authorization errors
        auth_patterns = [
            "unauthorized", "authentication", "auth", "permission denied",
            "access denied", "forbidden", "invalid credentials", "token expired",
            "not authenticated", "login required"
        ]
        for pattern in auth_patterns:
            if pattern in error_lower:
                logger.info("Classified as auth_required for tool {}", tool_name)
                return "auth_required"

        # Conflict errors (e.g., calendar conflicts, duplicate resources)
        conflict_patterns = [
            "conflict", "already exists", "duplicate", "overlaps",
            "time slot taken", "resource busy"
        ]
        for pattern in conflict_patterns:
            if pattern in error_lower:
                logger.info("Classified as conflict for tool {}", tool_name)
                return "conflict"

        # Retryable errors (network, rate limits, temporary issues)
        retryable_patterns = [
            "timeout", "rate limit", "temporarily unavailable",
            "service unavailable", "connection", "network", "try again",
            "quota exceeded", "too many requests"
        ]
        for pattern in retryable_patterns:
            if pattern in error_lower:
                logger.info("Classified as retryable for tool {}", tool_name)
                return "retryable"

        # Default to fatal if no specific pattern matches
        logger.info("Classified as fatal for tool {}", tool_name)
        return "fatal"

    def get_recovery_action(
        self,
        error_type: str,
        tool_name: str,
        tool_args: dict[str, Any],
        attempt: int = 1
    ) -> dict[str, Any]:
        """
        Get recovery action based on error classification.

        Args:
            error_type: Error classification from classify_error()
            tool_name: Name of the tool that failed
            tool_args: Arguments passed to the tool
            attempt: Current retry attempt number

        Returns:
            Dict with: action ("retry", "suggest_alternatives", "notify", "abort"),
                      delay (seconds to wait before retry),
                      message (user-facing explanation),
                      metadata (additional context)
        """
        if error_type == "retryable":
            # Exponential backoff: 2, 4, 8 seconds
            delay = min(2 ** attempt, 8)
            return {
                "action": "retry",
                "delay": delay,
                "message": f"⚠️ Temporary issue detected. Retrying in {delay}s... (Attempt {attempt}/3)",
                "metadata": {"max_retries": 3}
            }

        elif error_type == "conflict":
            if tool_name == "calendar":
                return {
                    "action": "suggest_alternatives",
                    "delay": 0,
                    "message": "⚠️ CONFLICT: Time slot already occupied. Suggesting alternative times...",
                    "metadata": {"suggest_times": True}
                }
            else:
                return {
                    "action": "notify",
                    "delay": 0,
                    "message": f"⚠️ CONFLICT: Resource already exists or conflicts with existing data.",
                    "metadata": {}
                }

        elif error_type == "auth_required":
            return {
                "action": "notify",
                "delay": 0,
                "message": f"🔒 AUTH REQUIRED: Please re-authenticate {tool_name} to continue.",
                "metadata": {"reauth_needed": True}
            }

        else:  # fatal
            return {
                "action": "abort",
                "delay": 0,
                "message": f"❌ Unable to complete action with {tool_name}.",
                "metadata": {"fatal": True}
            }

    def suggest_alternative_times(
        self,
        original_start: str,
        original_end: str,
        duration_minutes: int = 30
    ) -> list[dict[str, str]]:
        """
        Suggest alternative time slots for calendar conflicts.

        Args:
            original_start: ISO format datetime string
            original_end: ISO format datetime string
            duration_minutes: Duration of the event in minutes

        Returns:
            List of alternative time slot dicts with start/end times
        """
        try:
            start_dt = datetime.fromisoformat(original_start.replace('Z', '+00:00'))
        except Exception:
            # Fallback if parsing fails
            logger.warning("Failed to parse datetime: {}", original_start)
            return []

        alternatives = []

        # Suggest 3 alternatives:
        # 1. 1 hour later
        # 2. 2 hours later
        # 3. Same time next day
        offsets = [
            timedelta(hours=1),
            timedelta(hours=2),
            timedelta(days=1)
        ]

        for offset in offsets:
            alt_start = start_dt + offset
            alt_end = alt_start + timedelta(minutes=duration_minutes)

            alternatives.append({
                "start": alt_start.isoformat(),
                "end": alt_end.isoformat(),
                "display": alt_start.strftime("%I:%M %p on %A, %B %d")
            })

        logger.info("Generated {} alternative time suggestions", len(alternatives))
        return alternatives

    def format_fatal_error(self, error_message: str, tool_name: str) -> str:
        """
        Format a user-friendly fatal error message.

        Args:
            error_message: Raw error message
            tool_name: Name of the tool that failed

        Returns:
            Formatted error message for user
        """
        # Extract the most relevant part of the error
        error_lower = error_message.lower()

        # Try to extract a concise error reason
        if "error:" in error_lower:
            # Extract text after "error:"
            match = re.search(r'error:\s*(.+?)(?:\n|$)', error_message, re.IGNORECASE)
            if match:
                reason = match.group(1).strip()
                return f"❌ {tool_name.capitalize()} error: {reason}"

        # Truncate long error messages
        if len(error_message) > 100:
            return f"❌ {tool_name.capitalize()} error: {error_message[:97]}..."

        return f"❌ {tool_name.capitalize()} error: {error_message}"

    def should_retry(self, error_type: str, attempt: int, max_retries: int = 3) -> bool:
        """
        Determine if a retry should be attempted.

        Args:
            error_type: Error classification
            attempt: Current attempt number
            max_retries: Maximum number of retries allowed

        Returns:
            True if retry should be attempted, False otherwise
        """
        if error_type != "retryable":
            return False

        if attempt >= max_retries:
            logger.info("Max retries ({}) reached, aborting", max_retries)
            return False

        return True
