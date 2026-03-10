"""Task planner for multi-step complex tasks."""

import json
import re
from typing import Any

from loguru import logger


class TaskPlanner:
    """Plans and tracks multi-step tasks."""

    ACTION_VERBS = [
        "schedule", "create", "send", "email", "book", "write", "set up",
        "add", "make", "delete", "find", "search", "remind", "draft", "update", "move"
    ]

    TOOL_EMOJIS = {
        "gmail": "📧",
        "calendar": "📅",
        "write_file": "📁",
        "read_file": "📁",
        "edit_file": "📁",
        "web_search": "🔍",
        "web_fetch": "🔍",
        "exec": "⚙️",
        "memory": "🧠",
        "browser": "🌐",
    }

    NUMBER_EMOJIS = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣"]

    def is_complex_task(self, user_message: str) -> bool:
        """
        Determine if a task is complex (requires planning).

        A task is complex if it contains 2 or more action verbs.

        Args:
            user_message: The user's input message

        Returns:
            True if 2+ action verbs found, False otherwise
        """
        message_lower = user_message.lower()
        verb_count = 0

        for verb in self.ACTION_VERBS:
            # Use word boundary matching to avoid partial matches
            pattern = r'\b' + re.escape(verb) + r'\b'
            if re.search(pattern, message_lower):
                verb_count += 1
                if verb_count >= 2:
                    return True

        return False

    async def generate_plan(
        self,
        user_message: str,
        provider: Any,
        available_tools: list[str]
    ) -> list[dict]:
        """
        Generate a step-by-step plan for the user's request.

        Args:
            user_message: The user's input message
            provider: LLM provider instance
            available_tools: List of available tool names

        Returns:
            List of plan steps, each with: step, action, tool
        """
        # Build the system prompt
        tools_list = ", ".join(available_tools)
        system_prompt = (
            "You are a task planner. Break the user's request into numbered steps. "
            "For each step, identify: step number, a short action description (max 8 words), "
            f"and which tool will be used from this list: {tools_list}. "
            "Respond ONLY with valid JSON array. No markdown, no explanation. "
            'Format: [{"step": 1, "action": "Check calendar availability", "tool": "calendar"}, ...]'
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]

        try:
            # Call the LLM
            response = await provider.chat(
                messages=messages,
                tools=None,  # No tools for planning
                model=provider.get_default_model(),
                temperature=0.3,  # Lower temperature for more consistent planning
                max_tokens=500,
            )

            content = response.content or ""

            # Strip markdown fences if present
            content = content.strip()
            if content.startswith("```json"):
                content = content[7:]
            elif content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()

            # Parse JSON
            steps = json.loads(content)

            # Validate structure
            if not isinstance(steps, list):
                raise ValueError("Response is not a list")

            # Ensure each step has required fields
            validated_steps = []
            for i, step in enumerate(steps[:6], start=1):  # Max 6 steps
                if not isinstance(step, dict):
                    continue
                validated_steps.append({
                    "step": step.get("step", i),
                    "action": str(step.get("action", "Process step"))[:50],  # Max length
                    "tool": step.get("tool", "various")
                })

            if validated_steps:
                logger.info("Generated plan with {} steps", len(validated_steps))
                return validated_steps

            # If no valid steps, return fallback
            raise ValueError("No valid steps in response")

        except Exception as e:
            logger.warning("Plan generation failed: {}", e)
            # Fallback plan
            return [{"step": 1, "action": "Process your request", "tool": "various"}]

    def format_plan_message(self, steps: list[dict]) -> str:
        """
        Format the plan as a user-friendly message.

        Args:
            steps: List of plan steps

        Returns:
            Formatted plan message with emojis
        """
        if not steps:
            return "📋 Here's my plan:\n1️⃣ Process your request\n\nStarting now..."

        lines = ["📋 Here's my plan:"]

        for step in steps[:6]:  # Max 6 steps
            step_num = step.get("step", 1)
            action = step.get("action", "Process step")
            tool = step.get("tool", "various")

            # Get number emoji (1-6)
            if 1 <= step_num <= 6:
                num_emoji = self.NUMBER_EMOJIS[step_num - 1]
            else:
                num_emoji = str(step_num) + "."

            # Get tool emoji
            tool_emoji = self.TOOL_EMOJIS.get(tool, "🔧")

            lines.append(f"{num_emoji}  {action} → {tool_emoji} {tool}")

        lines.append("")
        lines.append("Starting now...")

        return "\n".join(lines)

    def format_completion_summary(
        self,
        steps: list[dict],
        results: list[dict] | list[str]
    ) -> str:
        """
        Format a completion summary after task execution.

        Args:
            steps: List of plan steps
            results: List of tool execution results (aligned with steps)
                    Can be list of dicts with {"result": str, "metadata": dict}
                    or legacy list of strings

        Returns:
            Formatted completion summary
        """
        if not steps:
            return "✅ Done!"

        completed_count = len(steps)
        lines = [f"✅ Done! Completed {completed_count} steps:"]

        for i, step in enumerate(steps):
            action = step.get("action", "Step completed")

            # Get result if available
            result_text = ""
            if i < len(results):
                result_item = results[i]

                # Handle both dict format (with metadata) and legacy string format
                if isinstance(result_item, dict) and "result" in result_item:
                    result = result_item["result"]
                    metadata = result_item.get("metadata", {})

                    # Check metadata for error/success status
                    is_error = not metadata.get("success", True)

                    # Add retry count if multiple attempts were made
                    attempt_info = ""
                    if metadata.get("attempts", 1) > 1:
                        attempt_info = f" (attempt {metadata['attempts']})"
                else:
                    # Legacy string format
                    result = str(result_item)
                    is_error = "error" in result.lower() or "failed" in result.lower()
                    attempt_info = ""

                bullet = "❌" if is_error else "•"

                # Extract useful info from result (truncate)
                result_clean = result.strip()
                # Remove JSON formatting if present
                if result_clean.startswith("{") or result_clean.startswith("["):
                    try:
                        result_obj = json.loads(result_clean)
                        if isinstance(result_obj, dict):
                            # Extract message or first value from multiple possible fields
                            result_clean = str(
                                result_obj.get("message") or
                                result_obj.get("status") or
                                result_obj.get("summary") or
                                result_obj.get("content") or
                                result_obj.get("result") or
                                next(iter(result_obj.values()), "")
                            )

                            # If extracted value is a URL or path, clear it
                            if (
                                result_clean.startswith("http://") or
                                result_clean.startswith("https://") or
                                result_clean.startswith("C:\\") or
                                result_clean.startswith("/") or
                                "://" in result_clean
                            ):
                                result_clean = ""
                    except Exception:
                        pass

                # If result is a URL, file path, or raw bytes info — skip it
                if (
                    result_clean.startswith("http://") or
                    result_clean.startswith("https://") or
                    result_clean.startswith("C:\\") or
                    result_clean.startswith("/") or
                    "bytes to" in result_clean or
                    (len(result_clean) > 0 and result_clean.count("://") > 0)
                ):
                    result_clean = ""  # Don't show it, just show the action with a checkmark

                # Truncate to 40 chars
                if len(result_clean) > 40:
                    result_text = f" — {result_clean[:37]}...{attempt_info}"
                elif result_clean:
                    result_text = f" — {result_clean}{attempt_info}"
            else:
                bullet = "•"

            lines.append(f"{bullet} {action}{result_text}")

        return "\n".join(lines)
