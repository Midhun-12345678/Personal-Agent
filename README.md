# YOURbot — Personal AI Agent

> Autonomous multi-step task execution across email, calendar, files, 
> web, and 11 messaging channels — from a single natural language command.

[![Live Demo](https://img.shields.io/badge/Demo-Live%20on%20Vercel-brightgreen)](https://personalagent-theta.vercel.app/)
[![GitHub](https://img.shields.io/badge/GitHub-Repository-black)](https://github.com/Midhun-12345678/Personal-Agent)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![Next.js](https://img.shields.io/badge/Frontend-Next.js%2014-black.svg)](https://nextjs.org/)
[![Docker](https://img.shields.io/badge/Deploy-Docker-blue.svg)](https://www.docker.com/)

---

## The Problem

Knowledge workers spend 2-3 hours daily on repetitive coordination tasks — 
scheduling meetings, drafting emails, managing files, searching for information.

These tasks are too fragmented for traditional automation but too simple 
to justify human attention. An autonomous agent that understands natural 
language and executes multi-step workflows solves this entirely.

---

## What This Does

One message. Multiple actions. Real results.
```
"Schedule a team meeting tomorrow at 2pm, create an agenda 
doc, and send everyone the calendar invite with the doc link"

Agent executes:
→ Step 1: Check calendar for conflicts at 2pm tomorrow
→ Step 2: Create agenda document in file system  
→ Step 3: Create Google Calendar event with doc link
→ Step 4: Send Gmail invites to all attendees
→ Done: "Meeting set for Tuesday 2pm. Agenda created. 
         4 invites sent. No conflicts found."
```

---

## Key Numbers

| Capability | Detail |
|------------|--------|
| Messaging channels supported | 11 (Web, Telegram, Discord, Slack, WhatsApp, SMS, Email + more) |
| Tools available | 8 (Gmail, Calendar, Files, Web Search, Browser, Shell, Memory, Cron) |
| LLM providers supported | 100+ via LiteLLM |
| Memory backend | ChromaDB semantic vector search |
| Task planning | Two-phase: Plan → Execute with real-time visibility |
| Error recovery | Exponential backoff, conflict detection, alternatives |

---

## Live Demo

**Web App:** https://personalagent-theta.vercel.app/

Try these commands after connecting your Google account:
- `"Check my calendar for this week"`
- `"Draft an email to [anyone] about project update"`
- `"Search for the latest AI news and summarize top 3"`
- `"Create a file called notes.txt with my meeting agenda"`

---

## All 7 Production Features

1. **Intent Classification & Auto-Confirmation**  
   Classifies every action as reversible or irreversible before executing.  
   Irreversible actions (send email, delete file) show a preview with  
   30-second auto-confirm timeout — preventing accidental execution.

2. **Calendar Conflict Detection**  
   Checks existing events before booking. If conflict found, suggests  
   3 alternative time slots automatically.

3. **Persistent Semantic Memory**  
   ChromaDB-backed vector memory remembers preferences, past conversations,  
   and context across sessions. Auto-injects relevant memories into every  
   new conversation.

4. **Multi-Step Task Planning**  
   Detects complex tasks (2+ action verbs), generates a formatted execution  
   plan shown to user before running, then executes with live tool progress.

5. **Smart Error Recovery**  
   Classifies errors as retryable, conflict, auth, or fatal. Implements  
   exponential backoff for retryable errors. Suggests alternatives for  
   conflicts. Never crashes silently.

6. **Usage Dashboard**  
   Tracks every task: tools used, success/failure, duration, estimated  
   time saved. Visible in the frontend dashboard.

7. **Real-Time Tool Visibility**  
   Live indicators show exactly which tool is running. Collapsible task  
   plans. Animated progress spinners. No black-box execution.

---

## Tools Available

| Tool | Capability |
|------|-----------|
| **Gmail** | Send, read, search, draft emails |
| **Google Calendar** | Create events, check availability, list upcoming |
| **File System** | Read, write, edit files with version tracking |
| **Web Search** | Brave Search API — real-time web results |
| **Browser** | Playwright-powered full web automation |
| **Shell** | Execute commands with safety classification |
| **Memory** | Read, write, semantic search across sessions |
| **Cron** | Schedule recurring automated tasks |

---

## Architecture
```
User (Web / Telegram / Slack / WhatsApp / ...)
              │
              ▼
    ┌─────────────────────┐
    │   FastAPI Backend   │  WebSocket + REST
    │   (port 8765)       │  LiteLLM orchestration
    │                     │  Agent loop + tool execution
    └──────────┬──────────┘
               │
    ┌──────────┼──────────┐
    │          │          │
    ▼          ▼          ▼
 ChromaDB   SQLite    Filesystem
 (semantic  (structured (sessions,
  memory)    audit log)  workspace)
               │
    ┌──────────┼──────────┐
    │          │          │
    ▼          ▼          ▼
  Gmail    Calendar   Browser
  API       API      (Playwright)

Frontend: Next.js 14 — App Router, WebSocket, Tailwind
Bridge:   Node.js TypeScript — WhatsApp via Baileys
```

---

## Tech Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| Backend | FastAPI + WebSocket | Async, real-time tool streaming |
| LLM Interface | LiteLLM | 100+ provider support, single API |
| Memory | ChromaDB + sentence-transformers | Semantic search across sessions |
| Frontend | Next.js 14 + Tailwind | Real-time WebSocket UI |
| Browser Automation | Playwright (Chromium) | Full web interaction capability |
| Google Integration | OAuth 2.0 | Gmail + Calendar with user consent |
| Messaging Bridge | Node.js + Baileys | WhatsApp without Business API |
| Containerization | Docker + docker-compose | One-command deployment |

---

## Quick Start (Docker)
```bash
# 1. Clone and configure
git clone https://github.com/Midhun-12345678/Personal-Agent.git
cd Personal-Agent
cp .env.example .env

# 2. Add your LLM API key to .env
ANTHROPIC_API_KEY=sk-ant-...
# or OPENAI_API_KEY / OPENROUTER_API_KEY

# 3. Start everything
docker-compose up --build -d

# 4. Open http://localhost:3000
```

---

## Connecting Google (Gmail + Calendar)

**Step 1:** Get OAuth credentials from Google Cloud Console
- Enable Gmail API and Google Calendar API
- Create OAuth 2.0 Client ID (Web application)
- Authorized redirect URI: `http://localhost:8765/integrations/callback`

**Step 2:** Add to `.env`
```bash
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
```

**Step 3:** Connect at `http://localhost:3000/integrations`

---

## Running Without Docker
```bash
# Backend
pip install -r requirements.txt
playwright install chromium
python run.py
# Runs on http://localhost:8765

# Frontend (new terminal)
cd frontend && npm install && npm run dev
# Runs on http://localhost:3000
```

---

## Project Structure
```
Personal-Agent/
├── nanobot/
│   ├── agent/        # Agent loop, tool execution, task planning
│   ├── bus/          # Message bus — channel to agent communication
│   ├── channels/     # 11 messaging channel integrations
│   ├── integrations/ # Google OAuth, external service connectors
│   ├── memory/       # ChromaDB semantic memory store
│   └── providers/    # LiteLLM provider wrappers
├── frontend/
│   ├── app/          # Next.js App Router pages
│   ├── components/   # React components, WebSocket hooks
│   └── lib/          # Utilities, WebSocket client
├── bridge/           # WhatsApp bridge (TypeScript + Baileys)
├── tests/            # Validation tests for memory, planning, recovery
└── run.py            # Backend entry point
```

---

## Testing
```bash
python test_memory_validation.py
python test_task_planner_validation.py
python test_error_recovery_validation.py
```

---

## Connecting Other Channels

**Telegram:** Create bot via @BotFather → add token to `.env`  
**Discord:** Create app at discord.com/developers → add bot token  
**Slack:** Create app at api.slack.com → add bot + app tokens  
**WhatsApp:** Bridge on port 3001 → scan QR code to connect  

---

## Troubleshooting

**Backend fails to start:**  
Check LLM API key in `.env` → check port 8765 → `docker-compose logs backend`

**Frontend can't connect:**  
Verify backend at `http://localhost:8765/health` → check `NEXT_PUBLIC_API_URL`

**Playwright fails:**  
Run `playwright install chromium --with-deps` → check disk space

**Memory/ChromaDB errors:**  
Check `~/.personal-agent/workspace/` is writable → delete and restart:  
`rm -rf ~/.personal-agent/workspace/chroma`

---

## Future Improvements

- Voice interface via Whisper transcription
- Proactive suggestions based on calendar + email patterns  
- Mobile app (React Native) with push notifications
- Fine-tuned task planning model on user interaction history
- Multi-user team workspace with shared memory

---

## Author

**Midhun M** — AI/ML Engineer  
[GitHub](https://github.com/Midhun-12345678) ·
[LinkedIn](https://linkedin.com/in/midhun-m-d2001) ·
[Portfolio](https://my-portfolio-lilac-gamma.vercel.app/)

---

**Star ⭐ this repo if Nanobot saves you time!**
