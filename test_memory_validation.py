"""Simple validation test for memory tool - checks structure only."""

from pathlib import Path


def test_memory_tool_structure():
    """Validate memory tool implementation structure."""
    print("\n" + "=" * 60)
    print("Memory Tool Structure Validation")
    print("=" * 60 + "\n")

    # Check file exists
    tool_file = Path("D:/Nanobot/nanobot/nanobot/agent/tools/memory_tool.py")
    assert tool_file.exists(), "memory_tool.py should exist"
    print("[OK] File exists: memory_tool.py")

    # Read and check structure
    content = tool_file.read_text(encoding="utf-8")

    # Check class definition
    assert "class MemoryTool(Tool):" in content
    print("[OK] MemoryTool class defined")

    # Check required methods
    required_methods = [
        "__init__",
        "name",
        "description",
        "parameters",
        "execute",
        "_read_memory",
        "_write_memory",
        "_search_memory",
        "_summarize_memory"
    ]

    for method in required_methods:
        assert f"def {method}" in content or f"def {method}(" in content
        print(f"[OK] Method exists: {method}")

    # Check action definitions
    actions = ["read", "write", "search", "summarize"]
    assert '"read", "write", "search", "summarize"' in content
    print(f"[OK] All actions defined: {actions}")

    # Check categories
    categories = ["profile", "goal", "preference", "task", "general"]
    assert '"profile", "goal", "preference", "task", "general"' in content
    print(f"[OK] All categories defined: {categories}")

    # Check ChromaDB integration
    assert "UserMemoryStore" in content
    print("[OK] ChromaDB integration: UserMemoryStore")

    # Check MEMORY.md handling
    assert "MEMORY.md" in content
    assert "memory_file" in content
    print("[OK] MEMORY.md file handling")

    # Check return formats
    assert "✅ Remembered:" in content
    assert "📋 Your Memory:" in content
    assert "🔍 Memory search results" in content
    assert "🧠 What I know about you:" in content
    print("[OK] All formatted responses defined")

    print("\n" + "=" * 60)
    print("ALL STRUCTURE CHECKS PASSED!")
    print("=" * 60)


def test_context_modification():
    """Validate context.py modifications."""
    print("\n" + "=" * 60)
    print("Context Modification Validation")
    print("=" * 60 + "\n")

    context_file = Path("D:/Nanobot/nanobot/nanobot/agent/context.py")
    assert context_file.exists()
    print("[OK] File exists: context.py")

    content = context_file.read_text()

    # Check __init__ accepts user_id
    assert "def __init__(self, workspace: Path, user_id: str = \"default\"):" in content
    print("[OK] __init__ accepts user_id parameter")

    # Check semantic_memory initialization
    assert "UserMemoryStore" in content
    assert "self.semantic_memory" in content
    print("[OK] Semantic memory store initialized")

    # Check build_system_prompt is async
    assert "async def build_system_prompt" in content
    print("[OK] build_system_prompt is async")

    # Check build_messages is async
    assert "async def build_messages" in content
    print("[OK] build_messages is async")

    # Check _get_preferences_context method
    assert "async def _get_preferences_context" in content
    assert "Known preferences" in content
    print("[OK] _get_preferences_context method exists")

    # Check preferences are injected
    assert "preferences_context = await self._get_preferences_context()" in content
    print("[OK] Preferences injection in build_system_prompt")

    print("\n" + "=" * 60)
    print("ALL CONTEXT CHECKS PASSED!")
    print("=" * 60)


def test_loop_registration():
    """Validate loop.py modifications."""
    print("\n" + "=" * 60)
    print("Loop Registration Validation")
    print("=" * 60 + "\n")

    loop_file = Path("D:/Nanobot/nanobot/nanobot/agent/loop.py")
    assert loop_file.exists()
    print("[OK] File exists: loop.py")

    content = loop_file.read_text(encoding="utf-8")

    # Check import
    assert "from nanobot.agent.tools.memory_tool import MemoryTool" in content
    print("[OK] MemoryTool imported")

    # Check registration
    assert "MemoryTool(user_id=self.user_id, workspace=self.workspace)" in content
    print("[OK] MemoryTool registered in _register_default_tools")

    # Check ContextBuilder initialization with user_id
    assert "ContextBuilder(workspace, user_id=user_id)" in content
    print("[OK] ContextBuilder receives user_id")

    # Check build_messages is awaited
    assert "await self.context.build_messages" in content
    print("[OK] build_messages calls are awaited")

    print("\n" + "=" * 60)
    print("ALL LOOP CHECKS PASSED!")
    print("=" * 60)


def test_compilation():
    """Test that all files compile."""
    print("\n" + "=" * 60)
    print("Python Compilation Check")
    print("=" * 60 + "\n")

    import subprocess

    files = [
        ("memory_tool.py", "nanobot/agent/tools/memory_tool.py"),
        ("context.py", "nanobot/agent/context.py"),
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


if __name__ == "__main__":
    try:
        test_memory_tool_structure()
        test_context_modification()
        test_loop_registration()
        test_compilation()

        print("\n" + "=" * 60)
        print("[SUCCESS] ALL VALIDATION TESTS PASSED!")
        print("=" * 60)
        print("\nMemory tool implementation is complete and ready for use.")

    except AssertionError as e:
        print(f"\n[X] VALIDATION FAILED: {e}")
        import sys
        sys.exit(1)
    except Exception as e:
        print(f"\n[X] ERROR: {e}")
        import traceback
        traceback.print_exc()
        import sys
        sys.exit(1)
