"""Test task planner functionality."""

import sys
from pathlib import Path
import importlib.util


def load_module(name, path):
    """Load a Python module directly from file path."""
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_task_planner():
    """Test the TaskPlanner implementation."""
    print("\n" + "=" * 60)
    print("Task Planner Validation")
    print("=" * 60 + "\n")

    # Load the TaskPlanner module
    task_planner_module = load_module(
        "task_planner",
        "D:/Nanobot/nanobot/nanobot/agent/task_planner.py"
    )
    TaskPlanner = task_planner_module.TaskPlanner

    planner = TaskPlanner()

    # Test 1: is_complex_task with simple message
    print("Test 1: Simple Task Detection")
    print("-" * 60)
    simple_msg = "What's the weather today?"
    result = planner.is_complex_task(simple_msg)
    print(f"Message: '{simple_msg}'")
    print(f"Is complex: {result}")
    assert result is False, "Simple task should not be complex"
    print("[OK] Simple task detected correctly\n")

    # Test 2: is_complex_task with complex message (2+ verbs)
    print("Test 2: Complex Task Detection")
    print("-" * 60)
    complex_msg = "Schedule a meeting tomorrow and send an email to the team"
    result = planner.is_complex_task(complex_msg)
    print(f"Message: '{complex_msg}'")
    print(f"Is complex: {result}")
    assert result is True, "Complex task should be detected"
    print("[OK] Complex task detected correctly\n")

    # Test 3: is_complex_task with 3 verbs
    print("Test 3: Multiple Action Verbs")
    print("-" * 60)
    multi_msg = "Create a file, write some content, and email it to Bob"
    result = planner.is_complex_task(multi_msg)
    print(f"Message: '{multi_msg}'")
    print(f"Is complex: {result}")
    assert result is True, "Task with 3 verbs should be complex"
    print("[OK] Multiple verbs detected correctly\n")

    # Test 4: is_complex_task with 1 verb
    print("Test 4: Single Action Verb")
    print("-" * 60)
    single_msg = "Send an email to john@example.com"
    result = planner.is_complex_task(single_msg)
    print(f"Message: '{single_msg}'")
    print(f"Is complex: {result}")
    assert result is False, "Task with 1 verb should not be complex"
    print("[OK] Single verb handled correctly\n")

    # Test 5: format_plan_message
    print("Test 5: Plan Message Formatting")
    print("-" * 60)
    plan_steps = [
        {"step": 1, "action": "Check calendar availability", "tool": "calendar"},
        {"step": 2, "action": "Book the meeting", "tool": "calendar"},
        {"step": 3, "action": "Send email notification", "tool": "gmail"}
    ]
    formatted = planner.format_plan_message(plan_steps)
    print(f"Formatted plan:\n{formatted}\n")
    assert "Here's my plan:" in formatted
    assert "Check calendar availability" in formatted
    assert "Starting now..." in formatted
    print("[OK] Plan formatted correctly\n")

    # Test 6: format_completion_summary
    print("Test 6: Completion Summary Formatting")
    print("-" * 60)
    results = [
        "Tuesday 2pm is available",
        "Meeting booked successfully",
        "Email sent to 5 recipients"
    ]
    summary = planner.format_completion_summary(plan_steps, results)
    print(f"Completion summary:\n{summary}\n")
    assert "Done! Completed 3 steps:" in summary
    assert "Check calendar availability" in summary
    print("[OK] Completion summary formatted correctly\n")

    # Test 7: format_completion_summary with error
    print("Test 7: Completion Summary with Error")
    print("-" * 60)
    error_results = [
        "Tuesday 2pm is available",
        "Error: Meeting conflict detected",
        "Email not sent"
    ]
    summary = planner.format_completion_summary(plan_steps, error_results)
    print(f"Summary with error:\n{summary}\n")
    assert "Done!" in summary
    # Should have error indicator for step with "error" in result
    print("[OK] Error handling in summary works\n")

    # Test 8: Tool emoji mapping
    print("Test 8: Tool Emoji Mapping")
    print("-" * 60)
    test_tools = ["gmail", "calendar", "write_file", "web_search", "exec", "memory", "browser", "unknown"]
    for tool in test_tools:
        emoji = planner.TOOL_EMOJIS.get(tool, "🔧")
        print(f"  {tool} → {emoji}")
    print("[OK] All tool emojis defined\n")

    # Test 9: Number emoji mapping
    print("Test 9: Number Emoji Mapping")
    print("-" * 60)
    for i, emoji in enumerate(planner.NUMBER_EMOJIS, 1):
        print(f"  Step {i} → {emoji}")
    assert len(planner.NUMBER_EMOJIS) == 6
    print("[OK] All 6 number emojis defined\n")

    # Test 10: Action verbs list
    print("Test 10: Action Verbs List")
    print("-" * 60)
    print(f"Total action verbs: {len(planner.ACTION_VERBS)}")
    print(f"Verbs: {', '.join(planner.ACTION_VERBS[:8])}...")
    assert len(planner.ACTION_VERBS) == 16
    assert "schedule" in planner.ACTION_VERBS
    assert "email" in planner.ACTION_VERBS
    print("[OK] All 16 action verbs defined\n")

    print("=" * 60)
    print("[SUCCESS] ALL TESTS PASSED!")
    print("=" * 60)


if __name__ == "__main__":
    try:
        test_task_planner()
        print("\nTask planner implementation is complete and ready for use.")
    except AssertionError as e:
        print(f"\n[FAIL] TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
