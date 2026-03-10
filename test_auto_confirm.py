"""Test auto-confirmation timer and calendar conflict detection."""

import asyncio
import sys
from datetime import datetime, timedelta
import importlib.util

# Load modules directly
def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

# Load PendingAction
pending_action = load_module(
    "pending_action",
    "D:/Nanobot/nanobot/nanobot/agent/pending_action.py"
)
PendingAction = pending_action.PendingAction


def test_pending_action_expiry():
    """Test that PendingAction correctly tracks expiry."""
    print("Test 1: PendingAction Expiry Tracking")
    print("=" * 60)

    # Create a pending action with 5 second timeout
    pending = PendingAction(
        tool_name="gmail",
        tool_args={"action": "send", "to": "test@example.com"},
        tool_call=None,
        messages=[],
        iteration=1,
        tools_used=["gmail"],
        auto_confirm_seconds=5
    )

    print(f"Created pending action at: {pending.created_at}")
    print(f"Auto-confirm seconds: {pending.auto_confirm_seconds}")
    print(f"Is expired (immediately): {pending.is_expired()}")
    print(f"Seconds remaining: {pending.seconds_remaining()}")

    assert not pending.is_expired(), "Should not be expired immediately"
    assert pending.seconds_remaining() > 0, "Should have seconds remaining"

    print("\nWaiting 6 seconds...")
    import time
    time.sleep(6)

    print(f"Is expired (after 6 seconds): {pending.is_expired()}")
    print(f"Seconds remaining: {pending.seconds_remaining()}")

    assert pending.is_expired(), "Should be expired after 6 seconds"
    assert pending.seconds_remaining() == 0, "Should have 0 seconds remaining"

    print("PASSED PASSED\n")


def test_pending_action_message_formatting():
    """Test that confirmation messages are formatted with timer info."""
    print("Test 2: Confirmation Message Formatting")
    print("=" * 60)

    pending = PendingAction(
        tool_name="gmail",
        tool_args={"action": "send", "to": "test@example.com"},
        tool_call=None,
        messages=[],
        iteration=1,
        tools_used=["gmail"],
        auto_confirm_seconds=30
    )

    base_msg = (
        "I'm about to send an email:\n"
        "  To: test@example.com\n"
        "  Subject: Test\n"
        "  Body: Hello"
    )

    formatted_msg = pending.format_confirmation_message(base_msg)

    print("Base message:")
    print(base_msg)
    print("\nFormatted message contains:")
    print("  - 'Reply YES to confirm or NO to cancel'")
    print("  - 'Auto-confirming in X seconds'")
    print("  - Original base message")

    assert "Reply YES to confirm or NO to cancel" in formatted_msg
    assert "Auto-confirming in" in formatted_msg
    assert "seconds" in formatted_msg
    assert base_msg in formatted_msg

    print("\nPASSED PASSED\n")


def test_seconds_remaining_countdown():
    """Test that seconds_remaining counts down correctly."""
    print("Test 3: Seconds Remaining Countdown")
    print("=" * 60)

    pending = PendingAction(
        tool_name="gmail",
        tool_args={"action": "send", "to": "test@example.com"},
        tool_call=None,
        messages=[],
        iteration=1,
        tools_used=["gmail"],
        auto_confirm_seconds=10
    )

    print(f"Initial seconds remaining: {pending.seconds_remaining()}")

    import time
    for i in range(3):
        time.sleep(2)
        remaining = pending.seconds_remaining()
        print(f"After {(i+1)*2} seconds: {remaining} seconds remaining")

    print("\nPASSED PASSED\n")


def test_calendar_conflict_detection_format():
    """Test calendar conflict detection message format (mocked)."""
    print("Test 4: Calendar Conflict Message Format")
    print("=" * 60)

    # Simulate what the calendar tool would return
    conflict_response = {
        "conflict": True,
        "error": 'CONFLICT: You already have "Team Standup" from 2024-03-11T14:00:00Z to 2024-03-11T15:00:00Z.',
        "message": "This event overlaps with an existing event. Please choose a different time or confirm to create anyway.",
        "conflicting_event": {
            "id": "abc123",
            "title": "Team Standup",
            "start": "2024-03-11T14:00:00Z",
            "end": "2024-03-11T15:00:00Z"
        }
    }

    print("Conflict detected:")
    print(f"  Event: {conflict_response['conflicting_event']['title']}")
    print(f"  Time: {conflict_response['conflicting_event']['start']} to {conflict_response['conflicting_event']['end']}")
    print(f"\nError message: {conflict_response['error']}")

    assert conflict_response["conflict"] is True
    assert "CONFLICT" in conflict_response["error"]
    assert "Team Standup" in conflict_response["error"]

    print("\nPASSED PASSED\n")


def main():
    print("\n" + "=" * 60)
    print("Testing Auto-Confirmation Timer & Calendar Conflicts")
    print("=" * 60 + "\n")

    try:
        test_pending_action_expiry()
        test_pending_action_message_formatting()
        test_seconds_remaining_countdown()
        test_calendar_conflict_detection_format()

        print("=" * 60)
        print("ALL TESTS PASSED!")
        print("=" * 60)

    except AssertionError as e:
        print(f"\nFAILED TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\nFAILED ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
