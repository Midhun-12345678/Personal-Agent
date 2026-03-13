"""Agent loop: the core processing engine."""

from __future__ import annotations

import asyncio
import json
import re
import time
import weakref
from contextlib import AsyncExitStack
from pathlib import Path
from typing import TYPE_CHECKING, Any, Awaitable, Callable

from loguru import logger

from nanobot.agent.context import ContextBuilder
from nanobot.agent.error_recovery import ErrorRecovery
from nanobot.agent.intent_classifier import IntentClassifier
from nanobot.agent.memory import MemoryStore
from nanobot.agent.pending_action import PendingAction
from nanobot.agent.subagent import SubagentManager
from nanobot.agent.task_planner import TaskPlanner
from nanobot.agent.usage_logger import UsageLogger
from nanobot.memory import UserMemoryStore, MemoryExtractor
from nanobot.agent.tools.cron import CronTool
from nanobot.agent.tools.filesystem import EditFileTool, ListDirTool, ReadFileTool, WriteFileTool
from nanobot.agent.tools.message import MessageTool
from nanobot.agent.tools.registry import ToolRegistry
from nanobot.agent.tools.shell import ExecTool
from nanobot.agent.tools.spawn import SpawnTool
from nanobot.agent.tools.web import WebFetchTool, WebSearchTool
from nanobot.agent.tools.gmail_tool import GmailTool
from nanobot.agent.tools.calendar_tool import CalendarTool
from nanobot.agent.tools.browser_tool import BrowserTool
from nanobot.agent.tools.notify_file import NotifyFileTool
from nanobot.agent.tools.memory_tool import MemoryTool
from nanobot.bus.events import InboundMessage, OutboundMessage
from nanobot.bus.queue import MessageBus
from nanobot.providers.base import LLMProvider
from nanobot.session.manager import Session, SessionManager
from nanobot.utils.helpers import get_user_workspace

if TYPE_CHECKING:
    from nanobot.config.schema import ChannelsConfig, ExecToolConfig
    from nanobot.cron.service import CronService


