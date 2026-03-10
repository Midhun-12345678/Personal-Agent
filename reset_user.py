"""Reset a user's onboarding state for retesting"""
import asyncio
import shutil
from pathlib import Path
from nanobot.agent.onboarding_state import OnboardingState
from nanobot.memory.store import UserMemoryStore
from nanobot.utils.helpers import get_user_workspace

USER_ID = "c06a06b6"  # Change this to your user ID
BASE_WORKSPACE = Path.home() / ".personal-agent" / "workspace"

async def main():
    workspace = get_user_workspace(BASE_WORKSPACE, USER_ID)
    
    # Reset onboarding state
    state = OnboardingState(workspace)
    await state.reset()
    print(f"Reset onboarding for user {USER_ID}")
    
    # Clear memories and verify
    memory = UserMemoryStore(USER_ID, BASE_WORKSPACE / "users")
    await memory.clear()
    count = await memory.count()
    print(f"Memories remaining after clear: {count}")
    
    if count == 0:
        print("✓ Memories cleared")
    else:
        print("✗ Warning: Some memories remain")
    
    # Clear session history
    session_dir = workspace / "sessions"
    if session_dir.exists():
        shutil.rmtree(session_dir)
        print("✓ Session history cleared")
    else:
        print("No session history to clear")
    
    print(f"\n✓ Reset complete - user {USER_ID} is ready for fresh onboarding")

if __name__ == "__main__":
    asyncio.run(main())
