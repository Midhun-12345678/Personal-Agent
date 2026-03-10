# Nanobot System Overview

## Summary

Nanobot is a personal AI assistant platform that combines LLM capabilities with a rich set of tools, integrations, and multi-channel support. It provides a unified interface for automation, scheduling, and AI-powered task execution.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend                              │
│                   (Next.js Web App)                          │
└─────────────────────┬───────────────────────────────────────┘
                      │ WebSocket
┌─────────────────────▼───────────────────────────────────────┐
│                    WebServer (FastAPI)                       │
│  - /register (POST) - User registration                      │
│  - /ws/{token} (WS) - Real-time communication                │
│  - /integrations/* - OAuth endpoints                         │
│  - /health (GET) - Health check                              │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│                     Application                              │
│  - AuthManager: Token-based user auth                        │
│  - MessageBus: Inbound/outbound message routing              │
│  - AgentLoop: Per-user AI agent instances                    │
│  - SessionManager: Conversation session handling             │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│                    AgentLoop                                 │
│  - LLM Provider (LiteLLM)                                    │
│  - Tool Execution Engine                                     │
│  - Memory System (ChromaDB + Embeddings)                     │
│  - Onboarding Flow                                           │
│  - Cron Service (Scheduled Tasks)                            │
└─────────────────────────────────────────────────────────────┘
```

---

## Core Components

### 1. LLM Providers
Supports multiple AI providers via LiteLLM abstraction:

| Provider | Status | Config Key |
|----------|--------|------------|
| OpenAI | ✅ Supported | `providers.openai.apiKey` |
| Anthropic | ✅ Supported | `providers.anthropic.apiKey` |
| OpenRouter | ✅ Supported | `providers.openrouter.apiKey` |
| DeepSeek | ✅ Supported | `providers.deepseek.apiKey` |
| Groq | ✅ Supported | `providers.groq.apiKey` |
| Gemini | ✅ Supported | `providers.gemini.apiKey` |
| Azure OpenAI | ✅ Supported | Via OpenAI config |
| Custom (OpenAI-compatible) | ✅ Supported | `providers.custom.apiKey` |

### 2. Memory System
- **Type**: Semantic vector memory
- **Storage**: ChromaDB (persistent)
- **Embeddings**: sentence-transformers (all-MiniLM-L6-v2)
- **Capabilities**:
  - Automatic memory extraction from conversations
  - Semantic search for relevant memories
  - Per-user isolated collections
  - Memory categories: preference, fact, goal, context

### 3. Authentication
- Token-based authentication
- Per-user isolation
- Persistent user storage (users.json)

---

## Tools

### Core Tools

| Tool | Name | Description | Dependencies |
|------|------|-------------|--------------|
| Shell Execution | `exec` | Run shell commands | Built-in |
| File Read | `read_file` | Read file contents | Built-in |
| File Write | `write_file` | Write/create files | Built-in |
| File Edit | `edit_file` | Edit existing files | Built-in |
| Web Search | `web_search` | Search the web | Brave API key |
| Web Fetch | `web_fetch` | Fetch URL content | Built-in |
| Browser | `browser` | Full browser automation | Playwright |
| Gmail | `gmail` | Email operations | Google OAuth |
| Calendar | `calendar` | Calendar management | Google OAuth |
| Cron | `cron` | Schedule tasks/reminders | Built-in |
| Message | `message` | Send messages to user | Built-in |
| Spawn | `spawn` | Create background subagents | Built-in |

### Tool Details

#### exec (Shell Execution)
- **Actions**: Run any shell command
- **Safety**: Deny patterns for dangerous commands (rm -rf, format, dd, etc.)
- **Config**: `tools.exec.timeout`, `tools.exec.pathAppend`
- **Optional**: `tools.restrictToWorkspace` to limit file access

#### browser (Browser Automation)
- **Actions**: navigate, fill_form, click, extract
- **Requires**: `playwright install chromium`
- **Features**:
  - Headless browser automation
  - Form filling
  - Element clicking
  - Content extraction with LLM

#### gmail
- **Actions**: search, read, send, draft
- **Requires**: Google OAuth credentials
- **Scopes**: gmail.readonly, gmail.send, gmail.compose

#### calendar
- **Actions**: list, create, delete
- **Requires**: Google OAuth credentials
- **Scopes**: calendar

#### cron (Task Scheduler)
- **Actions**: add, list, remove
- **Scheduling Options**:
  - `every_seconds`: Recurring interval
  - `cron_expr`: Cron expression (e.g., "0 9 * * *")
  - `at`: One-time ISO datetime

#### web_search
- **Requires**: Brave Search API key
- **Config**: `tools.web.search.apiKey`
- **Returns**: Titles, URLs, snippets

#### web_fetch
- **Uses**: Readability for content extraction
- **Modes**: markdown, text
- **Features**: Auto-redirect handling, JSON parsing

---

## Skills (Extended Capabilities)

Skills are markdown-based instruction sets that extend agent capabilities:

| Skill | Description | Requirements |
|-------|-------------|--------------|
| `github` | GitHub operations via `gh` CLI | gh CLI installed |
| `weather` | Weather information | None (uses wttr.in) |
| `summarize` | Summarize URLs, files, YouTube | None |
| `tmux` | Remote tmux control | tmux installed |
| `clawhub` | Install skills from registry | None |
| `skill-creator` | Create new skills | None |

---

## Communication Channels

### Currently Active
| Channel | Type | Status |
|---------|------|--------|
| Web | WebSocket | ✅ Active |

### Available (Require Configuration)
| Channel | Config Key | Features |
|---------|------------|----------|
| Telegram | `channels.telegram` | Bot token, proxy support |
| Discord | `channels.discord` | Bot token, guild support |
| Slack | `channels.slack` | Socket mode, threads |
| WhatsApp | `channels.whatsapp` | Bridge connection |
| Email | `channels.email` | IMAP/SMTP |
| Matrix | `channels.matrix` | E2EE support |
| Feishu/Lark | `channels.feishu` | WebSocket |
| DingTalk | `channels.dingtalk` | Stream mode |
| QQ | `channels.qq` | botpy SDK |
| Mochat | `channels.mochat` | Socket.IO |

---

## Integrations (OAuth)

### Google Services
- **Gmail**: Read, search, send, draft emails
- **Calendar**: Create, view, delete events
- **Setup**: Configure `integrations.google.clientId` and `clientSecret`

### OAuth Endpoints
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/integrations/status` | GET | Check connection status |
| `/integrations/connect/{service}` | GET | Start OAuth flow |
| `/integrations/callback` | GET | OAuth callback |
| `/integrations/disconnect/{service}` | DELETE | Disconnect service |

---

## Configuration

Configuration file: `~/.personal-agent/config.json`

### Full Schema Example
```json
{
  "agents": {
    "defaults": {
      "model": "gpt-4o",
      "provider": "openai",
      "maxTokens": 8192,
      "temperature": 0.1,
      "maxToolIterations": 40,
      "memoryWindow": 100
    }
  },
  "providers": {
    "openai": {
      "apiKey": "sk-..."
    },
    "anthropic": {
      "apiKey": "sk-ant-..."
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
      "search": {
        "apiKey": "BRAVE_API_KEY"
      },
      "proxy": null
    },
    "exec": {
      "timeout": 60
    },
    "restrictToWorkspace": false
  },
  "server": {
    "host": "0.0.0.0",
    "port": 8765
  }
}
```

---

## Data Storage

| Data | Location | Format |
|------|----------|--------|
| Configuration | `~/.personal-agent/config.json` | JSON |
| Users | `~/.personal-agent/workspace/users.json` | JSON |
| Memory (ChromaDB) | `~/.personal-agent/workspace/users/memory/` | SQLite |
| Sessions | `~/.personal-agent/workspace/sessions/` | JSON |
| Onboarding State | `~/.personal-agent/workspace/{user_id}/onboarding.json` | JSON |
| OAuth Credentials | `~/.personal-agent/workspace/{user_id}/integrations/` | JSON |
| Cron Jobs | `~/.personal-agent/workspace/cron.json` | JSON |

---

## Features Summary

### User-Facing Features
1. **Conversational AI** - Natural language interaction
2. **Memory** - Remembers user preferences, facts, goals
3. **Task Scheduling** - Reminders, recurring tasks
4. **Email Automation** - Gmail integration
5. **Calendar Management** - Google Calendar integration
6. **Web Browsing** - Navigate and extract web content
7. **File Operations** - Read, write, edit files
8. **Shell Commands** - Execute system commands
9. **Web Search** - Search the internet
10. **Background Tasks** - Spawn subagents for complex tasks

### System Features
1. **Multi-Provider LLM** - Switch between AI providers
2. **Token Authentication** - Secure user isolation
3. **WebSocket Real-time** - Instant communication
4. **OAuth Integration** - One-click service connections
5. **Extensible Skills** - Markdown-based capability extension
6. **Onboarding Flow** - New user setup wizard

---

## Security Considerations

### Built-in Protections
- Shell command deny patterns (rm -rf, format, etc.)
- URL validation for web tools
- Workspace restriction option
- Token-based authentication
- Per-user data isolation

### Potential Risks for Production
| Risk | Mitigation |
|------|------------|
| Shell command injection | Enable `restrictToWorkspace`, review deny patterns |
| File system access | Enable `restrictToWorkspace` |
| Credential exposure | Use environment variables, secure config |
| OAuth token theft | HTTPS required, secure callback URLs |

---

## Dependencies

### Python (Backend)
- fastapi, uvicorn (web server)
- litellm (LLM abstraction)
- chromadb (vector database)
- sentence-transformers (embeddings)
- httpx (HTTP client)
- playwright (browser automation)
- google-api-python-client (Gmail/Calendar)
- pydantic (validation)
- loguru (logging)
- apscheduler (cron)

### Node.js (Frontend)
- next.js 14
- react 18
- tailwindcss
- lucide-react (icons)

---

## API Endpoints Summary

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/health` | GET | No | Health check |
| `/register` | POST | No | Register new user |
| `/ws/{token}` | WS | Token | WebSocket connection |
| `/integrations/status` | GET | Token | OAuth status |
| `/integrations/connect/{service}` | GET | Token | Start OAuth |
| `/integrations/callback` | GET | No | OAuth callback |
| `/integrations/disconnect/{service}` | DELETE | Token | Disconnect OAuth |

---

## Testing Checklist

### Phase 1: Core Functionality
- [ ] User registration
- [ ] WebSocket connection
- [ ] Basic chat response
- [ ] Memory storage and retrieval
- [ ] Onboarding flow completion

### Phase 2: Tool Execution
- [ ] exec (shell commands)
- [ ] read_file / write_file
- [ ] web_fetch (URL content)
- [ ] web_search (if API key configured)
- [ ] browser (if Playwright installed)
- [ ] cron (schedule + trigger)

### Phase 3: Integrations
- [ ] Google OAuth flow
- [ ] Gmail operations
- [ ] Calendar operations

### Phase 4: Edge Cases
- [ ] Reconnection handling
- [ ] Error recovery
- [ ] Token expiration
- [ ] Concurrent users
- [ ] Large message handling

### Phase 5: Security
- [ ] Dangerous command blocking
- [ ] Path traversal prevention
- [ ] Invalid token rejection
- [ ] OAuth state validation

---

## Version Information

- **Platform**: Personal Agent (Nanobot)
- **Backend**: Python 3.11+
- **Frontend**: Next.js 14
- **Default Port**: 8765
- **Config Path**: `~/.personal-agent/config.json`
