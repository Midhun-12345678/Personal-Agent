# Nanobot — Your Personal AI Agent

> Handles complex multi-step tasks autonomously. Schedule meetings, draft emails, manage files, search the web — all from a single chat interface.

## What It Can Do

- **Multi-step task chaining** — "Schedule a team meeting tomorrow at 2pm and send invites" executes as a complete workflow with real-time tool visibility
- **Email & Calendar integration** — Connect your Gmail and Google Calendar for seamless scheduling, email drafting, and inbox management
- **Persistent memory across sessions** — ChromaDB-powered semantic memory remembers your preferences, past conversations, and context
- **11 messaging channels** — Chat via web UI, Telegram, Discord, Slack, WhatsApp, SMS, email, and more
- **Smart error recovery** — Automatic retries with exponential backoff, conflict detection, and alternative suggestions

## Quick Start (Docker)

### 1. Clone & Configure

```bash
git clone https://github.com/yourusername/nanobot.git
cd nanobot
cp .env.example .env
```

Edit `.env` and add at least one LLM API key:

```bash
# Choose one or more:
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
OPENROUTER_API_KEY=sk-or-...
```

### 2. Start Everything

```bash
docker-compose up --build -d
```

This will:
- Build and start the backend (FastAPI on port 8765)
- Build and start the frontend (Next.js on port 3000)
- Build and start the WhatsApp bridge (Node.js on port 3001)

### 3. Open the App

Visit **http://localhost:3000**

1. Click "Register" and create an account
2. Start chatting with your AI agent
3. Try: "Search for Python tutorials and summarize the top 3 results"

## Connecting Google (Gmail + Calendar)

To enable Gmail and Google Calendar integration:

**Step 1:** Get OAuth credentials from Google Cloud Console
- Go to https://console.cloud.google.com
- Create a new project (or select existing)
- Enable Gmail API and Google Calendar API
- Go to "Credentials" → "Create Credentials" → "OAuth 2.0 Client ID"
- Application type: Web application
- Authorized redirect URIs: `http://localhost:8765/integrations/callback`
- Copy your Client ID and Client Secret

**Step 2:** Add credentials to `.env`
```bash
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
```

**Step 3:** Restart services
```bash
docker-compose restart backend
```

**Step 4:** Connect your account
- Visit http://localhost:3000/integrations
- Click "Connect Google"
- Complete the OAuth flow
- Grant permissions for Gmail and Calendar

Now you can say things like:
- "Check my calendar for this week"
- "Draft an email to john@example.com about the project update"
- "Schedule a meeting with the team tomorrow at 2pm"

## Connecting Messaging Channels

### Telegram

