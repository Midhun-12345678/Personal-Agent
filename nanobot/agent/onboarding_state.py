"""Persistent state storage for onboarding."""

import json
from pathlib import Path

from loguru import logger


class OnboardingState:
    """Stores onboarding progress to survive server restarts.
    
    Persists the answers collected so far to a JSON file in the user's workspace.
    """

    def __init__(self, workspace: Path):
        """Initialize the onboarding state store.
        
        Args:
            workspace: User's workspace directory
        """
        self.workspace = Path(workspace)
        self.state_file = self.workspace / "onboarding.json"

    async def load(self) -> dict:
        """Load onboarding answers from file.
        
        Returns:
            Dict of field -> answer, or empty dict if not found
        """
        try:
            if self.state_file.exists():
                data = json.loads(self.state_file.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    return data.get("answers", {})
        except Exception as e:
            logger.warning("Failed to load onboarding state: {}", e)
        
        return {}

    async def save(self, answers: dict) -> None:
        """Save onboarding answers to file.
        
        Args:
            answers: Dict of field -> answer to persist
        """
        try:
            self.workspace.mkdir(parents=True, exist_ok=True)
            data = {"answers": answers, "version": 1}
            self.state_file.write_text(
                json.dumps(data, indent=2, ensure_ascii=False),
                encoding="utf-8"
            )
            logger.debug("Saved onboarding state: {} fields", len(answers))
        except Exception as e:
            logger.error("Failed to save onboarding state: {}", e)

    async def clear(self) -> None:
        """Clear the onboarding state file."""
        try:
            if self.state_file.exists():
                self.state_file.unlink()
                logger.debug("Cleared onboarding state")
        except Exception as e:
            logger.warning("Failed to clear onboarding state: {}", e)

    async def is_complete(self) -> bool:
        """Check if onboarding state indicates completion.
        
        Returns:
            True if all required fields are present
        """
        required_fields = {"name", "profession", "goals", "schedule", "preferences"}
        answers = await self.load()
        return required_fields.issubset(answers.keys())

    async def reset(self) -> None:
        """Reset/clear onboarding state for retesting."""
        if self.state_file.exists():
            self.state_file.unlink()
        logger.debug("Onboarding state reset")
