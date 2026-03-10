# Nanobot - Complete Knowledge Transfer Document

> **Purpose**: This document provides end-to-end knowledge transfer for the Nanobot personal AI assistant platform. It covers architecture, agent flows, tools, integrations, limitations, and development guidance to enable continued development.

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Technology Stack](#2-technology-stack)
3. [Architecture Overview](#3-architecture-overview)
4. [Core Data Flow](#4-core-data-flow)
5. [Module Structure](#5-module-structure)
6. [Agent System](#6-agent-system)
7. [Tools System](#7-tools-system)
8. [LLM Providers](#8-llm-providers)
9. [Communication Channels](#9-communication-channels)
10. [Memory System](#10-memory-system)
11. [Skills System](#11-skills-system)
12. [Special Services](#12-special-services)
13. [Configuration](#13-configuration)
14. [Frontend & Bridge](#14-frontend--bridge)
15. [Data Storage](#15-data-storage)
16. [Known Limitations & Issues](#16-known-limitations--issues)
17. [Security Considerations](#17-security-considerations)
18. [Deployment](#18-deployment)
19. [Testing](#19-testing)
20. [Development Guide](#20-development-guide)
21. [API Reference](#21-api-reference)
22. [Troubleshooting](#22-troubleshooting)

---

## 1. Executive Summary

**Nanobot** (also called "Personal Agent" or "YourBot") is a personal AI automation assistant platform that:

- Combines LLM capabilities with actionable tools (shell, browser, email, calendar, etc.)
- Supports 11+ communication channels (Web, Telegram, Discord, Slack, WhatsApp, etc.)
- Features semantic memory with ChromaDB vector storage
- Provides per-user isolation with token-based authentication
- Offers extensible skills via markdown-based instruction sets

**Author**: Midhun  
**License**: MIT  
**Python Version**: 3.11+  
**Default Port**: 8765

---

## 2. Technology Stack

### Backend (Python)
| Component | Technology | Version |
|-----------|------------|---------|
| Web Framework | FastAPI + Uvicorn | >=0.115.0 |
| LLM Abstraction | LiteLLM | >=1.81.5 |
| Vector Database | ChromaDB | >=0.4.0 |
| Embeddings | sentence-transformers (all-MiniLM-L6-v2) | >=2.2.0 |
| Browser Automation | Playwright | >=1.40.0 |
| Validation | Pydantic | >=2.12.0 |
| HTTP Client | httpx | >=0.28.0 |
| Logging | Loguru | >=0.7.3 |
| Cron Parsing | croniter | >=6.0.0 |

### Frontend (Node.js)
| Component | Technology |
|-----------|------------|
| Framework | Next.js 14+ |
| UI | React 18 + Tailwind CSS |
| Icons | lucide-react |
| API Calls | fetch + WebSocket |

### Bridge (WhatsApp)
| Component | Technology |
|-----------|------------|
| Runtime | Node.js + TypeScript |
| WhatsApp Client | Baileys |
| Server | WebSocket (localhost:3001) |

---

## 3. Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend                              │
│                   (Next.js Web App)                          │
│           frontend/app/chat/page.tsx                         │
└─────────────────────┬───────────────────────────────────────┘
                      │ WebSocket (/ws/{token})
┌─────────────────────▼───────────────────────────────────────┐
│                    WebServer (FastAPI)                       │
│                    nanobot/main.py                           │
│  - /register (POST) - User registration                      │
│  - /login (POST) - User login                                │
│  - /ws/{token} (WS) - Real-time communication                │
│  - /integrations/* - OAuth endpoints                         │
│  - /health (GET) - Health check                              │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│                     Application                              │
│                    nanobot/main.py                           │
│  - AuthManager: Token-based user auth                        │
│  - MessageBus: Inbound/outbound message routing              │
│  - ChannelManager: Multi-channel support                     │
│  - AgentLoop: Per-user AI agent instances                    │
│  - SessionManager: Conversation session handling             │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│                    AgentLoop                                 │
│                nanobot/agent/loop.py                         │
│  - LLM Provider (LiteLLM/Custom)                             │
│  - Tool Execution Engine                                     │
│  - ContextBuilder (prompt assembly)                          │
│  - Memory System (ChromaDB + Embeddings)                     │
│  - Onboarding Flow                                           │
│  - Cron Service (Scheduled Tasks)                            │
│  - Heartbeat Service (Periodic checks)                       │
└─────────────────────────────────────────────────────────────┘
```

---

## 4. Core Data Flow

### Message Processing Flow

```
User Message 
    → Channel (Web/Telegram/Discord/etc.)
    → MessageBus.inbound queue
    → AgentLoop._dispatch()
    → AgentLoop._process_message()
    → ContextBuilder.build_messages()
        ├── Core identity (system prompt)
        ├── Bootstrap files (AGENTS.md, SOUL.md, USER.md)
        ├── Memory context (MEMORY.md)
        ├── Active skills (always=true)
        └── Runtime context (timestamp, channel)
    → LLM Provider (LiteLLM)
    → Tool Execution (if tool_calls present)
        └── Loop up to max_iterations (40)
    → Response Generation
    → MessageBus.outbound queue
    → Channel.send()
    → User
```

### Agent Loop Iteration Cycle

```python
# Simplified from nanobot/agent/loop.py
async def _run_agent_loop(self, messages, user_id, channel):
    for iteration in range(self.max_iterations):  # default: 40
        response = await self.provider.chat(messages, tools)
        
        if response.tool_calls:
            # Execute each tool call
            for tool_call in response.tool_calls:
                result = await self.registry.execute(tool_call.name, tool_call.arguments)
                messages.append(tool_result_message)
        else:
            # No tools = final response
            return response.content
```

---

## 5. Module Structure

| Module | Path | Purpose |
|--------|------|---------|
| **agent/** | `nanobot/agent/` | Core agent loop, tools, context, memory, skills, subagents |
| **auth/** | `nanobot/auth/` | Token-based authentication (`AuthManager`) |
| **bus/** | `nanobot/bus/` | Message queue (`MessageBus` with inbound/outbound queues) |
| **channels/** | `nanobot/channels/` | Communication channels (Web, Telegram, Discord, etc.) |
| **config/** | `nanobot/config/` | Pydantic configuration schemas |
| **cron/** | `nanobot/cron/` | Task scheduler service |
| **heartbeat/** | `nanobot/heartbeat/` | Periodic agent wake-up service |
| **integrations/** | `nanobot/integrations/` | OAuth for Google services |
| **memory/** | `nanobot/memory/` | Semantic memory with ChromaDB |
| **providers/** | `nanobot/providers/` | LLM providers via LiteLLM |
| **session/** | `nanobot/session/` | Conversation session management |
| **skills/** | `nanobot/skills/` | Markdown-based skill extensions |
| **templates/** | `nanobot/templates/` | Prompt templates (SOUL.md, USER.md, etc.) |
| **utils/** | `nanobot/utils/` | Helper utilities |
| **cli/** | `nanobot/cli/` | Command-line interface |

---

## 6. Agent System

### 6.1 AgentLoop (`nanobot/agent/loop.py`)

The core processing engine that handles all user interactions.

#### Key Methods

| Method | Purpose |
|--------|---------|
| `run()` | Main async loop consuming from message bus |
| `_run_agent_loop()` | LLM iteration loop (max 40 iterations) |
| `_process_message()` | Handles single message with context building |
| `_dispatch()` | Routes messages to appropriate handlers |
| `_handle_stop()` | Handles `/stop` command to cancel active tasks |
| `_save_turn()` | Persists conversation to session |

#### Key Limits & Constants

```python
max_iterations = 40        # Max tool calls per turn
memory_window = 100        # Messages before consolidation
max_tokens = 4096          # Per LLM call (configurable)
tool_result_truncation = 500  # Characters for tool results in session
```

#### Error Handling Pattern

```python
# From loop.py - errors not persisted to prevent "400 loops"
try:
    response = await self.provider.chat(messages, tools)
except Exception as e:
    # Log error but don't add to messages
    # This prevents error→retry→error loops
    logger.error(f"LLM error: {e}")
    return "I encountered an error processing your request."
```

### 6.2 ContextBuilder (`nanobot/agent/context.py`)

Assembles the full prompt context from multiple sources.

#### Context Assembly Order

1. **Core Identity** - System prompt with workspace path, runtime info
2. **Bootstrap Files** - `AGENTS.md`, `SOUL.md`, `USER.md`, `TOOLS.md`
3. **Memory Context** - `MEMORY.md` (long-term facts)
4. **Active Skills** - Skills marked `always=true`
5. **Skills Summary** - XML format for progressive loading
6. **Runtime Context** - Timestamp, channel info

#### Template Files (from `nanobot/templates/`)

| Template | Purpose |
|----------|---------|
| `SOUL.md` | Agent core identity/personality |
| `USER.md` | User profile template |
| `AGENTS.md` | Agent instructions for reminders/heartbeat |
| `TOOLS.md` | Tool usage notes and safety limits |
| `HEARTBEAT.md` | Heartbeat task template |
| `memory/MEMORY.md` | Long-term memory structure |

### 6.3 Memory (`nanobot/agent/memory.py`)

Dual-layer memory system for context persistence.

| File | Purpose | Format |
|------|---------|--------|
| `MEMORY.md` | Long-term facts, preferences, goals | Markdown |
| `HISTORY.md` | Grep-searchable event log | Timestamped log |

#### Memory Operations

```python
# Writing to MEMORY.md
def remember(self, fact: str, category: str = "general"):
    """Add fact to appropriate section in MEMORY.md"""
    
# Reading from HISTORY.md  
def recall(self, query: str) -> list[str]:
    """Search HISTORY.md for relevant entries"""
```

### 6.4 Skills Manager (`nanobot/agent/skills.py`)

Loads and manages markdown-based skill extensions.

#### Skill Loading

```python
# Skill locations (checked in order):
# 1. workspace/skills/{name}/SKILL.md (user skills)
# 2. nanobot/skills/{name}/SKILL.md (built-in skills)

# Skill metadata in YAML frontmatter:
"""
---
name: github
description: GitHub operations via gh CLI
always: false  # if true, always included in context
bins: [gh]     # required executables
env: []        # required environment variables
---
"""
```

#### Built-in Skills

| Skill | Description | Requirements |
|-------|-------------|--------------|
| `github` | GitHub CLI operations | `gh` CLI installed |
| `weather` | Weather info via wttr.in | None |
| `summarize` | URL/file/YouTube summarization | None |
| `cron` | Scheduling guidance | None |
| `memory` | Memory system documentation | None |
| `tmux` | tmux session control | `tmux` installed |
| `skill-creator` | Create new skills | None |

### 6.5 Subagent (`nanobot/agent/subagent.py`)

Background task execution for complex operations.

#### Subagent Limits

```python
max_iterations = 15  # Lower than main agent (40)
restricted_tools = ['message', 'spawn']  # Cannot send messages or spawn more subagents
```

#### Subagent Flow

```
SpawnTool.execute(task)
    → SubagentManager.spawn(task)
    → Create new AgentLoop with limited tools
    → Execute task (max 15 iterations)
    → Report result via message bus
    → Main agent receives completion notification
```

---

## 7. Tools System

### 7.1 Tool Registry (`nanobot/agent/tools/registry.py`)

Manages dynamic tool registration, validation, and execution.

```python
class ToolRegistry:
    def register(self, tool: Tool) -> None
    def unregister(self, name: str) -> None
    def get(self, name: str) -> Tool | None
    def execute(self, name: str, params: dict) -> str
    def get_definitions(self) -> list[dict]  # OpenAI function schema
```

### 7.2 Tool Base Class (`nanobot/agent/tools/base.py`)

```python
class Tool(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...
    
    @property
    @abstractmethod
    def description(self) -> str: ...
    
    @property
    @abstractmethod
    def parameters(self) -> dict: ...  # JSON Schema
    
    @abstractmethod
    async def execute(self, **kwargs) -> str: ...
```

### 7.3 Available Tools

| Tool | File | Description | Key Parameters |
|------|------|-------------|----------------|
| `read_file` | `filesystem.py` | Read file contents | `path`, `start_line`, `end_line` |
| `write_file` | `filesystem.py` | Create/write files | `path`, `content` |
| `edit_file` | `filesystem.py` | Replace text in files | `path`, `old_text`, `new_text` |
| `list_dir` | `filesystem.py` | List directory contents | `path` |
| `exec` | `shell.py` | Execute shell commands | `command`, `timeout` |
| `web_search` | `web.py` | Search the web | `query`, `num_results` |
| `web_fetch` | `web.py` | Fetch URL content | `url`, `mode` |
| `browser` | `browser_tool.py` | Browser automation | `action`, `url`, `selector` |
| `gmail` | `gmail_tool.py` | Gmail operations | `action`, `query`, `to`, `body` |
| `calendar` | `calendar_tool.py` | Calendar management | `action`, `event_id`, `summary` |
| `cron` | `cron.py` | Schedule tasks/reminders | `action`, `schedule`, `task` |
| `message` | `message.py` | Send messages to user | `content`, `channel` |
| `spawn` | `spawn.py` | Create background subagent | `task` |
| `notify_file` | `notify_file.py` | Notify about created files | `path`, `description` |
| `mcp_*` | `mcp.py` | MCP protocol tools | (varies by server) |

### 7.4 ExecTool Safety (`nanobot/agent/tools/shell.py`)

#### Blocked Command Patterns

```python
DENY_PATTERNS = [
    r'\brm\s+(-[rf]+\s+)*/',          # rm -rf /
    r'\bdel\s+/[fqs]',                 # Windows del
    r'\brmdir\s+/s',                   # Windows rmdir
    r'\bformat\b',                     # Disk format
    r'\bmkfs\b',                       # Linux filesystem creation
    r'\bdiskpart\b',                   # Windows disk management
    r'\bdd\s+.*of=/',                  # dd to device
    r'>\s*/dev/',                      # Redirect to device
    r'\bshutdown\b',                   # System shutdown
    r'\breboot\b',                     # System reboot
    r'\bpoweroff\b',                   # System poweroff
    r':\(\)\s*\{\s*:\|:\s*&\s*\};:',  # Fork bomb
]
```

#### ExecTool Configuration

```python
# From config schema
class ExecToolConfig:
    timeout: int = 60          # Command timeout in seconds
    path_append: list[str] = []  # Additional PATH entries
    
# Output truncation
MAX_OUTPUT_LENGTH = 10000  # Characters
```

### 7.5 Browser Tool (`nanobot/agent/tools/browser_tool.py`)

#### Available Actions

| Action | Description | Parameters |
|--------|-------------|------------|
| `navigate` | Go to URL | `url` |
| `fill_form` | Fill form fields | `selector`, `value` |
| `click` | Click element | `selector` |
| `extract` | Extract content with LLM | `instruction` |

#### Requirements

```bash
# Install Playwright browsers
playwright install chromium
```

### 7.6 MCP Tool Integration (`nanobot/agent/tools/mcp.py`)

Model Context Protocol (MCP) integration for external tool servers.

```python
# Tools are registered with prefix: mcp_{server}_{tool}
# Example: mcp_filesystem_read_file

async def connect_mcp_servers(config: dict) -> list[Tool]:
    """Connect to MCP servers and register their tools"""
    # Supports stdio and HTTP transports
```

---

## 8. LLM Providers

### 8.1 Provider Architecture

| File | Class | Purpose |
|------|-------|---------|
| `base.py` | `LLMProvider` | Abstract base class |
| `registry.py` | `ProviderSpec`, `PROVIDERS` | Provider registration |
| `litellm_provider.py` | `LiteLLMProvider` | Main multi-provider implementation |
| `custom_provider.py` | `CustomProvider` | Direct OpenAI-compatible endpoint |
| `openai_codex_provider.py` | `OpenAICodexProvider` | OAuth-based Codex |
| `transcription.py` | `GroqTranscriptionProvider` | Voice transcription |

### 8.2 Supported Providers

| Provider | Type | Env Variable | Model Prefix | Notes |
|----------|------|--------------|--------------|-------|
| **OpenAI** | Standard | `OPENAI_API_KEY` | `gpt-*` | Native support |
| **Anthropic** | Standard | `ANTHROPIC_API_KEY` | `claude-*` | Prompt caching |
| **OpenRouter** | Gateway | `OPENROUTER_API_KEY` | (any) | `sk-or-` prefix detection |
| **DeepSeek** | Standard | `DEEPSEEK_API_KEY` | `deepseek/` | |
| **Gemini** | Standard | `GEMINI_API_KEY` | `gemini/` | |
| **Groq** | Auxiliary | `GROQ_API_KEY` | `groq/` | Fast inference, Whisper |
| **Zhipu AI** | Standard | `ZAI_API_KEY` | `zai/` | GLM models |
| **DashScope** | Standard | `DASHSCOPE_API_KEY` | `dashscope/` | Qwen models |
| **Moonshot** | Standard | `MOONSHOT_API_KEY` | `moonshot/` | Kimi models |
| **MiniMax** | Standard | `MINIMAX_API_KEY` | `minimax/` | |
| **AiHubMix** | Gateway | `OPENAI_API_KEY` | (varies) | |
| **SiliconFlow** | Gateway | `OPENAI_API_KEY` | (varies) | Chinese |
| **VolcEngine** | Gateway | `OPENAI_API_KEY` | (varies) | Chinese |
| **vLLM** | Local | `HOSTED_VLLM_API_KEY` | (custom) | Self-hosted |
| **GitHub Copilot** | OAuth | (OAuth) | `github_copilot/` | |
| **OpenAI Codex** | OAuth | (OAuth) | (varies) | Responses API |
| **Custom** | Direct | (user config) | (any) | Bypasses LiteLLM |

### 8.3 Provider Selection Logic

```python
# From registry.py
def find_by_model(model: str) -> ProviderSpec | None:
    """Match provider by model name keywords"""
    # e.g., "claude-3" → Anthropic
    
def find_gateway(provider_name: str, api_key: str, api_base: str) -> ProviderSpec | None:
    """Detect gateway/local by key prefix or base URL"""
    # e.g., "sk-or-" prefix → OpenRouter

def find_by_name(name: str) -> ProviderSpec | None:
    """Find by config field name"""
    # e.g., "anthropic" → Anthropic
```

### 8.4 Provider Configuration Example

```json
{
  "providers": {
    "anthropic": {
      "apiKey": "sk-ant-..."
    },
    "openai": {
      "apiKey": "sk-..."
    },
    "openrouter": {
      "apiKey": "sk-or-..."
    },
    "custom": {
      "apiKey": "...",
      "apiBase": "http://localhost:8080/v1"
    }
  },
  "agents": {
    "defaults": {
      "model": "claude-sonnet-4-20250514",
      "provider": "anthropic",
      "maxTokens": 8192,
      "temperature": 0.1
    }
  }
}
```

---

## 9. Communication Channels

### 9.1 Channel Base Class (`nanobot/channels/base.py`)

```python
class Channel(ABC):
    @abstractmethod
    async def start(self) -> None: ...
    
    @abstractmethod
    async def stop(self) -> None: ...
    
    @abstractmethod
    async def send(self, message: OutboundMessage) -> None: ...
    
    def is_allowed(self, user_id: str) -> bool:
        """Check if user is in allowFrom list"""
```

### 9.2 Available Channels

| Channel | File | Protocol | Key Features |
|---------|------|----------|--------------|
| **Web** | `web.py` | WebSocket | Keepalive, pending messages |
| **Telegram** | `telegram.py` | Long polling | Markdown→HTML, proxy support |
| **Discord** | `discord.py` | Gateway WS | Guild support, message splitting |
| **Slack** | `slack.py` | Socket mode | Threads, reactions |
| **WhatsApp** | `whatsapp.py` | Bridge (Node.js) | Via Baileys, localhost:3001 |
| **Email** | `email.py` | IMAP/SMTP | Subject parsing, attachments |
| **Matrix** | `matrix.py` | Matrix protocol | E2EE support (optional) |
| **Feishu/Lark** | `feishu.py` | WebSocket | Enterprise messaging |
| **DingTalk** | `dingtalk.py` | Stream mode | Enterprise messaging |
| **QQ** | `qq.py` | botpy SDK | Chinese IM |
| **Mochat** | `mochat.py` | Socket.IO | Custom protocol |

### 9.3 Channel Configuration Examples

```json
{
  "channels": {
    "telegram": {
      "token": "BOT_TOKEN",
      "allowFrom": ["user_id_1", "user_id_2"],
      "proxy": "socks5://127.0.0.1:1080"
    },
    "discord": {
      "token": "BOT_TOKEN",
      "allowFrom": ["user_id"]
    },
    "slack": {
      "appToken": "xapp-...",
      "botToken": "xoxb-...",
      "allowFrom": ["U12345"]
    },
    "email": {
      "imapHost": "imap.gmail.com",
      "imapPort": 993,
      "smtpHost": "smtp.gmail.com",
      "smtpPort": 587,
      "username": "bot@gmail.com",
      "password": "app_password",
      "allowFrom": ["user@example.com"]
    }
  }
}
```

### 9.4 Channel Manager (`nanobot/channels/manager.py`)

```python
class ChannelManager:
    async def start_all(self) -> None
    async def stop_all(self) -> None
    def get_channel(self, name: str) -> Channel | None
    async def send(self, message: OutboundMessage) -> None
```

---

## 10. Memory System

### 10.1 Semantic Memory (`nanobot/memory/store.py`)

ChromaDB-based vector storage for semantic search.

#### Configuration

```python
# Embedding model
model = "all-MiniLM-L6-v2"  # sentence-transformers

# Storage location
path = "~/.nanobot/workspace/users/{user_id}/memory/"
```

#### Memory Categories

| Category | Purpose | Examples |
|----------|---------|----------|
| `profile` | User identity info | Name, profession |
| `goal` | User objectives | "Learn Spanish", "Launch startup" |
| `preference` | User preferences | "Prefers morning meetings" |
| `task` | Active/completed tasks | "Review PR #123" |
| `general` | Other facts | "Uses VSCode", "Lives in SF" |

### 10.2 Memory Extraction (`nanobot/memory/extractor.py`)

Automatic extraction of facts from conversations.

```python
class MemoryExtractor:
    async def extract(self, conversation: list[dict]) -> list[Memory]:
        """Use LLM to extract memorable facts from conversation"""
        # Returns list of (fact, category, importance) tuples
```

### 10.3 Memory Consolidation

When `memory_window` (100 messages) is exceeded:

1. Extract key facts from older messages
2. Add to MEMORY.md and semantic store
3. Summarize and compress conversation history
4. Remove raw old messages from context

---

## 11. Skills System

### 11.1 Skill Anatomy

```markdown
---
name: skill-name
description: Short description
always: false       # Always include in context?
bins: [git, gh]     # Required executables
env: [GITHUB_TOKEN] # Required environment variables
---

# Skill Name

## Overview
What this skill does...

## Commands/Usage
How to use this skill...

## Examples
Concrete examples...
```

### 11.2 Skill Loading Flow

```python
# SkillManager.load_skill()
1. Check workspace/skills/{name}/SKILL.md (user override)
2. Fallback to nanobot/skills/{name}/SKILL.md (built-in)
3. Parse YAML frontmatter
4. Check requirements (bins, env)
5. Add to available skills
6. If always=true, include in every context
```

### 11.3 Progressive Skill Disclosure

Skills are summarized in XML format for efficient token usage:

```xml
<available_skills>
  <skill name="github" description="GitHub CLI operations" />
  <skill name="weather" description="Weather information" />
  <!-- Agent can request full skill content when needed -->
</available_skills>
```

---

## 12. Special Services

### 12.1 Onboarding Flow (`nanobot/agent/onboarding.py`)

New user setup wizard with 5 questions:

| Step | Field | Question |
|------|-------|----------|
| 1 | `name` | What's your name? |
| 2 | `profession` | What do you do for work? |
| 3 | `goals` | Top 1-2 goals you'd love help with? |
| 4 | `schedule` | Morning or evening person? Daily routine? |
| 5 | `preferences` | How do you like to work/communicate? |

#### Key Methods

```python
class OnboardingFlow:
    def is_onboarded(self) -> bool
    def get_next_question(self, answers: dict) -> str
    async def save_answer(self, field: str, answer: str, answers: dict) -> None
    async def run_step(self, user_message: str, answers: dict) -> tuple
```

#### State Persistence

```python
# OnboardingState stores answers in:
# {workspace}/users/{user_id}/onboarding.json
```

### 12.2 Heartbeat Service (`nanobot/heartbeat/service.py`)

Periodic agent wake-up to check for tasks.

#### Configuration

```python
interval_s = 1800  # 30 minutes default
heartbeat_file = "{workspace}/HEARTBEAT.md"
```

#### Two-Phase Execution

1. **Decision Phase**: Read `HEARTBEAT.md`, ask LLM if tasks exist
   - Returns `skip` (no tasks) or `run` (tasks found)
2. **Execution Phase**: If `run`, execute task via callback

#### HEARTBEAT.md Format

```markdown
# Active Tasks

- [ ] Check email at 9 AM
- [ ] Review calendar for tomorrow

# Completed

- [x] Send weekly report
```

### 12.3 Cron Service (`nanobot/cron/service.py`)

Task scheduling with multiple schedule types.

#### Schedule Types

| Type | Format | Example |
|------|--------|---------|
| `every_seconds` | Integer | `3600` (hourly) |
| `cron_expr` | Cron string | `"0 9 * * *"` (9 AM daily) |
| `at` | ISO datetime | `"2024-03-15T14:00:00"` |

#### Cron Job Storage

```json
// ~/.personal-agent/workspace/cron.json
{
  "jobs": [
    {
      "id": "abc123",
      "user_id": "user1",
      "task": "Remind to drink water",
      "schedule": {"cron_expr": "0 * * * *", "tz": "America/New_York"},
      "created_at": "2024-01-01T00:00:00Z"
    }
  ]
}
```

---

## 13. Configuration

### 13.1 Config Location

```
~/.personal-agent/config.json
```

### 13.2 Full Configuration Schema

```json
{
  "agents": {
    "defaults": {
      "model": "claude-sonnet-4-20250514",
      "provider": "anthropic",
      "maxTokens": 8192,
      "temperature": 0.1,
      "maxToolIterations": 40,
      "memoryWindow": 100
    }
  },
  "providers": {
    "anthropic": { "apiKey": "sk-ant-..." },
    "openai": { "apiKey": "sk-..." },
    "openrouter": { "apiKey": "sk-or-..." },
    "deepseek": { "apiKey": "..." },
    "gemini": { "apiKey": "..." },
    "groq": { "apiKey": "..." },
    "custom": {
      "apiKey": "...",
      "apiBase": "http://localhost:8080/v1"
    }
  },
  "integrations": {
    "google": {
      "clientId": "xxx.apps.googleusercontent.com",
      "clientSecret": "xxx"
    }
  },
  "tools": {
    "web": {
      "search": { "apiKey": "BRAVE_API_KEY" },
      "proxy": null
    },
    "exec": {
      "timeout": 60,
      "pathAppend": []
    },
    "restrictToWorkspace": false
  },
  "channels": {
    "telegram": { "token": "...", "allowFrom": [] },
    "discord": { "token": "...", "allowFrom": [] },
    "slack": { "appToken": "...", "botToken": "...", "allowFrom": [] }
  },
  "server": {
    "host": "0.0.0.0",
    "port": 8765
  },
  "mcp": {
    "servers": {
      "filesystem": {
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"]
      }
    }
  }
}
```

### 13.3 Environment Variables

| Variable | Purpose |
|----------|---------|
| `ANTHROPIC_API_KEY` | Anthropic API key |
| `OPENAI_API_KEY` | OpenAI API key |
| `OPENROUTER_API_KEY` | OpenRouter API key |
| `BRAVE_API_KEY` | Brave Search API key |
| `PERSONAL_AGENT_CONFIG` | Custom config path |

---

## 14. Frontend & Bridge

### 14.1 Frontend Structure (`frontend/`)

| File | Purpose |
|------|---------|
| `app/page.tsx` | Login/register page |
| `app/chat/page.tsx` | Main chat interface |
| `app/integrations/page.tsx` | OAuth integration management |
| `components/ChatWindow.tsx` | Chat message display |
| `components/InputBar.tsx` | Message input |
| `components/MessageBubble.tsx` | Individual message rendering |
| `components/MemoryPanel.tsx` | Memory display panel |
| `lib/api.ts` | Backend API calls |
| `lib/websocket.ts` | WebSocket hook with auto-reconnect |
| `lib/integrations.ts` | Integration status helpers |

### 14.2 WebSocket Protocol

```typescript
// Connection
ws://localhost:8765/ws/{token}

// Inbound message format (server → client)
{
  "type": "message",
  "content": "Assistant response",
  "timestamp": "2024-01-01T00:00:00Z"
}

// Outbound message format (client → server)
{
  "content": "User message",
  "channel": "web"
}
```

### 14.3 WhatsApp Bridge (`bridge/`)

Node.js TypeScript bridge using Baileys library.

| File | Purpose |
|------|---------|
| `src/server.ts` | WebSocket server (localhost:3001) |
| `src/whatsapp.ts` | Baileys client wrapper |
| `src/index.ts` | Entry point |

#### Security

- Binds to `127.0.0.1` only (no external access)
- Optional token authentication

---

## 15. Data Storage

| Data | Location | Format |
|------|----------|--------|
| Configuration | `~/.personal-agent/config.json` | JSON |
| Users | `~/.personal-agent/workspace/users.json` | JSON |
| Sessions | `~/.personal-agent/workspace/sessions/{session_id}.jsonl` | JSONL |
| Memory (ChromaDB) | `~/.personal-agent/workspace/users/{user_id}/memory/` | SQLite |
| Onboarding | `~/.personal-agent/workspace/users/{user_id}/onboarding.json` | JSON |
| OAuth Credentials | `~/.personal-agent/workspace/users/{user_id}/integrations/` | JSON |
| Cron Jobs | `~/.personal-agent/workspace/cron.json` | JSON |
| User Workspace | `~/.personal-agent/workspace/users/{user_id}/` | Directory |

---

## 16. Known Limitations & Issues

### 16.1 Agent Loop Limitations

| Limitation | Location | Impact |
|------------|----------|--------|
| **Max 40 iterations** | `loop.py` | Complex tasks may hit limit |
| **Error responses not persisted** | `loop.py#L268` | Prevents "400 loops" but loses error context |
| **Tool result truncation (500 chars)** | `loop.py` | Large tool outputs truncated in session |
| **Memory window (100 messages)** | `loop.py` | Consolidation may lose context |

### 16.2 Tool Limitations

| Tool | Limitation | Details |
|------|------------|---------|
| `exec` | Blocked patterns | May block legitimate commands matching deny patterns |
| `exec` | 60s timeout | Long-running commands will timeout |
| `exec` | 10K char output limit | Large outputs truncated |
| `write_file` | Text only | Cannot create binary files (PDFs, images) |
| `browser` | Headless only | No visual debugging |
| `gmail`/`calendar` | OAuth required | Needs Google OAuth setup |

### 16.3 Provider Limitations

| Provider | Limitation |
|----------|------------|
| All | Rate limits apply per provider |
| OpenRouter | Model availability varies |
| Custom | Must be OpenAI-compatible |

### 16.4 Channel Limitations

| Channel | Limitation |
|---------|------------|
| WhatsApp | Requires Node.js bridge running |
| Matrix E2EE | Requires `matrix-nio[e2e]` extra |
| Email | IMAP polling interval affects responsiveness |

### 16.5 Known Code Issues

```python
# 1. Empty content sanitization (providers/base.py#L48)
# MCP tools can return empty content causing provider errors
# Workaround: Content is replaced with "(empty)" string

# 2. Cron nesting block (cron.py#L75)
# Cannot schedule jobs from within cron callbacks
# This is intentional to prevent infinite loops

# 3. LLM error handling (loop.py#L268)
# Errors not added to messages to prevent retry loops
# Trade-off: Loses error context for debugging
```

---

## 17. Security Considerations

### 17.1 Built-in Protections

| Protection | Implementation |
|------------|----------------|
| Shell command deny patterns | `shell.py` regex patterns |
| URL validation | `web.py` URL parsing |
| Workspace restriction | `tools.restrictToWorkspace` config |
| Token authentication | `auth/middleware.py` |
| Per-user data isolation | Separate workspace dirs |
| Channel allowlists | `allowFrom` config per channel |

### 17.2 Security Best Practices

```bash
# 1. Secure config file permissions
chmod 600 ~/.personal-agent/config.json

# 2. Use environment variables for secrets
export ANTHROPIC_API_KEY="sk-ant-..."

# 3. Enable workspace restriction for untrusted use
# config.json: "tools": { "restrictToWorkspace": true }

# 4. Use allowFrom lists for channels
# config.json: "channels": { "telegram": { "allowFrom": ["your_id"] } }

# 5. Use HTTPS in production
# Behind reverse proxy (nginx/caddy) with TLS
```

### 17.3 Potential Risks

| Risk | Mitigation |
|------|------------|
| Shell command injection | Enable `restrictToWorkspace`, review deny patterns |
| File system access | Enable `restrictToWorkspace` |
| Credential exposure | Environment variables, secure config permissions |
| OAuth token theft | HTTPS required, secure callback URLs |

---

## 18. Deployment

### 18.1 Docker Deployment

```yaml
# docker-compose.yml
x-common-config: &common-config
  build:
    context: .
    dockerfile: Dockerfile
  volumes:
    - ~/.nanobot:/root/.nanobot

services:
  nanobot-gateway:
    container_name: nanobot-gateway
    <<: *common-config
    command: ["gateway"]
    restart: unless-stopped
    ports:
      - 18790:18790
    deploy:
      resources:
        limits:
          cpus: '1'
          memory: 1G
        reservations:
          cpus: '0.25'
          memory: 256M
```

```bash
# Run with Docker
docker-compose up -d nanobot-gateway
```

### 18.2 Local Development

```bash
# 1. Install dependencies
pip install -e ".[dev]"

# 2. Install Playwright browsers
playwright install chromium

# 3. Create config
mkdir -p ~/.personal-agent
cp config.example.json ~/.personal-agent/config.json
# Edit config with your API keys

# 4. Run backend
python run.py
# Or: python -m nanobot

# 5. Run frontend (separate terminal)
cd frontend
npm install
npm run dev
```

### 18.3 WhatsApp Bridge

```bash
# In separate terminal
cd bridge
npm install
npm start
```

---

## 19. Testing

### 19.1 Test Files

| Test File | Purpose |
|-----------|---------|
| `test_tool_validation.py` | JSON schema validation for tools |
| `test_task_cancel.py` | `/stop` command functionality |
| `test_loop_save_turn.py` | Message persistence |
| `test_consolidate_offset.py` | Memory consolidation |
| `test_memory_consolidation_types.py` | Memory category handling |
| `test_email_channel.py` | Email channel parsing |
| `test_matrix_channel.py` | Matrix protocol handling |
| `test_feishu_post_content.py` | Feishu message formatting |
| `test_cron_service.py` | Cron scheduling |
| `test_heartbeat_service.py` | Heartbeat wake-up |

### 19.2 Running Tests

```bash
# Run all tests
pytest tests/

# Run specific test
pytest tests/test_tool_validation.py

# Run with coverage
pytest --cov=nanobot tests/
```

### 19.3 Testing Patterns

```python
# Mocking pattern
from unittest.mock import AsyncMock, patch

@patch('nanobot.providers.litellm_provider.completion')
async def test_agent_response(mock_completion):
    mock_completion.return_value = AsyncMock(
        choices=[Mock(message=Mock(content="Hello"))]
    )
    # ... test code
```

---

## 20. Development Guide

### 20.1 Adding a New Tool

```python
# 1. Create tool file: nanobot/agent/tools/my_tool.py

from nanobot.agent.tools.base import Tool

class MyTool(Tool):
    @property
    def name(self) -> str:
        return "my_tool"
    
    @property
    def description(self) -> str:
        return "Description of what my tool does"
    
    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "param1": {
                    "type": "string",
                    "description": "First parameter"
                }
            },
            "required": ["param1"]
        }
    
    async def execute(self, param1: str, **kwargs) -> str:
        # Implementation
        return f"Result: {param1}"

# 2. Register in nanobot/agent/tools/__init__.py
from .my_tool import MyTool

# 3. Add to registry in loop.py or tools/__init__.py
registry.register(MyTool())
```

### 20.2 Adding a New Channel

```python
# 1. Create channel file: nanobot/channels/my_channel.py

from nanobot.channels.base import Channel

class MyChannel(Channel):
    def __init__(self, config: MyChannelConfig, bus: MessageBus):
        self.config = config
        self.bus = bus
    
    async def start(self) -> None:
        # Connect to service
        pass
    
    async def stop(self) -> None:
        # Disconnect
        pass
    
    async def send(self, message: OutboundMessage) -> None:
        # Send message to user
        pass
    
    def is_allowed(self, user_id: str) -> bool:
        return user_id in self.config.allow_from

# 2. Add config schema in nanobot/config/schema.py
class MyChannelConfig(BaseModel):
    api_key: str
    allow_from: list[str] = []

# 3. Register in nanobot/channels/manager.py
```

### 20.3 Adding a New Provider

```python
# 1. Add to registry: nanobot/providers/registry.py

PROVIDERS = (
    # ... existing providers
    ProviderSpec(
        name="myprovider",
        config_field="myprovider",
        env_key="MYPROVIDER_API_KEY",
        prefixes=["myprovider/"],
        keywords=["mymodel"],
        provider_class=LiteLLMProvider,  # or custom
    ),
)

# 2. If custom implementation needed, create:
# nanobot/providers/my_provider.py
```

### 20.4 Creating a Skill

```markdown
<!-- workspace/skills/my-skill/SKILL.md -->
---
name: my-skill
description: My custom skill
always: false
bins: []
env: []
---

# My Skill

## Overview
What this skill enables...

## Usage
How to use this skill...

## Examples
```
User: Do the skill thing
Agent: [uses the skill]
```
```

### 20.5 Code Style

```bash
# Linting
ruff check nanobot/

# Formatting
ruff format nanobot/

# Type checking
mypy nanobot/
```

---

## 21. API Reference

### 21.1 HTTP Endpoints

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/health` | GET | No | Health check |
| `/register` | POST | No | Register new user |
| `/login` | POST | No | Login existing user |
| `/ws/{token}` | WS | Token | WebSocket connection |
| `/integrations/status` | GET | Token | OAuth connection status |
| `/integrations/connect/{service}` | GET | Token | Start OAuth flow |
| `/integrations/callback` | GET | No | OAuth callback |
| `/integrations/disconnect/{service}` | DELETE | Token | Disconnect OAuth |

### 21.2 WebSocket Events

```python
# Inbound (server → client)
{
    "type": "message",      # Agent response
    "content": str,
    "timestamp": str
}
{
    "type": "typing",       # Agent is typing
}
{
    "type": "error",        # Error occurred
    "content": str
}

# Outbound (client → server)
{
    "content": str,         # User message
    "channel": "web"
}
```

### 21.3 Tool Call Format

```python
# LLM tool call request
{
    "id": "call_abc123",
    "type": "function",
    "function": {
        "name": "exec",
        "arguments": "{\"command\": \"ls -la\"}"
    }
}

# Tool result format
{
    "role": "tool",
    "tool_call_id": "call_abc123",
    "content": "file1.txt\nfile2.txt"
}
```

---

## 22. Troubleshooting

### 22.1 Common Issues

| Issue | Solution |
|-------|----------|
| "Connection refused" on port 8765 | Ensure backend is running: `python run.py` |
| "Invalid token" | Re-register or login to get new token |
| Tool timeout | Increase `tools.exec.timeout` in config |
| Memory not working | Check ChromaDB installation: `pip install chromadb` |
| Gmail/Calendar not working | Complete OAuth flow at `/integrations` |
| WhatsApp not connecting | Ensure bridge is running: `cd bridge && npm start` |

### 22.2 Debug Mode

```python
# Enable debug logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Or via environment
export LOGURU_LEVEL=DEBUG
```

### 22.3 Log Locations

| Component | Log |
|-----------|-----|
| Backend | stdout/stderr |
| Frontend | Browser console |
| Bridge | stdout/stderr |

### 22.4 Health Checks

```bash
# Check backend health
curl http://localhost:8765/health

# Check WebSocket
wscat -c ws://localhost:8765/ws/YOUR_TOKEN

# Check WhatsApp bridge
curl http://localhost:3001/health
```

---

## Quick Reference Card

```
┌─────────────────────────────────────────────────────────────┐
│                    NANOBOT QUICK REFERENCE                   │
├─────────────────────────────────────────────────────────────┤
│ Start Backend:    python run.py                              │
│ Start Frontend:   cd frontend && npm run dev                 │
│ Start Bridge:     cd bridge && npm start                     │
│ Config File:      ~/.personal-agent/config.json             │
│ Default Port:     8765                                       │
├─────────────────────────────────────────────────────────────┤
│ LIMITS                                                       │
│ Max Iterations:   40 tool calls per turn                     │
│ Memory Window:    100 messages before consolidation          │
│ Exec Timeout:     60 seconds                                 │
│ Subagent Limit:   15 iterations                              │
├─────────────────────────────────────────────────────────────┤
│ KEY FILES                                                    │
│ Entry Point:      nanobot/main.py (Application)              │
│ Agent Loop:       nanobot/agent/loop.py (AgentLoop)          │
│ Tools:            nanobot/agent/tools/*.py                   │
│ Channels:         nanobot/channels/*.py                      │
│ Providers:        nanobot/providers/*.py                     │
│ Memory:           nanobot/memory/store.py                    │
├─────────────────────────────────────────────────────────────┤
│ COMMANDS                                                     │
│ /stop             Cancel active task                         │
│ /memory           Show memory contents                       │
│ /skills           List available skills                      │
└─────────────────────────────────────────────────────────────┘
```

---

*Last Updated: March 2026*
*Version: 0.1.0*