**Step 1:** Create a bot
- Open Telegram and message [@BotFather](https://t.me/botfather)
- Send `/newbot` and follow the prompts
- Copy your bot token (looks like `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)

**Step 2:** Add to config

Edit `~/.personal-agent/config.json`:
```json
{
  "channels": {
    "telegram": {
      "enabled": true,
      "token": "123456789:ABCdefGHIjklMNOpqrsTUVwxyz"
    }
  }
}
```

Or set in `.env`:
```bash
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
```

**Step 3:** Restart
```bash
docker-compose restart backend
```

Now message your bot on Telegram to interact with your agent!

### Discord, Slack, WhatsApp

Similar setup process:
- **Discord:** Create a bot at https://discord.com/developers, get bot token
- **Slack:** Create an app at https://api.slack.com/apps, get bot and app tokens
- **WhatsApp:** Bridge service runs on port 3001, scan QR code to connect

See the `nanobot/channels/` directory for all available channels and their configuration requirements.

## Running Without Docker

### Prerequisites

- Python 3.11 or higher
- Node.js 20 or higher
- Git

### Backend

```bash
# Install Python dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium

# Start the backend
python run.py
```

Backend runs on http://localhost:8765

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend runs on http://localhost:3000

### WhatsApp Bridge (optional)

```bash
cd bridge
npm install
npm run build
npm start
```

Bridge runs on http://localhost:3001

## Configuration

Nanobot looks for configuration at `~/.personal-agent/config.json`

Minimal config to get started:

```json
{
  "agents": {
    "defaults": {
      "model": "claude-sonnet-4-20250514",
      "provider": "anthropic"
    }
  },
  "providers": {
    "anthropic": {
      "apiKey": "sk-ant-..."
    }
  }
}
```

Full configuration options:

```json
{
  "agents": {
    "defaults": {
      "model": "claude-sonnet-4-20250514",
      "provider": "anthropic",
      "temperature": 0.7,
      "maxTokens": 4096
    }
  },
  "providers": {
    "anthropic": {
      "apiKey": "sk-ant-..."
    },
    "openai": {
      "apiKey": "sk-...",
      "apiBase": "https://api.openai.com/v1"
    }
  },
  "tools": {
    "web": {
      "search": {
        "apiKey": "BSA...",
        "serpApiKey": ""
      },
      "proxy": null
    }
  },
  "integrations": {
    "google": {
      "clientId": "your-client-id.apps.googleusercontent.com",
      "clientSecret": "your-client-secret"
    }
  },
  "channels": {
    "telegram": {
      "enabled": true,
      "token": "123456789:ABC..."
    },
    "discord": {
      "enabled": false,
      "token": ""
    }
  }
}
```

Data is stored in `~/.personal-agent/workspace/`:
- `users/{user_id}/` - User-specific data, sessions, memory
- `chroma/` - ChromaDB vector database for semantic memory
- `sessions/` - Conversation history

## Architecture

Nanobot is a multi-service architecture designed for flexibility and scalability:

- **Backend:** FastAPI server with WebSocket support, handles agent loops, tool execution, and LLM orchestration via LiteLLM (supports 100+ providers)
- **Frontend:** Next.js 14 app with real-time WebSocket communication, Tailwind CSS for styling, and React hooks for state management
- **WhatsApp Bridge:** Optional Node.js TypeScript service that connects WhatsApp via Baileys to the backend WebSocket API
- **Storage:** ChromaDB for semantic memory with sentence-transformers embeddings, SQLite for structured data, filesystem for sessions and logs
- **Browser Automation:** Playwright (Chromium) enables the browser tool for web scraping and automation tasks

Key features:
- **Multi-step planning:** Detects complex tasks (2+ action verbs), generates execution plans, shows real-time tool progress
- **Error recovery:** Classifies errors (retryable/conflict/auth/fatal), implements exponential backoff retries, suggests alternatives
- **Memory system:** Persistent user memory with semantic search, automatic preference injection, conversation summarization
- **Usage tracking:** Logs every task with tools used, success/failure, duration, estimated time saved

## Built With

- **[FastAPI](https://fastapi.tiangolo.com/)** - High-performance Python web framework for the backend API
- **[LiteLLM](https://github.com/BerriAI/litellm)** - Unified LLM interface supporting 100+ providers (OpenAI, Anthropic, Gemini, etc.)
- **[ChromaDB](https://www.trychroma.com/)** - Vector database for semantic memory and retrieval
- **[Next.js 14](https://nextjs.org/)** - React framework with App Router for the frontend
- **[Playwright](https://playwright.dev/)** - Browser automation for web scraping and interaction
- **[Tailwind CSS](https://tailwindcss.com/)** - Utility-first CSS framework for styling
- **[sentence-transformers](https://www.sbert.net/)** - State-of-the-art text embeddings for semantic search

## Features Overview

### Implemented Features (All 7 Steps Complete)

1. ✅ **Intent Classification & Auto-Confirmation** - Classifies actions as reversible/irreversible, auto-confirms after 30s timeout
2. ✅ **Calendar Conflict Detection** - Checks for scheduling conflicts, suggests alternative times
3. ✅ **Memory Tool with Preference Injection** - ChromaDB-backed semantic memory, auto-injects preferences into every conversation
4. ✅ **Task Planning System** - Two-phase planning (plan → execute), shows formatted plan with emojis, completion summary
5. ✅ **Error Recovery** - Smart retry with exponential backoff, conflict resolution, alternative suggestions
6. ✅ **Usage Dashboard** - Tracks tasks, tools used, time saved, shows stats in frontend
7. ✅ **Real-time Tool Visibility** - Live tool execution indicators, collapsible task plans, animated spinners

### Tools Available

- **Gmail** - Send, read, search emails
- **Google Calendar** - Create events, check availability, list upcoming
- **File System** - Read, write, edit files
- **Web Search** - Brave Search API integration
- **Browser** - Playwright-powered web automation
- **Shell** - Execute commands (with safety checks)
- **Memory** - Read, write, search semantic memory
- **Cron** - Schedule recurring tasks

## Development

### Project Structure

```
nanobot/
├── nanobot/              # Python backend
│   ├── agent/           # Agent loop, tools, planning
│   ├── bus/             # Message bus for channel-agent communication
│   ├── channels/        # 11 messaging channels
│   ├── integrations/    # OAuth, external services
│   ├── memory/          # ChromaDB memory store
│   └── providers/       # LLM provider wrappers
├── frontend/            # Next.js frontend
│   ├── app/            # Next.js App Router pages
│   ├── components/      # React components
│   └── lib/            # WebSocket, utilities
├── bridge/              # WhatsApp bridge (TypeScript)
└── run.py              # Backend entry point
```

### Running Tests

```bash
# Backend validation
cd nanobot
python test_memory_validation.py
python test_task_planner_validation.py
python test_error_recovery_validation.py

# Compile checks
python -m py_compile nanobot/agent/loop.py
python -m py_compile nanobot/agent/tools/memory_tool.py
```

### Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Troubleshooting

### Issue: Backend fails to start

**Check:**
- Is at least one LLM API key configured in `.env`?
- Is port 8765 already in use? (`lsof -i :8765`)
- Check logs: `docker-compose logs backend`

### Issue: Frontend can't connect to backend

**Check:**
- Is backend healthy? Visit http://localhost:8765/health
- Check `NEXT_PUBLIC_API_URL` environment variable
- For Docker: Use `http://localhost:8765` for client-side, `http://backend:8765` for SSR

### Issue: Playwright browser fails

**Check:**
- Are Chromium dependencies installed? (`playwright install chromium --with-deps`)
- Is there enough disk space?
- Try running outside Docker first to isolate the issue

### Issue: Memory/ChromaDB errors

**Check:**
- Is `~/.personal-agent/workspace/` writable?
- Is ChromaDB initialized? Check `workspace/chroma/` directory
- Try deleting ChromaDB and restarting: `rm -rf ~/.personal-agent/workspace/chroma`

## License

MIT License - see LICENSE file for details

## Acknowledgments

- Built with [Claude](https://www.anthropic.com/claude) (Opus 4.6)
- Inspired by personal AI assistants and autonomous agents
- Thanks to the open-source community for the amazing tools

---

**Star ⭐ this repo if Nanobot helps you save time!**
