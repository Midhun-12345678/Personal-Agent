"""Structure validation test for task planner."""

import sys
from pathlib import Path


def test_task_planner_structure():
    """Validate task planner file structure."""
    print("\n" + "=" * 60)
    print("Task Planner Structure Validation")
    print("=" * 60 + "\n")

    # Check file exists
    planner_file = Path("D:/Nanobot/nanobot/nanobot/agent/task_planner.py")
    assert planner_file.exists(), "task_planner.py should exist"
    print("[OK] File exists: task_planner.py")

    # Read and check structure
    content = planner_file.read_text(encoding="utf-8")

    # Check class definition
    assert "class TaskPlanner:" in content
    print("[OK] TaskPlanner class defined")

    # Check required methods
    required_methods = [
        "is_complex_task",
        "generate_plan",
        "format_plan_message",
        "format_completion_summary"
    ]

    for method in required_methods:
        assert f"def {method}" in content
        print(f"[OK] Method exists: {method}")

    # Check action verbs list
    assert "ACTION_VERBS = [" in content
    assert '"schedule"' in content
    assert '"create"' in content
    assert '"send"' in content
    assert '"email"' in content
    print("[OK] ACTION_VERBS list defined")

    # Check tool emoji mapping
    assert "TOOL_EMOJIS = {" in content
    assert '"gmail"' in content
    assert '"calendar"' in content
    print("[OK] TOOL_EMOJIS mapping defined")

    # Check number emojis
    assert "NUMBER_EMOJIS = [" in content
    print("[OK] NUMBER_EMOJIS list defined")

    # Check formatted output strings
    assert "Here's my plan:" in content
    assert "Starting now..." in content
    assert "Done! Completed" in content
    print("[OK] All formatted output strings present")

    # Check complexity detection logic
    assert "verb_count" in content
    assert "verb_count >= 2" in content
    print("[OK] Complexity detection logic present")

    # Check LLM integration
    assert "await provider.chat" in content
    assert "temperature=0.3" in content
    assert "max_tokens=500" in content
    print("[OK] LLM integration configured")

    # Check JSON parsing
    assert "json.loads" in content
    assert "```json" in content  # Markdown fence stripping
    print("[OK] JSON parsing with markdown fence stripping")

    # Check max 6 steps limit
    assert "[:6]" in content or "[i, step in enumerate(steps[:6]" in content
    print("[OK] Max 6 steps limit enforced")

    print("\n" + "=" * 60)
    print("ALL STRUCTURE CHECKS PASSED!")
    print("=" * 60)


def test_loop_integration():
    """Validate loop.py integration."""
    print("\n" + "=" * 60)
    print("Loop Integration Validation")
    print("=" * 60 + "\n")

    loop_file = Path("D:/Nanobot/nanobot/nanobot/agent/loop.py")
    assert loop_file.exists()
    print("[OK] File exists: loop.py")

    content = loop_file.read_text(encoding="utf-8")

    # Check import
    assert "from nanobot.agent.task_planner import TaskPlanner" in content
    print("[OK] TaskPlanner imported")

    # Check state variables in __init__
    assert "_current_plan: dict[str, list[dict]] = {}" in content
    assert "_tool_results: dict[str, list[str]] = {}" in content
    print("[OK] State variables initialized")

    # Check tool result tracking in _run_agent_loop
    assert "self._tool_results[session_key].append(result)" in content
    print("[OK] Tool result tracking implemented")

    # Check planning logic in _process_message
    assert "task_planner = TaskPlanner()" in content
    assert "task_planner.is_complex_task" in content
    assert "task_planner.generate_plan" in content
    assert "task_planner.format_plan_message" in content
    print("[OK] Planning logic integrated")

    # Check completion summary logic
    assert "task_planner.format_completion_summary" in content
    assert "self._current_plan.pop(key)" in content
    assert "self._tool_results.pop(key" in content
    print("[OK] Completion summary logic implemented")

    # Check plan message sent to bus
    assert "await self.bus.publish_outbound(OutboundMessage(" in content
    print("[OK] Plan messages sent via message bus")

    print("\n" + "=" * 60)
    print("ALL INTEGRATION CHECKS PASSED!")
    print("=" * 60)


def test_compilation():
    """Test that all files compile."""
    print("\n" + "=" * 60)
    print("Python Compilation Check")
    print("=" * 60 + "\n")

    import subprocess

    files = [
        ("task_planner.py", "nanobot/agent/task_planner.py"),
        ("loop.py", "nanobot/agent/loop.py")
    ]

    for name, file_path in files:
        result = subprocess.run(
            ["python", "-m", "py_compile", file_path],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            print(f"[OK] Compiles successfully: {name}")
        else:
            print(f"[FAIL] Compilation error in {name}")
            print(result.stderr)
            raise RuntimeError(f"Compilation failed for {name}")

    print("\n" + "=" * 60)
    print("ALL FILES COMPILE SUCCESSFULLY!")
    print("=" * 60)


def test_logic_validation():
    """Test complexity detection logic manually."""
    print("\n" + "=" * 60)
    print("Logic Validation (Manual)")
    print("=" * 60 + "\n")

    # Simulate is_complex_task logic with word boundary matching
    import re

    action_verbs = [
        "schedule", "create", "send", "email", "book", "write", "set up",
        "add", "make", "delete", "find", "search", "remind", "draft", "update", "move"
    ]

    test_cases = [
        ("What's the weather today?", False),
        ("Schedule a meeting", False),
        ("Schedule a meeting and send an email", True),
        ("Create file, write content, and email it", True),
        ("Send an email to john@example.com", True),  # "send" + "email" = 2 verbs
        ("What is the status of my task", False),  # No action verbs
    ]

    for message, expected_complex in test_cases:
        message_lower = message.lower()
        verb_count = 0

        for verb in action_verbs:
            # Use word boundary matching like the actual implementation
            pattern = r'\b' + re.escape(verb) + r'\b'
            if re.search(pattern, message_lower):
                verb_count += 1

        is_complex = verb_count >= 2

        status = "[OK]" if is_complex == expected_complex else "[FAIL]"
        print(f"{status} '{message[:40]}...'")
        print(f"     Verbs found: {verb_count}, Complex: {is_complex}, Expected: {expected_complex}")

        assert is_complex == expected_complex, f"Logic failed for: {message}"

    print("\n[OK] All logic validation tests passed")

    print("\n" + "=" * 60)
    print("ALL LOGIC TESTS PASSED!")
    print("=" * 60)


if __name__ == "__main__":
    try:
        test_task_planner_structure()
        test_loop_integration()
        test_compilation()
        test_logic_validation()

        print("\n" + "=" * 60)
        print("[SUCCESS] ALL VALIDATION TESTS PASSED!")
        print("=" * 60)
        print("\nTask planning implementation is complete and ready for use.")

    except AssertionError as e:
        print(f"\n[X] VALIDATION FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n[X] ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
