# Personal Agent

Your personal AI that remembers everything and takes real action on your behalf.

## Quick Start

### Step 1: Install and Setup

```bash
pip install -e .
python setup.py
```

### Step 2: Add Your API Key

Edit `~/.personal-agent/config.json` and replace `YOUR_ANTHROPIC_API_KEY_HERE` with your actual Anthropic API key.

Get one at: https://console.anthropic.com/

### Step 3: Run

**Backend:**
```bash
python run.py
```

**Frontend (in a separate terminal):**
```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:3000 in your browser.

## Features

- **Semantic Memory**: Remembers facts about you across conversations using vector embeddings (ChromaDB + sentence-transformers)
- **Action Tools**: 
  - **Gmail**: Search, read, send, and draft emails
  - **Calendar**: List, create, and delete events
  - **Browser**: Navigate, fill forms, click elements, and extract data
- **Onboarding**: Learns about you through a guided 5-question flow on first interaction
- **Multi-User**: Each user gets isolated workspace with their own memory and data

## Architecture

```
personal-agent/
├── run.py                  # Entry point - starts backend
├── setup.py                # First-time config setup
├── frontend/               # Next.js chat interface
│   ├── app/                # Pages (landing, chat)
│   ├── components/         # React components
│   └── lib/                # API & WebSocket utilities
└── nanobot/                # Python backend
    ├── main.py             # Application orchestrator
    ├── agent/              # Agent loop, tools, memory
    │   ├── loop.py         # Core processing engine
    │   ├── tools/          # Gmail, Calendar, Browser tools
    │   ├── onboarding.py   # User onboarding flow
    │   └── onboarding_state.py
    ├── auth/               # Token-based authentication
    ├── bus/                # Message queue (channel ↔ agent)
    ├── channels/           # WebSocket server, web channel
    ├── memory/             # Semantic memory (ChromaDB)
    └── providers/          # LLM providers (Anthropic, etc.)
```

## API Endpoints

- `POST /register` - Register a new user, returns `{user_id, token}`
- `GET /health` - Health check
- `WS /ws/{token}` - WebSocket for real-time chat

## Configuration

Config file: `~/.personal-agent/config.json`

```json
{
  "providers": {
    "anthropic": {
      "apiKey": "sk-ant-..."
    }
  },
  "agents": {
    "defaults": {
      "model": "claude-sonnet-4-20250514",
      "provider": "anthropic"
    }
  },
  "server": {
    "host": "0.0.0.0",
    "port": 8765
  }
}
```

## Requirements

- Python 3.11+
- Node.js 18+
- Anthropic API key

## Built By

Midhun

## License

MIT
