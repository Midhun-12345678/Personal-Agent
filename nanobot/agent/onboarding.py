"""Onboarding flow for new users."""

from typing import TYPE_CHECKING

from loguru import logger

if TYPE_CHECKING:
    from nanobot.memory import UserMemoryStore


class OnboardingFlow:
    """Manages the onboarding conversation flow for new users.
    
    Asks a series of questions to build the user's profile and seeds
    their semantic memory store with the information gathered.
    """

    INTRO_MESSAGE = """Hey! 👋 I'm Nanobot, your personal AI automation assistant.

I can help you with:
• Reading and sending emails (Gmail)
• Managing your calendar events
• Searching the web for information
• Creating and editing files
• Running commands and automating tasks
• Remembering important things about you

Let me get to know you with a few quick questions so I can help you better!"""

    ONBOARDING_QUESTIONS = [
        {
            "field": "name",
            "question": "First off — what's your name?"
        },
        {
            "field": "profession",
            "question": "Nice to meet you {name}! What do you do for work?"
        },
        {
            "field": "goals",
            "question": "What are your top 1-2 goals right now that you'd love help with?"
        },
        {
            "field": "schedule",
            "question": "Are you more of a morning person or evening person? And roughly what does your day look like?"
        },
        {
            "field": "preferences",
            "question": "Last one — anything you want me to always remember about how you like to work or communicate?"
        },
    ]

    def __init__(self, memory_store: "UserMemoryStore"):
        """Initialize the onboarding flow.
        
        Args:
            memory_store: The user's semantic memory store
        """
        self.memory_store = memory_store

    async def is_onboarded(self) -> bool:
        """Check if the user has already completed onboarding.
        
        Returns:
            True if user has profile memories for all questions, False otherwise
        """
        try:
            profiles = await self.memory_store.get_profile()
            # Require profile memories for all onboarding questions
            return len(profiles) >= len(self.ONBOARDING_QUESTIONS)
        except Exception as e:
            logger.warning("Failed to check onboarding status: {}", e)
            return False

    def _get_missing_fields(self, answers_so_far: dict) -> list[str]:
        """Get list of fields that haven't been answered yet.
        
        Args:
            answers_so_far: Dict of field -> answer collected so far
            
        Returns:
            List of field names still needing answers
        """
        all_fields = [q["field"] for q in self.ONBOARDING_QUESTIONS]
        return [f for f in all_fields if f not in answers_so_far]

    async def get_next_question(self, answers_so_far: dict) -> str | None:
        """Get the next onboarding question to ask.
        
        Args:
            answers_so_far: Dict of field -> answer collected so far
            
        Returns:
            The next question string with placeholders filled, or None if complete
        """
        missing = self._get_missing_fields(answers_so_far)
        
        if not missing:
            return None
        
        next_field = missing[0]
        
        for q in self.ONBOARDING_QUESTIONS:
            if q["field"] == next_field:
                question = q["question"]
                # Substitute {name} if we have it
                if "{name}" in question and "name" in answers_so_far:
                    question = question.replace("{name}", answers_so_far["name"])
                return question
        
        return None

    async def save_answer(self, field: str, answer: str, answers_so_far: dict) -> None:
        """Save an onboarding answer to the memory store.
        
        Args:
            field: The field name (name, profession, etc.)
            answer: The user's answer
            answers_so_far: Current answers dict (used to check if all complete)
        """
        # Save the individual profile field
        await self.memory_store.save_profile(field, answer)
        logger.info("Saved onboarding answer: {} = '{}'", field, answer[:50])
        
        # Check if this completes onboarding
        updated_answers = {**answers_so_far, field: answer}
        missing = self._get_missing_fields(updated_answers)
        
        if not missing:
            # All fields answered - save a combined summary
            summary_parts = []
            for q in self.ONBOARDING_QUESTIONS:
                f = q["field"]
                if f in updated_answers:
                    summary_parts.append(f"{f}={updated_answers[f]}")
            
            summary = "User profile: " + ", ".join(summary_parts)
            await self.memory_store.save(summary, category="profile", source="onboarding")
            logger.info("Onboarding complete, saved profile summary")

    async def run_step(
        self,
        user_message: str,
        answers_so_far: dict
    ) -> tuple[str | None, dict, bool]:
        """Run one step of the onboarding conversation.
        
        Takes the user's message, figures out which question it answers,
        saves the answer, and returns the next question.
        
        Args:
            user_message: The user's latest message
            answers_so_far: Dict of answers collected so far
            
        Returns:
            Tuple of (next_question_or_none, updated_answers, is_complete)
        """
        # Figure out which field is being answered (first missing one)
        missing = self._get_missing_fields(answers_so_far)
        
        if not missing:
            # Already complete
            return None, answers_so_far, True
        
        # The user is answering the first missing field
        current_field = missing[0]
        
        # Save the answer
        await self.save_answer(current_field, user_message, answers_so_far)
        
        # Update answers
        updated_answers = {**answers_so_far, current_field: user_message}
        
        # Get next question
        next_question = await self.get_next_question(updated_answers)
        
        is_complete = next_question is None
        
        return next_question, updated_answers, is_complete
