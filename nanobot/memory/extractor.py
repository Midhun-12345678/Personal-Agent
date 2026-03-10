"""Memory extraction from conversations using LLM."""

import json
from typing import TYPE_CHECKING, Any

from loguru import logger

if TYPE_CHECKING:
    from nanobot.providers.base import LLMProvider


EXTRACTION_SYSTEM_PROMPT = """You are a memory extraction system. Given a conversation turn, extract important facts about the user worth remembering long-term.

Return JSON array only, no markdown. Each item must have:
- "text": The fact to remember (clear, standalone statement)
- "category": One of "profile", "goal", "preference", "task", "general"

Categories:
- profile: Personal info (name, job, location, relationships)
- goal: Short or long-term objectives
- preference: Likes, dislikes, habits, preferences
- task: Specific tasks or action items mentioned
- general: Other noteworthy information

If nothing worth remembering, return [].

Examples:
Input: "User: I work as a software engineer at Google.\nAgent: That's great! How do you like it?"
Output: [{"text": "User works as a software engineer at Google", "category": "profile"}]

Input: "User: Can you check the weather?\nAgent: It's 72°F and sunny."
Output: []

Input: "User: I want to learn Spanish this year and also save $10k.\nAgent: Those are great goals!"
Output: [{"text": "User wants to learn Spanish this year", "category": "goal"}, {"text": "User wants to save $10,000 this year", "category": "goal"}]"""


class MemoryExtractor:
    """Extracts memorable facts from conversations using LLM."""

    def __init__(self, provider: "LLMProvider", model: str | None = None):
        """Initialize the extractor.
        
        Args:
            provider: LLM provider for extraction calls
            model: Model to use (defaults to provider's default)
        """
        self.provider = provider
        self.model = model

    async def extract(self, conversation_turn: str) -> list[dict[str, Any]]:
        """Extract memorable facts from a conversation turn.
        
        Args:
            conversation_turn: The conversation text to analyze
                Format: "User: {message}\nAgent: {response}"
                
        Returns:
            List of extracted memories with 'text' and 'category' keys
        """
        if not conversation_turn or not conversation_turn.strip():
            return []

        try:
            response = await self.provider.chat(
                messages=[
                    {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
                    {"role": "user", "content": conversation_turn},
                ],
                model=self.model,
                temperature=0.1,  # Low temp for consistent extraction
                max_tokens=1024,
            )

            if not response.content:
                return []

            # Parse JSON response
            content = response.content.strip()
            
            # Handle markdown code blocks if present
            if content.startswith("```"):
                lines = content.split("\n")
                content = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])
            
            memories = json.loads(content)
            
            if not isinstance(memories, list):
                logger.warning("Memory extraction returned non-list: {}", type(memories))
                return []

            # Validate and filter results
            valid_categories = {"profile", "goal", "preference", "task", "general"}
            validated = []
            
            for mem in memories:
                if not isinstance(mem, dict):
                    continue
                if "text" not in mem or not mem["text"]:
                    continue
                    
                category = mem.get("category", "general")
                if category not in valid_categories:
                    category = "general"
                    
                validated.append({
                    "text": str(mem["text"]).strip(),
                    "category": category,
                })

            logger.debug(
                "Extracted {} memories from conversation",
                len(validated)
            )
            return validated

        except json.JSONDecodeError as e:
            logger.warning("Failed to parse memory extraction JSON: {}", e)
            return []
        except Exception as e:
            logger.error("Memory extraction failed: {}", e)
            return []