class AgentLoop:
    """
    The agent loop is the core processing engine.

    It:
    1. Receives messages from the bus
    2. Builds context with history, memory, skills
    3. Calls the LLM
    4. Executes tool calls
    5. Sends responses back
    """

    _TOOL_RESULT_MAX_CHARS = 500
    
    # Welcome message for new users (first message in session)
    WELCOME_INTRO = """Hey! 👋 I'm YourBot, your personal AI assistant.

I can help you with:
• 📧 Reading and sending emails (Gmail)
• 📅 Managing your calendar events
• 🔍 Searching the web for information
• 📁 Creating and editing files
• 💻 Running commands and automating tasks
• 🧠 Remembering important things about you

What can I help you with today?"""

    def _clean_message_history(self, messages: list[dict]) -> list[dict]:
        """Remove orphaned tool messages that break OpenAI message format."""
        if not messages:
            return messages
        
        cleaned = []
        i = 0
        while i < len(messages):
            msg = messages[i]
            
            # Case 1: assistant message with tool_calls
            # Check if ALL tool_call_ids have matching tool responses after it
            if msg.get("role") == "assistant" and msg.get("tool_calls"):
                tool_call_ids = {tc["id"] for tc in msg["tool_calls"]}
                # Look ahead for matching tool responses
                following_tool_ids = set()
                j = i + 1
                while j < len(messages) and messages[j].get("role") == "tool":
                    following_tool_ids.add(messages[j].get("tool_call_id"))
                    j += 1
                
                if tool_call_ids.issubset(following_tool_ids):
                    # All tool calls have responses — keep this and following tools
                    cleaned.append(msg)
                else:
                    # Incomplete tool call chain — skip this assistant msg 
                    # and skip any following tool messages
                    while i + 1 < len(messages) and messages[i+1].get("role") == "tool":
                        i += 1
                    i += 1
                    continue
            
            # Case 2: tool message with no preceding assistant tool_calls
            elif msg.get("role") == "tool":
                prev = cleaned[-1] if cleaned else None
                if not prev or prev.get("role") != "assistant" or not prev.get("tool_calls"):
                    i += 1
                    continue
            
            cleaned.append(msg)
            i += 1
        
        return cleaned

    def __init__(
        self,
        bus: MessageBus,
        provider: LLMProvider,
        workspace: Path,
        user_id: str = "default",
        model: str | None = None,
        max_iterations: int = 40,
        temperature: float = 0.1,
        max_tokens: int = 4096,
        memory_window: int = 100,
        reasoning_effort: str | None = None,
        brave_api_key: str | None = None,
        serp_api_key: str | None = None,
        web_proxy: str | None = None,
        exec_config: ExecToolConfig | None = None,
        cron_service: CronService | None = None,
        restrict_to_workspace: bool = False,
        session_manager: SessionManager | None = None,
        mcp_servers: dict | None = None,
        channels_config: ChannelsConfig | None = None,
    ):
        from nanobot.config.schema import ExecToolConfig
        # Resolve per-user workspace
        workspace = get_user_workspace(workspace, user_id)
        
        self.bus = bus
        self.channels_config = channels_config
        self.provider = provider
        self.workspace = workspace
        self.user_id = user_id
        self.model = model or provider.get_default_model()
        self.max_iterations = max_iterations
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.memory_window = memory_window
        self.reasoning_effort = reasoning_effort
        self.brave_api_key = brave_api_key
        self.serp_api_key = serp_api_key
        self.web_proxy = web_proxy
        self.exec_config = exec_config or ExecToolConfig()
        self.cron_service = cron_service
        self.restrict_to_workspace = restrict_to_workspace

        self.context = ContextBuilder(workspace, user_id=user_id)
        self.sessions = session_manager or SessionManager(workspace)
        self.tools = ToolRegistry()
        self.subagents = SubagentManager(
            provider=provider,
            workspace=workspace,
            bus=bus,
            model=self.model,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            reasoning_effort=reasoning_effort,
            brave_api_key=brave_api_key,
            serp_api_key=serp_api_key,
            web_proxy=web_proxy,
            exec_config=self.exec_config,
            restrict_to_workspace=restrict_to_workspace,
        )

        self._running = False
        self._mcp_servers = mcp_servers or {}
        self._mcp_stack: AsyncExitStack | None = None
        self._mcp_connected = False
        self._mcp_connecting = False
        self._consolidating: set[str] = set()  # Session keys with consolidation in progress
        self._consolidation_tasks: set[asyncio.Task] = set()  # Strong refs to in-flight tasks
        self._consolidation_locks: weakref.WeakValueDictionary[str, asyncio.Lock] = weakref.WeakValueDictionary()
        self._active_tasks: dict[str, list[asyncio.Task]] = {}  # session_key -> tasks
        self._processing_lock = asyncio.Lock()

        # Semantic memory engine (per-user)
        # Store in workspace.parent so chromadb is centralized but collections are per-user
        self.semantic_memory = UserMemoryStore(user_id, workspace.parent)
        self.memory_extractor = MemoryExtractor(provider, model=self.model)

        # Intent classification and confirmation tracking
        self.intent_classifier = IntentClassifier()
        self._pending_confirmations: dict[str, PendingAction] = {}  # session_key -> PendingAction
        self._expiry_check_task: asyncio.Task | None = None

        # Error recovery for tool execution failures
        self.error_recovery = ErrorRecovery()

        # Usage logging for dashboard
        self.usage_logger = UsageLogger(self.workspace.parent.parent, self.user_id)

        # Task planning for complex multi-step tasks
        self._current_plan: dict[str, list[dict]] = {}  # session_key -> plan steps
        self._tool_results: dict[str, list[dict]] = {}  # session_key -> tool results with metadata

        self._register_default_tools()

    def _register_default_tools(self) -> None:
        """Register the default set of tools."""
        allowed_dir = self.workspace if self.restrict_to_workspace else None
        for cls in (ReadFileTool, WriteFileTool, EditFileTool, ListDirTool):
            self.tools.register(cls(workspace=self.workspace, allowed_dir=allowed_dir))
        self.tools.register(ExecTool(
            working_dir=str(self.workspace),
            timeout=self.exec_config.timeout,
            restrict_to_workspace=self.restrict_to_workspace,
            path_append=self.exec_config.path_append,
        ))
        self.tools.register(WebSearchTool(api_key=self.brave_api_key, serp_api_key=self.serp_api_key, proxy=self.web_proxy))
        self.tools.register(WebFetchTool(proxy=self.web_proxy))
        self.tools.register(MessageTool(send_callback=self.bus.publish_outbound))
        self.tools.register(SpawnTool(manager=self.subagents))
        if self.cron_service:
            self.tools.register(CronTool(self.cron_service))

        # Action tools
        self.tools.register(GmailTool(user_workspace=self.workspace))
        self.tools.register(CalendarTool(user_workspace=self.workspace))
        self.tools.register(BrowserTool(provider=self.provider))
        self.tools.register(NotifyFileTool(
            send_callback=self.bus.publish_outbound,
            user_id=self.user_id,
        ))
        self.tools.register(MemoryTool(user_id=self.user_id, workspace=self.workspace))

    async def _connect_mcp(self) -> None:
        """Connect to configured MCP servers (one-time, lazy)."""
        if self._mcp_connected or self._mcp_connecting or not self._mcp_servers:
            return
        self._mcp_connecting = True
        from nanobot.agent.tools.mcp import connect_mcp_servers
        try:
            self._mcp_stack = AsyncExitStack()
            await self._mcp_stack.__aenter__()
            await connect_mcp_servers(self._mcp_servers, self.tools, self._mcp_stack)
            self._mcp_connected = True
        except Exception as e:
            logger.error("Failed to connect MCP servers (will retry next message): {}", e)
            if self._mcp_stack:
                try:
                    await self._mcp_stack.aclose()
                except Exception:
                    pass
                self._mcp_stack = None
        finally:
            self._mcp_connecting = False

    def _set_tool_context(self, channel: str, chat_id: str, message_id: str | None = None) -> None:
        """Update context for all tools that need routing info."""
        for name in ("message", "spawn", "cron", "notify_file"):
            if tool := self.tools.get(name):
                if hasattr(tool, "set_context"):
                    tool.set_context(channel, chat_id, *([message_id] if name == "message" else []))

    def _make_bus_progress(self, msg: InboundMessage) -> Callable[..., Awaitable[None]]:
        """Create a progress callback that publishes to the message bus."""
        async def _bus_progress(content: str, *, tool_hint: bool = False) -> None:
            meta = dict(msg.metadata or {})
            meta["_progress"] = True
            meta["_tool_hint"] = tool_hint
            await self.bus.publish_outbound(OutboundMessage(
                channel=msg.channel, chat_id=msg.chat_id, content=content, metadata=meta,
            ))
        return _bus_progress

    @staticmethod
    def _strip_think(text: str | None) -> str | None:
        """Remove <think>…</think> blocks that some models embed in content."""
        if not text:
            return None
        return re.sub(r"<think>[\s\S]*?</think>", "", text).strip() or None

    @staticmethod
    def _tool_hint(tool_calls: list) -> str:
        """Format tool calls as concise hint, e.g. 'web_search("query")'."""
        def _fmt(tc):
            args = (tc.arguments[0] if isinstance(tc.arguments, list) else tc.arguments) or {}
            val = next(iter(args.values()), None) if isinstance(args, dict) else None
            if not isinstance(val, str):
                return tc.name
            return f'{tc.name}("{val[:40]}…")' if len(val) > 40 else f'{tc.name}("{val}")'
        return ", ".join(_fmt(tc) for tc in tool_calls)

    def _get_tool_description(self, tool_name: str, tool_args: dict) -> str:
        """Generate a user-friendly description of a tool call."""
        if tool_name == "gmail":
            action = tool_args.get("action", "")
            if action == "send":
                to = tool_args.get("to", "...")
                return f"Sending email to {to}"
            elif action == "read":
                return "Reading emails"
            return "Using Gmail"

        elif tool_name == "calendar":
            action = tool_args.get("action", "")
            if action == "create":
                summary = tool_args.get("summary", "event")
                return f"Creating event: {summary}"
            elif action == "list":
                return "Checking calendar"
            return "Using Calendar"

        elif tool_name == "write_file":
            path = tool_args.get("path", "file")
            return f"Writing {path}"

        elif tool_name == "read_file":
            path = tool_args.get("path", "file")
            return f"Reading {path}"

        elif tool_name == "web_search":
            query = str(tool_args.get("query", "..."))[:30]
            return f"Searching: {query}"

        elif tool_name == "exec":
            command = str(tool_args.get("command", ""))[:30]
            return f"Running: {command}"

        elif tool_name == "memory":
            action = tool_args.get("action", "access")
            return f"Memory: {action}"

        else:
            return f"Using {tool_name}"

    async def _run_agent_loop(
        self,
        initial_messages: list[dict],
        on_progress: Callable[..., Awaitable[None]] | None = None,
        session_key: str | None = None,
        user_message: str = "",
    ) -> tuple[str | None, list[str], list[dict]]:
        """Run the agent iteration loop. Returns (final_content, tools_used, messages)."""
        messages = initial_messages
        iteration = 0
        final_content = None
        tools_used: list[str] = []

        while iteration < self.max_iterations:
            iteration += 1

            tool_defs = self.tools.get_definitions()
            logger.debug(f"Sending {len(tool_defs)} tools to LLM: {[t['function']['name'] for t in tool_defs]}")

            # Clean messages immediately before sending to the LLM to avoid
            # sending orphaned or corrupted tool messages that cause 400s.
            messages_to_send = self._clean_message_history(messages)

            response = await self.provider.chat(
                messages=messages_to_send,
                tools=tool_defs,
                model=self.model,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                reasoning_effort=self.reasoning_effort,
            )

            logger.debug(f"LLM response: finish_reason={response.finish_reason}, tool_calls={len(response.tool_calls) if response.tool_calls else 0}, content_preview={str(response.content)[:100]}")

            if response.has_tool_calls:
                if on_progress:
                    clean = self._strip_think(response.content)
                    if clean:
                        await on_progress(clean)
                    await on_progress(self._tool_hint(response.tool_calls), tool_hint=True)

                tool_call_dicts = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.name,
                            "arguments": json.dumps(tc.arguments, ensure_ascii=False)
                        }
                    }
                    for tc in response.tool_calls
                ]
                messages = self.context.add_assistant_message(
                    messages, response.content, tool_call_dicts,
                    reasoning_content=response.reasoning_content,
                    thinking_blocks=response.thinking_blocks,
                )

                for tool_call in response.tool_calls:
                    tools_used.append(tool_call.name)
                    args_str = json.dumps(tool_call.arguments, ensure_ascii=False)
                    logger.info("Tool call: {}({})", tool_call.name, args_str[:200])

                    # Intent classification - check if confirmation is needed
                    classification = self.intent_classifier.classify(
                        user_message, tool_call.name, tool_call.arguments
                    )
                    logger.debug(f"Intent classification for {tool_call.name}: {classification}")

                    if self.intent_classifier.requires_confirmation(classification):
                        # Store pending tool call and pause execution
                        if session_key:
                            base_confirmation_msg = self.intent_classifier.get_confirmation_message(
                                tool_call.name, tool_call.arguments
                            )

                            pending_action = PendingAction(
                                tool_name=tool_call.name,
                                tool_args=tool_call.arguments,
                                tool_call=tool_call,
                                messages=initial_messages,
                                iteration=iteration,
                                tools_used=tools_used,
                                auto_confirm_seconds=30,
                            )

                            self._pending_confirmations[session_key] = pending_action

                            # Format confirmation message with timer
                            confirmation_msg = pending_action.format_confirmation_message(
                                base_confirmation_msg
                            )

                            # Return early with confirmation message
                            return confirmation_msg, tools_used, messages
                        else:
                            # No session key means we can't get confirmation, log warning and proceed
                            logger.warning(
                                f"Tool {tool_call.name} requires confirmation but no session_key provided, executing anyway"
                            )

                    # Send tool_start event
                    if on_progress:
                        await on_progress(json.dumps({
                            "type": "tool_start",
                            "tool": tool_call.name,
                            "description": self._get_tool_description(tool_call.name, tool_call.arguments)
                        }), tool_hint=True)

                    # Execute tool with error recovery and retry logic
                    result = None
                    result_metadata = {}
                    retry_attempt = 0
                    max_retries = 3

                    while retry_attempt < max_retries:
                        try:
                            result = await self.tools.execute(tool_call.name, tool_call.arguments)
                            result_metadata = {
                                "success": True,
                                "tool": tool_call.name,
                                "attempts": retry_attempt + 1
                            }
                            break  # Success, exit retry loop

                        except Exception as e:
                            error_message = str(e)
                            logger.warning(
                                f"Tool {tool_call.name} failed (attempt {retry_attempt + 1}/{max_retries}): {error_message}"
                            )

                            # Classify error type
                            error_type = self.error_recovery.classify_error(
                                error_message, tool_call.name
                            )

                            # Get recovery action
                            recovery_action = self.error_recovery.get_recovery_action(
                                error_type, tool_call.name, tool_call.arguments, retry_attempt + 1
                            )

                            # Handle recovery action
                            if recovery_action["action"] == "retry":
                                retry_attempt += 1
                                if retry_attempt < max_retries:
                                    # Send progress message about retry
                                    if on_progress:
                                        await on_progress(recovery_action["message"], tool_hint=True)

                                    # Wait before retry
                                    await asyncio.sleep(recovery_action["delay"])
                                    continue
                                else:
                                    # Max retries reached
                                    result = self.error_recovery.format_fatal_error(
                                        error_message, tool_call.name
                                    )
                                    result_metadata = {
                                        "success": False,
                                        "error": error_message,
                                        "error_type": error_type,
                                        "tool": tool_call.name,
                                        "attempts": retry_attempt + 1
                                    }
                                    break

                            elif recovery_action["action"] == "suggest_alternatives":
                                # For calendar conflicts, suggest alternatives
                                if tool_call.name == "calendar" and "start" in tool_call.arguments:
                                    alternatives = self.error_recovery.suggest_alternative_times(
                                        tool_call.arguments.get("start", ""),
                                        tool_call.arguments.get("end", ""),
                                        duration_minutes=30
                                    )

                                    alt_text = "\n".join([
                                        f"  • {alt['display']}"
                                        for alt in alternatives[:3]
                                    ])
                                    result = f"{recovery_action['message']}\n\nAlternatives:\n{alt_text}"
                                else:
                                    result = recovery_action["message"]

                                result_metadata = {
                                    "success": False,
                                    "error": error_message,
                                    "error_type": error_type,
                                    "tool": tool_call.name,
                                    "alternatives_suggested": True
                                }
                                break

                            elif recovery_action["action"] == "notify":
                                # Just notify user about the issue
                                result = recovery_action["message"]
                                result_metadata = {
                                    "success": False,
                                    "error": error_message,
                                    "error_type": error_type,
                                    "tool": tool_call.name
                                }
                                break

                            else:  # abort
                                # Fatal error
                                result = self.error_recovery.format_fatal_error(
                                    error_message, tool_call.name
                                )
                                result_metadata = {
                                    "success": False,
                                    "error": error_message,
                                    "error_type": error_type,
                                    "tool": tool_call.name,
                                    "fatal": True
                                }
                                break

                    # Track tool results for task completion summary
                    if session_key:
                        if session_key not in self._tool_results:
                            self._tool_results[session_key] = []
                        self._tool_results[session_key].append({
                            "result": result,
                            "metadata": result_metadata
                        })

                    # Send tool_done event
                    if on_progress:
                        await on_progress(json.dumps({
                            "type": "tool_done",
                            "tool": tool_call.name,
                            "description": self._get_tool_description(tool_call.name, tool_call.arguments) + " ✓"
                        }), tool_hint=True)

                    messages = self.context.add_tool_result(
                        messages, tool_call.id, tool_call.name, result
                    )
            else:
                clean = self._strip_think(response.content)
                # Don't persist error responses to session history — they can
                # poison the context and cause permanent 400 loops (#1303).
                if response.finish_reason == "error":
                    logger.error("LLM returned error: {}", (clean or "")[:200])
                    final_content = clean or "Sorry, I encountered an error calling the AI model."
                    break
                messages = self.context.add_assistant_message(
                    messages, clean, reasoning_content=response.reasoning_content,
                    thinking_blocks=response.thinking_blocks,
                )
                final_content = clean
                break

        if final_content is None and iteration >= self.max_iterations:
            logger.warning("Max iterations ({}) reached", self.max_iterations)
            final_content = (
                f"I reached the maximum number of tool call iterations ({self.max_iterations}) "
                "without completing the task. You can try breaking the task into smaller steps."
            )

        return final_content, tools_used, messages

    async def run(self) -> None:
        """Run the agent loop, dispatching messages as tasks to stay responsive to /stop."""
        self._running = True
        await self._connect_mcp()
        logger.info("Agent loop started")

        # Start background task for checking expired confirmations
        self._expiry_check_task = asyncio.create_task(self._check_expired_confirmations())

        while self._running:
            try:
                msg = await asyncio.wait_for(self.bus.consume_inbound(), timeout=1.0)
            except asyncio.TimeoutError:
                continue

            if msg.content.strip().lower() == "/stop":
                await self._handle_stop(msg)
            else:
                task = asyncio.create_task(self._dispatch(msg))
                self._active_tasks.setdefault(msg.session_key, []).append(task)
                task.add_done_callback(lambda t, k=msg.session_key: self._active_tasks.get(k, []) and self._active_tasks[k].remove(t) if t in self._active_tasks.get(k, []) else None)

    async def _handle_stop(self, msg: InboundMessage) -> None:
        """Cancel all active tasks and subagents for the session."""
        tasks = self._active_tasks.pop(msg.session_key, [])
        cancelled = sum(1 for t in tasks if not t.done() and t.cancel())
        for t in tasks:
            try:
                await t
            except (asyncio.CancelledError, Exception):
                pass
        sub_cancelled = await self.subagents.cancel_by_session(msg.session_key)
        total = cancelled + sub_cancelled
        content = f"⏹ Stopped {total} task(s)." if total else "No active task to stop."
        await self.bus.publish_outbound(OutboundMessage(
            channel=msg.channel, chat_id=msg.chat_id, content=content,
        ))

    async def _dispatch(self, msg: InboundMessage) -> None:
        """Process a message under the global lock."""
        async with self._processing_lock:
            try:
                # Check for pending confirmation BEFORE processing the message
                session_key = msg.session_key

                if session_key in self._pending_confirmations:
                    pending = self._pending_confirmations[session_key]
                    user_response = msg.content.strip().lower()

                    # Check if the pending action has expired
                    if pending.is_expired():
                        # Auto-execute the tool
                        logger.info("Auto-confirming expired action for session {}", session_key)

                        tool_call = pending.tool_call
                        messages = pending.messages
                        args_str = json.dumps(tool_call.arguments, ensure_ascii=False)
                        logger.info("Auto-executing tool: {}({})", tool_call.name, args_str[:200])

                        result = await self.tools.execute(tool_call.name, tool_call.arguments)
                        messages = self.context.add_tool_result(
                            messages, tool_call.id, tool_call.name, result
                        )

                        # Continue the agent loop
                        session = self.sessions.get_or_create(session_key)
                        # Clean persisted session messages on load and persist if changed
                        try:
                            if session.messages:
                                cleaned = self._clean_message_history(session.messages)
                                if cleaned != session.messages:
                                    session.messages = cleaned
                                    session.metadata.setdefault("_cleaned_on_load", True)
                                    self.sessions.save(session)
                        except Exception as e:
                            logger.warning("Failed to clean/persist session on load {}: {}", session.key, e)
                        final_content, _, all_msgs = await self._run_agent_loop(
                            messages,
                            on_progress=self._make_bus_progress(msg),
                            session_key=session_key,
                            user_message=msg.content,
                        )

                        if final_content is None:
                            final_content = "I've completed processing but have no response to give."

                        self._save_turn(session, all_msgs, 1 + len(session.get_history(max_messages=self.memory_window)))
                        self.sessions.save(session)

                        # Clear the pending confirmation
                        self._pending_confirmations.pop(session_key, None)

                        # Send the auto-confirmation notification + result
                        await self.bus.publish_outbound(OutboundMessage(
                            channel=msg.channel, chat_id=msg.chat_id,
                            content=f"⏱️ Auto-confirmed and executed.\n\n{final_content}",
                            metadata=msg.metadata or {},
                        ))
                        return

                    # Check for user confirmation
                    if user_response in ["yes", "y", "confirm", "ok"]:
                        # User confirmed - execute the tool
                        logger.info("User confirmed action for session {}", session_key)

                        tool_call = pending.tool_call
                        messages = pending.messages
                        args_str = json.dumps(tool_call.arguments, ensure_ascii=False)
                        logger.info("Executing confirmed tool: {}({})", tool_call.name, args_str[:200])

                        result = await self.tools.execute(tool_call.name, tool_call.arguments)
                        messages = self.context.add_tool_result(
                            messages, tool_call.id, tool_call.name, result
                        )

                        # Continue the agent loop
                        session = self.sessions.get_or_create(session_key)
                        # Clean persisted session messages on load and persist if changed
                        try:
                            if session.messages:
                                cleaned = self._clean_message_history(session.messages)
                                if cleaned != session.messages:
                                    session.messages = cleaned
                                    session.metadata.setdefault("_cleaned_on_load", True)
                                    self.sessions.save(session)
                        except Exception as e:
                            logger.warning("Failed to clean/persist session on load {}: {}", session.key, e)
                        final_content, _, all_msgs = await self._run_agent_loop(
                            messages,
                            on_progress=self._make_bus_progress(msg),
                            session_key=session_key,
                            user_message=msg.content,
                        )

                        if final_content is None:
                            final_content = "I've completed processing but have no response to give."

                        self._save_turn(session, all_msgs, 1 + len(session.get_history(max_messages=self.memory_window)))
                        self.sessions.save(session)

                        # Clear the pending confirmation
                        self._pending_confirmations.pop(session_key, None)

                        await self.bus.publish_outbound(OutboundMessage(
                            channel=msg.channel, chat_id=msg.chat_id,
                            content=final_content,
                            metadata=msg.metadata or {},
                        ))
                        return

                    elif user_response in ["no", "n", "cancel", "abort"]:
                        # User cancelled - abort the action
                        logger.info("User cancelled action for session {}", session_key)

                        # Clear the pending confirmation
                        self._pending_confirmations.pop(session_key, None)

                        await self.bus.publish_outbound(OutboundMessage(
                            channel=msg.channel, chat_id=msg.chat_id,
                            content="❌ Action cancelled.",
                            metadata=msg.metadata or {},
                        ))
                        return

                    else:
                        # Invalid response - remind user
                        seconds_remaining = pending.seconds_remaining()
                        await self.bus.publish_outbound(OutboundMessage(
                            channel=msg.channel, chat_id=msg.chat_id,
                            content=f"Please reply YES to confirm or NO to cancel. ⏱️ {seconds_remaining} seconds remaining.",
                            metadata=msg.metadata or {},
                        ))
                        return

                # No pending confirmation - proceed with normal message processing
                response = await self._process_message(msg)
                if response is not None:
                    await self.bus.publish_outbound(response)
                elif msg.channel == "cli":
                    await self.bus.publish_outbound(OutboundMessage(
                        channel=msg.channel, chat_id=msg.chat_id,
                        content="", metadata=msg.metadata or {},
                    ))
            except asyncio.CancelledError:
                logger.info("Task cancelled for session {}", msg.session_key)
                raise
            except Exception:
                logger.exception("Error processing message for session {}", msg.session_key)
                await self.bus.publish_outbound(OutboundMessage(
                    channel=msg.channel, chat_id=msg.chat_id,
                    content="Sorry, I encountered an error.",
                ))

    async def close_mcp(self) -> None:
        """Close MCP connections."""
        if self._mcp_stack:
            try:
                await self._mcp_stack.aclose()
            except (RuntimeError, BaseExceptionGroup):
                pass  # MCP SDK cancel scope cleanup is noisy but harmless
            self._mcp_stack = None

    def stop(self) -> None:
        """Stop the agent loop."""
        self._running = False
        if self._expiry_check_task and not self._expiry_check_task.done():
            self._expiry_check_task.cancel()
        logger.info("Agent loop stopping")

    async def _check_expired_confirmations(self) -> None:
        """
        Background task that periodically checks for expired pending confirmations
        and auto-executes them.
        """
        logger.info("Started background task for checking expired confirmations")

        while self._running:
            try:
                await asyncio.sleep(5)  # Check every 5 seconds

                # Get a snapshot of pending confirmations to avoid dict modification during iteration
                pending_items = list(self._pending_confirmations.items())

                for session_key, pending in pending_items:
                    if pending.is_expired():
                        logger.info("Auto-confirming expired action for session {}", session_key)

                        # Execute the tool
                        tool_call = pending.tool_call
                        args_str = json.dumps(tool_call.arguments, ensure_ascii=False)
                        logger.info("Auto-executing tool: {}({})", tool_call.name, args_str[:200])

                        try:
                            result = await self.tools.execute(tool_call.name, tool_call.arguments)
                            messages = self.context.add_tool_result(
                                pending.messages, tool_call.id, tool_call.name, result
                            )

                            # Continue the agent loop
                            session = self.sessions.get_or_create(session_key)
                            # Clean persisted session messages on load and persist if changed
                            try:
                                if session.messages:
                                    cleaned = self._clean_message_history(session.messages)
                                    if cleaned != session.messages:
                                        session.messages = cleaned
                                        session.metadata.setdefault("_cleaned_on_load", True)
                                        self.sessions.save(session)
                            except Exception as e:
                                logger.warning("Failed to clean/persist session on load {}: {}", session.key, e)
                            final_content, _, all_msgs = await self._run_agent_loop(
                                messages,
                                session_key=session_key,
                                user_message="",
                            )

                            if final_content is None:
                                final_content = "I've completed processing but have no response to give."

                            self._save_turn(session, all_msgs, 1 + len(session.get_history(max_messages=self.memory_window)))
                            self.sessions.save(session)

                            # Parse channel and chat_id from session_key (format: "channel:chat_id")
                            channel, chat_id = session_key.split(":", 1) if ":" in session_key else ("cli", session_key)

                            # Send notification to user
                            await self.bus.publish_outbound(OutboundMessage(
                                channel=channel, chat_id=chat_id,
                                content=f"⏱️ Auto-confirmed and executed.\n\n{final_content}",
                            ))

                        except Exception as e:
                            logger.error("Error auto-executing expired confirmation: {}", e)
                            # Parse channel and chat_id from session_key
                            channel, chat_id = session_key.split(":", 1) if ":" in session_key else ("cli", session_key)

                            await self.bus.publish_outbound(OutboundMessage(
                                channel=channel, chat_id=chat_id,
                                content=f"⏱️ Auto-confirmation failed: {str(e)}",
                            ))

                        finally:
                            # Clear the pending confirmation
                            self._pending_confirmations.pop(session_key, None)

            except asyncio.CancelledError:
                logger.info("Expired confirmations check task cancelled")
                break
            except Exception as e:
                logger.error("Error in expired confirmations check task: {}", e)

        logger.info("Stopped background task for checking expired confirmations")

    async def _process_message(
        self,
        msg: InboundMessage,
        session_key: str | None = None,
        on_progress: Callable[[str], Awaitable[None]] | None = None,
    ) -> OutboundMessage | None:
        """Process a single inbound message and return the response."""
        # Track task duration for usage logging
        start_time = time.monotonic()

        # System messages: parse origin from chat_id ("channel:chat_id")
        if msg.channel == "system":
            channel, chat_id = (msg.chat_id.split(":", 1) if ":" in msg.chat_id
                                else ("cli", msg.chat_id))
            logger.info("Processing system message from {}", msg.sender_id)
            key = f"{channel}:{chat_id}"
            session = self.sessions.get_or_create(key)
            # Clean persisted session messages on load and persist if changed
            try:
                if session.messages:
                    cleaned = self._clean_message_history(session.messages)
                    if cleaned != session.messages:
                        session.messages = cleaned
                        session.metadata.setdefault("_cleaned_on_load", True)
                        self.sessions.save(session)
            except Exception as e:
                logger.warning("Failed to clean/persist session on load {}: {}", session.key if session else key, e)
            self._set_tool_context(channel, chat_id, msg.metadata.get("message_id"))
            history = session.get_history(max_messages=self.memory_window)
            history = self._clean_message_history(history)
            messages = await self.context.build_messages(
                history=history,
                current_message=msg.content, channel=channel, chat_id=chat_id,
            )
            final_content, _, all_msgs = await self._run_agent_loop(
                messages, session_key=key, user_message=msg.content
            )
            self._save_turn(session, all_msgs, 1 + len(history))
            self.sessions.save(session)
            return OutboundMessage(channel=channel, chat_id=chat_id,
                                  content=final_content or "Background task completed.")

        preview = msg.content[:80] + "..." if len(msg.content) > 80 else msg.content
        logger.info("Processing message from {}:{}: {}", msg.channel, msg.sender_id, preview)

        key = session_key or msg.session_key
        session = self.sessions.get_or_create(key)

        # Slash commands
        cmd = msg.content.strip().lower()
        if cmd == "/new":
            lock = self._consolidation_locks.setdefault(session.key, asyncio.Lock())
            self._consolidating.add(session.key)
            try:
                async with lock:
                    snapshot = session.messages[session.last_consolidated:]
                    if snapshot:
                        temp = Session(key=session.key)
                        temp.messages = list(snapshot)
                        if not await self._consolidate_memory(temp, archive_all=True):
                            return OutboundMessage(
                                channel=msg.channel, chat_id=msg.chat_id,
                                content="Memory archival failed, session not cleared. Please try again.",
                            )
            except Exception:
                logger.exception("/new archival failed for {}", session.key)
                return OutboundMessage(
                    channel=msg.channel, chat_id=msg.chat_id,
                    content="Memory archival failed, session not cleared. Please try again.",
                )
            finally:
                self._consolidating.discard(session.key)

            session.clear()
            self.sessions.save(session)
            self.sessions.invalidate(session.key)
            return OutboundMessage(channel=msg.channel, chat_id=msg.chat_id,
                                  content="New session started.")
        if cmd == "/help":
            return OutboundMessage(channel=msg.channel, chat_id=msg.chat_id,
                                  content="🤖 YourBot commands:\n/new — Start a new conversation\n/stop — Stop the current task\n/help — Show available commands")

        unconsolidated = len(session.messages) - session.last_consolidated
        if (unconsolidated >= self.memory_window and session.key not in self._consolidating):
            self._consolidating.add(session.key)
            lock = self._consolidation_locks.setdefault(session.key, asyncio.Lock())

            async def _consolidate_and_unlock():
                try:
                    async with lock:
                        await self._consolidate_memory(session)
                finally:
                    self._consolidating.discard(session.key)
                    _task = asyncio.current_task()
                    if _task is not None:
                        self._consolidation_tasks.discard(_task)

            _task = asyncio.create_task(_consolidate_and_unlock())
            self._consolidation_tasks.add(_task)

        self._set_tool_context(msg.channel, msg.chat_id, msg.metadata.get("message_id"))
        if message_tool := self.tools.get("message"):
            if isinstance(message_tool, MessageTool):
                message_tool.start_turn()

        history = session.get_history(max_messages=self.memory_window)

        # First message in session - send welcome intro (use flag to prevent race condition)
        if not session.metadata.get("_welcomed"):
            session.metadata["_welcomed"] = True  # Set immediately to prevent duplicates
            # Send welcome to user
            await self.bus.publish_outbound(OutboundMessage(
                channel=msg.channel, chat_id=msg.chat_id,
                content=self.WELCOME_INTRO,
            ))
            # Save welcome to history so LLM has context
            session.add_message("assistant", self.WELCOME_INTRO)
            self.sessions.save(session)
            history = session.get_history(max_messages=self.memory_window)

        # Clean history to remove orphaned tool messages
        history = self._clean_message_history(history)

        # Search semantic memory for relevant context
        semantic_context = ""
        try:
            memories = await self.semantic_memory.search(msg.content, top_k=5)
            if memories:
                memory_lines = [f"- {m['text']}" for m in memories if m.get('score', 0) > 0.3]
                if memory_lines:
                    semantic_context = "Relevant memories:\n" + "\n".join(memory_lines)
        except Exception as e:
            logger.warning("Semantic memory search failed: {}", e)

        # Build message with semantic context prepended
        current_message = msg.content
        if semantic_context:
            current_message = f"{semantic_context}\n\n{msg.content}"

        # Ensure history is cleaned immediately before building messages
        history = self._clean_message_history(history)

        initial_messages = await self.context.build_messages(
            history=history,
            current_message=current_message,
            media=msg.media if msg.media else None,
            channel=msg.channel, chat_id=msg.chat_id,
        )

        # Task planning for complex multi-step tasks
        task_planner = TaskPlanner()
        if task_planner.is_complex_task(msg.content):
            logger.info("Detected complex task, generating plan for session {}", key)

            # Get available tool names
            tool_names = [tool.name for tool in self.tools._tools.values() if hasattr(tool, 'name')]

            # Generate plan
            plan_steps = await task_planner.generate_plan(
                msg.content,
                self.provider,
                tool_names
            )

            # Format and send plan message to user
            plan_message = task_planner.format_plan_message(plan_steps)
            await self.bus.publish_outbound(OutboundMessage(
                channel=msg.channel,
                chat_id=msg.chat_id,
                content=json.dumps({
                    "type": "plan",
                    "steps": [s["action"] for s in plan_steps],
                    "tools": [s["tool"] for s in plan_steps],
                    "formatted": plan_message
                }),
                metadata={"_tool_hint": True, **(msg.metadata or {})},
            ))

            # Store plan for completion summary
            self._current_plan[key] = plan_steps

            # Clear any existing tool results for this session
            self._tool_results[key] = []

        async def _bus_progress(content: str, *, tool_hint: bool = False) -> None:
            meta = dict(msg.metadata or {})
            meta["_progress"] = True
            meta["_tool_hint"] = tool_hint
            await self.bus.publish_outbound(OutboundMessage(
                channel=msg.channel, chat_id=msg.chat_id, content=content, metadata=meta,
            ))

        final_content, _, all_msgs = await self._run_agent_loop(
            initial_messages,
            on_progress=on_progress or _bus_progress,
            session_key=key,
            user_message=msg.content,
        )

        if final_content is None:
            final_content = "I've completed processing but have no response to give."

        # Add completion summary if a plan was generated
        if key in self._current_plan:
            plan_steps = self._current_plan.pop(key)
            tool_results = self._tool_results.pop(key, [])

            # Generate completion summary
            completion_summary = task_planner.format_completion_summary(
                plan_steps,
                tool_results
            )

            # Append summary to final content
            final_content = f"{final_content}\n\n{completion_summary}"

            logger.info("Added completion summary for plan with {} steps", len(plan_steps))

        # Log task usage for dashboard
        try:
            duration = time.monotonic() - start_time

            # Extract tools used from tool results
            tools_used = []
            if key in self._tool_results:
                for result_dict in self._tool_results[key]:
                    if isinstance(result_dict, dict) and "metadata" in result_dict:
                        tool_name = result_dict["metadata"].get("tool")
                        if tool_name:
                            tools_used.append(tool_name)

            # Remove duplicates while preserving order
            tools_used = list(dict.fromkeys(tools_used))

            # Determine success
            success = True
            error_msg = None

            if final_content and final_content.startswith("❌"):
                success = False
                error_msg = final_content[:100]

            # Check for fatal errors in tool results
            if key in self._tool_results:
                for result_dict in self._tool_results[key]:
                    if isinstance(result_dict, dict) and "metadata" in result_dict:
                        if result_dict["metadata"].get("fatal"):
                            success = False
                            if not error_msg:
                                error_msg = result_dict.get("result", "Unknown error")[:100]
                            break

            self.usage_logger.log_task(msg.content, tools_used, success, error_msg, duration)

        except Exception as e:
            logger.warning(f"Failed to log task usage: {e}")

        self._save_turn(session, all_msgs, 1 + len(history))
        self.sessions.save(session)

        # Extract and save memories from this conversation turn
        try:
            conversation_turn = f"User: {msg.content}\nAgent: {final_content}"
            extracted = await self.memory_extractor.extract(conversation_turn)
            for mem in extracted:
                await self.semantic_memory.save(mem["text"], category=mem["category"])
        except Exception as e:
            logger.warning("Memory extraction failed: {}", e)

        if (mt := self.tools.get("message")) and isinstance(mt, MessageTool) and mt._sent_in_turn:
            return None

        preview = final_content[:120] + "..." if len(final_content) > 120 else final_content
        logger.info("Response to {}:{}: {}", msg.channel, msg.sender_id, preview)
        return OutboundMessage(
            channel=msg.channel, chat_id=msg.chat_id, content=final_content,
            metadata=msg.metadata or {},
        )

    def _save_turn(self, session: Session, messages: list[dict], skip: int) -> None:
        """Save new-turn messages into session, truncating large tool results."""
        from datetime import datetime
        for m in messages[skip:]:
            entry = dict(m)
            role, content = entry.get("role"), entry.get("content")
            if role == "assistant" and not content and not entry.get("tool_calls"):
                continue  # skip empty assistant messages — they poison session context
            if role == "tool" and isinstance(content, str) and len(content) > self._TOOL_RESULT_MAX_CHARS:
                entry["content"] = content[:self._TOOL_RESULT_MAX_CHARS] + "\n... (truncated)"
            elif role == "user":
                if isinstance(content, str) and content.startswith(ContextBuilder._RUNTIME_CONTEXT_TAG):
                    # Strip the runtime-context prefix, keep only the user text.
                    parts = content.split("\n\n", 1)
                    if len(parts) > 1 and parts[1].strip():
                        entry["content"] = parts[1]
                    else:
                        continue
                if isinstance(content, list):
                    filtered = []
                    for c in content:
                        if c.get("type") == "text" and isinstance(c.get("text"), str) and c["text"].startswith(ContextBuilder._RUNTIME_CONTEXT_TAG):
                            continue  # Strip runtime context from multimodal messages
                        if (c.get("type") == "image_url"
                                and c.get("image_url", {}).get("url", "").startswith("data:image/")):
                            filtered.append({"type": "text", "text": "[image]"})
                        else:
                            filtered.append(c)
                    if not filtered:
                        continue
                    entry["content"] = filtered
            entry.setdefault("timestamp", datetime.now().isoformat())
            session.messages.append(entry)
        session.updated_at = datetime.now()

    async def _consolidate_memory(self, session, archive_all: bool = False) -> bool:
        """Delegate to MemoryStore.consolidate(). Returns True on success."""
        return await MemoryStore(self.workspace).consolidate(
            session, self.provider, self.model,
            archive_all=archive_all, memory_window=self.memory_window,
        )

    async def process_direct(
        self,
        content: str,
        session_key: str = "cli:direct",
        channel: str = "cli",
        chat_id: str = "direct",
        on_progress: Callable[[str], Awaitable[None]] | None = None,
    ) -> str:
        """Process a message directly (for CLI or cron usage)."""
        await self._connect_mcp()
        msg = InboundMessage(channel=channel, sender_id="user", chat_id=chat_id, content=content)
        response = await self._process_message(msg, session_key=session_key, on_progress=on_progress)
        return response.content if response else ""
