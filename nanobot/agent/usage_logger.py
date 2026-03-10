"""Usage logging and dashboard for tracking agent tasks."""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from loguru import logger


class UsageLogger:
    """Logs task usage and generates dashboard statistics."""

    def __init__(self, workspace: Path, user_id: str):
        """
        Initialize usage logger.

        Args:
            workspace: Base workspace directory
            user_id: User identifier
        """
        self.user_id = user_id
        self.usage_file = workspace / "users" / user_id / "usage.jsonl"

        # Create parent directories if they don't exist
        try:
            self.usage_file.parent.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.warning(f"Failed to create usage log directory: {e}")

    def log_task(
        self,
        task_description: str,
        tools_used: list[str],
        success: bool,
        error: str | None,
        duration_seconds: float
    ) -> None:
        """
        Log a completed task to usage.jsonl.

        Args:
            task_description: Description of the task
            tools_used: List of tool names used
            success: Whether the task succeeded
            error: Error message if failed, None otherwise
            duration_seconds: Task duration in seconds
        """
        try:
            # Truncate task description to 100 chars
            task_truncated = task_description[:100]

            # Create log entry
            entry = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "task": task_truncated,
                "tools": tools_used,
                "success": success,
                "error": error,
                "duration_seconds": round(duration_seconds, 2)
            }

            # Append to file
            with open(self.usage_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")

            logger.debug(f"Logged task for user {self.user_id}: success={success}")

        except Exception as e:
            logger.warning(f"Failed to log task usage: {e}")

    def get_summary(self, days: int = 7) -> dict[str, Any]:
        """
        Get usage summary for the last N days.

        Args:
            days: Number of days to include in summary

        Returns:
            Dictionary with summary statistics
        """
        try:
            # Check if file exists
            if not self.usage_file.exists():
                return self._empty_summary()

            # Calculate cutoff time
            cutoff_time = datetime.now(timezone.utc) - timedelta(days=days)

            # Read and filter entries
            tasks_completed = 0
            tasks_failed = 0
            tool_counts: dict[str, int] = {}
            total_duration = 0.0
            recent_failures: list[dict] = []

            with open(self.usage_file, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        entry = json.loads(line.strip())

                        # Parse timestamp
                        timestamp = datetime.fromisoformat(entry["timestamp"])

                        # Filter by date
                        if timestamp < cutoff_time:
                            continue

                        # Count successes/failures
                        if entry["success"]:
                            tasks_completed += 1
                        else:
                            tasks_failed += 1
                            # Track recent failures (keep last 3)
                            recent_failures.append({
                                "task": entry["task"],
                                "error": entry.get("error", "Unknown error"),
                                "timestamp": entry["timestamp"]
                            })

                        # Count tools
                        for tool in entry.get("tools", []):
                            tool_counts[tool] = tool_counts.get(tool, 0) + 1

                        # Sum duration
                        total_duration += entry.get("duration_seconds", 0.0)

                    except (json.JSONDecodeError, KeyError, ValueError) as e:
                        logger.warning(f"Failed to parse usage log entry: {e}")
                        continue

            # Get top 3 most used tools
            most_used_tools = [
                {"tool": tool, "count": count}
                for tool, count in sorted(tool_counts.items(), key=lambda x: x[1], reverse=True)[:3]
            ]

            # Keep only last 3 failures
            recent_failures = recent_failures[-3:]

            # Calculate estimated time saved (5 minutes per completed task)
            estimated_time_saved_minutes = tasks_completed * 5

            return {
                "tasks_completed": tasks_completed,
                "tasks_failed": tasks_failed,
                "most_used_tools": most_used_tools,
                "total_duration_seconds": round(total_duration, 1),
                "estimated_time_saved_minutes": estimated_time_saved_minutes,
                "recent_failures": recent_failures
            }

        except Exception as e:
            logger.warning(f"Failed to generate usage summary: {e}")
            return self._empty_summary()

    def _empty_summary(self) -> dict[str, Any]:
        """Return an empty summary structure."""
        return {
            "tasks_completed": 0,
            "tasks_failed": 0,
            "most_used_tools": [],
            "total_duration_seconds": 0.0,
            "estimated_time_saved_minutes": 0,
            "recent_failures": []
        }

    def format_dashboard(self, summary: dict[str, Any]) -> str:
        """
        Format summary as a dashboard string.

        Args:
            summary: Summary dictionary from get_summary()

        Returns:
            Formatted dashboard string
        """
        lines = [
            "📊 Your Nanobot Stats (Last 7 Days)",
            "─────────────────────────────────",
            f"✅ Tasks Completed: {summary['tasks_completed']}",
            f"❌ Failed Tasks: {summary['tasks_failed']}",
            "🔧 Most Used Tools:"
        ]

        # Add tools or "No tools used yet"
        if summary["most_used_tools"]:
            for i, tool_info in enumerate(summary["most_used_tools"], 1):
                lines.append(f"{i}. {tool_info['tool']} ({tool_info['count']} times)")
        else:
            lines.append("  No tools used yet.")

        lines.append(f"⏱️ Estimated Time Saved: ~{summary['estimated_time_saved_minutes']} minutes")

        # Add recent failures if any
        if summary["recent_failures"]:
            lines.append("📋 Recent Failures:")
            for failure in summary["recent_failures"]:
                lines.append(f"• \"{failure['task']}\" — {failure['error']}")

        return "\n".join(lines)
