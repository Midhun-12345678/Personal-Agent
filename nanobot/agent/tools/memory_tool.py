"""Memory tool: Read, write, search, and summarize user's persistent memory."""

import json
from pathlib import Path
from typing import Any

from loguru import logger

from nanobot.agent.tools.base import Tool
from nanobot.memory.store import UserMemoryStore


class MemoryTool(Tool):
    """Tool to manage user's persistent memory and preferences.

    Provides read/write access to the MEMORY.md file and semantic search
    via ChromaDB vector store.
    """

    def __init__(self, user_id: str, workspace: Path):
        """Initialize memory tool.

        Args:
            user_id: User identifier for isolated memory
            workspace: User's workspace path (contains memory/ subdirectory)
        """
        self.user_id = user_id
        self.workspace = workspace
        self.memory_file = workspace / "memory" / "MEMORY.md"

        # Initialize semantic memory store
        # Store at workspace.parent so ChromaDB is centralized across users
        self.memory_store = UserMemoryStore(user_id, workspace.parent)

    @property
    def name(self) -> str:
        return "memory"

    @property
    def description(self) -> str:
        return "Read, write, search, or summarize the user's persistent memory and preferences"

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["read", "write", "search", "summarize"],
                    "description": "Action to perform on user memory"
                },
                "category": {
                    "type": "string",
                    "enum": ["profile", "goal", "preference", "task", "general"],
                    "description": "Memory category (used with write action)"
                },
                "fact": {
                    "type": "string",
                    "description": "The fact to store (required when action=write)"
                },
                "query": {
                    "type": "string",
                    "description": "Semantic search query (required when action=search)"
                }
            },
            "required": ["action"]
        }

    async def execute(
        self,
        action: str,
        category: str = "general",
        fact: str = "",
        query: str = "",
        **kwargs: Any
    ) -> str:
        """Execute the memory tool action."""
        try:
            if action == "read":
                return await self._read_memory()
            elif action == "write":
                if not fact:
                    return json.dumps({"error": "fact is required for write action"})
                return await self._write_memory(fact, category)
            elif action == "search":
                if not query:
                    return json.dumps({"error": "query is required for search action"})
                return await self._search_memory(query)
            elif action == "summarize":
                return await self._summarize_memory()
            else:
                return json.dumps({"error": f"Unknown action: {action}"})
        except Exception as e:
            logger.error("Memory tool error (action={}): {}", action, e)
            return json.dumps({"error": f"Memory operation failed: {str(e)}"})

    async def _read_memory(self) -> str:
        """Read the MEMORY.md file."""
        if not self.memory_file.exists():
            return "No memories stored yet."

        try:
            content = self.memory_file.read_text(encoding="utf-8")
            if not content.strip():
                return "No memories stored yet."

            return f"📋 Your Memory:\n\n{content}"
        except Exception as e:
            logger.error("Error reading MEMORY.md: {}", e)
            return f"Error reading memory file: {str(e)}"

    async def _write_memory(self, fact: str, category: str) -> str:
        """Write a fact to both MEMORY.md and ChromaDB."""
        # Ensure memory directory exists
        self.memory_file.parent.mkdir(parents=True, exist_ok=True)

        # Map category to section header
        category_headers = {
            "profile": "## Profile",
            "goal": "## Goals",
            "preference": "## Preferences",
            "task": "## Tasks",
            "general": "## General"
        }

        header = category_headers.get(category, "## General")

        # Read existing content
        if self.memory_file.exists():
            content = self.memory_file.read_text(encoding="utf-8")
        else:
            content = "# Personal Memory\n\n"

        # Find or create the category section
        if header in content:
            # Section exists - append to it
            section_start = content.index(header)
            # Find the next section or end of file
            next_section = len(content)
            for other_header in category_headers.values():
                if other_header != header and other_header in content:
                    idx = content.index(other_header, section_start + len(header))
                    if idx < next_section:
                        next_section = idx

            # Insert the fact before the next section
            section_content = content[section_start:next_section].rstrip()
            new_content = (
                content[:section_start] +
                section_content + f"\n- {fact}\n\n" +
                content[next_section:]
            )
        else:
            # Section doesn't exist - create it
            new_content = content.rstrip() + f"\n\n{header}\n- {fact}\n"

        # Write back to file
        self.memory_file.write_text(new_content, encoding="utf-8")

        # Also store in ChromaDB for semantic search
        await self.memory_store.save(fact, category=category, source="memory_tool")

        logger.info("Stored memory [{}]: {}", category, fact[:50])

        return f"✅ Remembered: {fact}"

    async def _search_memory(self, query: str) -> str:
        """Search ChromaDB for relevant memories."""
        results = await self.memory_store.search(query, top_k=3)

        if not results:
            return "No matching memories found."

        # Format results
        lines = [f"🔍 Memory search results for '{query}':"]
        for i, result in enumerate(results, 1):
            score = result.get("score", 0.0)
            text = result.get("text", "")
            category = result.get("category", "general")

            # Only show results with reasonable similarity (> 0.3)
            if score > 0.3:
                lines.append(f"{i}. [{category}] {text} (relevance: {score:.2f})")

        if len(lines) == 1:  # Only the header
            return "No matching memories found."

        return "\n".join(lines)

    async def _summarize_memory(self) -> str:
        """Summarize user's profile, preferences, and goals."""
        # Get memories from key categories
        profile_results = []
        preference_results = []
        goal_results = []

        try:
            # Search for profile information
            all_results = await self.memory_store.search("profile name profession", top_k=20)
            for r in all_results:
                if r.get("category") == "profile":
                    profile_results.append(r)
                elif r.get("category") == "preference":
                    preference_results.append(r)
                elif r.get("category") == "goal":
                    goal_results.append(r)

            # If we didn't get enough, try direct category queries
            if len(profile_results) < 3:
                # Use search with category-specific terms
                prof_search = await self.memory_store.search("user profile information", top_k=5)
                profile_results.extend([r for r in prof_search if r.get("category") == "profile"])

            if len(preference_results) < 3:
                pref_search = await self.memory_store.search("preferences likes dislikes", top_k=5)
                preference_results.extend([r for r in pref_search if r.get("category") == "preference"])

            if len(goal_results) < 3:
                goal_search = await self.memory_store.search("goals objectives plans", top_k=5)
                goal_results.extend([r for r in goal_search if r.get("category") == "goal"])

        except Exception as e:
            logger.warning("Error loading memory categories: {}", e)

        # Remove duplicates and limit
        profile_results = list({r["text"]: r for r in profile_results}.values())[:5]
        preference_results = list({r["text"]: r for r in preference_results}.values())[:5]
        goal_results = list({r["text"]: r for r in goal_results}.values())[:5]

        if not profile_results and not preference_results and not goal_results:
            return "I don't know much about you yet. Tell me about yourself!"

        # Build summary
        lines = ["🧠 What I know about you:"]

        if profile_results:
            profile_text = ", ".join([r["text"] for r in profile_results[:3]])
            lines.append(f"Profile: {profile_text}")

        if preference_results:
            pref_text = ", ".join([r["text"] for r in preference_results[:3]])
            lines.append(f"Preferences: {pref_text}")

        if goal_results:
            goal_text = ", ".join([r["text"] for r in goal_results[:3]])
            lines.append(f"Goals: {goal_text}")

        return "\n".join(lines)
