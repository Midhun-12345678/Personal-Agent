"""Test memory tool functionality."""

import asyncio
import sys
from pathlib import Path
import tempfile
import importlib.util


def load_module(name, path):
    """Load a Python module directly from file path."""
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


async def test_memory_tool():
    """Test the MemoryTool implementation."""
    print("\n" + "=" * 60)
    print("Testing Memory Tool")
    print("=" * 60 + "\n")

    # Load the MemoryTool module
    memory_tool_module = load_module(
        "memory_tool",
        "D:/Nanobot/nanobot/nanobot/agent/tools/memory_tool.py"
    )
    MemoryTool = memory_tool_module.MemoryTool

    # Create a temporary workspace for testing
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir) / "test_workspace"
        workspace.mkdir()

        # Initialize the memory tool
        tool = MemoryTool(user_id="test_user", workspace=workspace)

        print("Test 1: Tool Properties")
        print("=" * 60)
        print(f"Tool name: {tool.name}")
        print(f"Tool description: {tool.description}")
        print(f"Parameters: {list(tool.parameters['properties'].keys())}")
        assert tool.name == "memory"
        assert "action" in tool.parameters["properties"]
        print("PASSED\n")

        print("Test 2: Read Empty Memory")
        print("=" * 60)
        result = await tool.execute(action="read")
        print(f"Result: {result}")
        assert "No memories stored yet" in result
        print("PASSED\n")

        print("Test 3: Write to Memory")
        print("=" * 60)
        result = await tool.execute(
            action="write",
            category="profile",
            fact="User is a software engineer"
        )
        print(f"Result: {result}")
        assert "Remembered" in result
        print("PASSED\n")

        print("Test 4: Write Another Memory")
        print("=" * 60)
        result = await tool.execute(
            action="write",
            category="preference",
            fact="Prefers dark mode interfaces"
        )
        print(f"Result: {result}")
        assert "Remembered" in result
        print("PASSED\n")

        print("Test 5: Read Memory File")
        print("=" * 60)
        result = await tool.execute(action="read")
        print(f"Result preview: {result[:200]}...")
        assert "software engineer" in result.lower()
        assert "dark mode" in result.lower()
        print("PASSED\n")

        print("Test 6: Summarize Memory")
        print("=" * 60)
        result = await tool.execute(action="summarize")
        print(f"Result: {result}")
        # Should have profile and preference
        assert "Profile:" in result or "Preferences:" in result or "don't know much" in result
        print("PASSED\n")

        print("Test 7: Error Handling - Missing Required Parameter")
        print("=" * 60)
        result = await tool.execute(action="write")  # Missing 'fact'
        print(f"Result: {result}")
        assert "error" in result.lower()
        print("PASSED\n")

        print("Test 8: Verify MEMORY.md File Structure")
        print("=" * 60)
        memory_file = workspace / "memory" / "MEMORY.md"
        assert memory_file.exists(), "MEMORY.md should exist"
        content = memory_file.read_text()
        print(f"File content preview:\n{content[:300]}...")
        assert "## Profile" in content or "## Preferences" in content
        print("PASSED\n")

        print("=" * 60)
        print("ALL TESTS PASSED!")
        print("=" * 60)


if __name__ == "__main__":
    try:
        asyncio.run(test_memory_tool())
    except Exception as e:
        print(f"\nFAILED ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
