# Architecture & Setup Guide

## Final Architecture

```
  [Students on Telegram]
         │
    Telegram Bot API
         │
  ┌──────▼──────────────────────────────┐
  │  Open Claw Gateway (port 18789)     │
  │  Running on home machine 24/7       │
  │                                     │
  │  ┌────────────────────────────────┐ │
  │  │  github-spy skill (SKILL.md)  │ │
  │  │                               │ │
  │  │  Scripts (Python, stdlib only):│ │
  │  │  - github_roast.py            │ │
  │  │  - github_stalk.py            │ │
  │  │  - github_watch.py            │ │
  │  └────────────────────────────────┘ │
  │                                     │
  │  LLM (Ollama or OpenAI)             │
  │  - Generates roasts from data       │
  │  - Writes surveillance reports      │
  │  - Interprets user messages         │
  └─────────────────────────────────────┘
         │
    GitHub REST API v3
    (5000 req/hr with token)
```

## Project Structure (Final)

```
demo_open_claw_agent/
├── github-spy/              # The Open Claw skill
│   ├── SKILL.md            # Skill definition (triggers + instructions)
│   ├── scripts/
│   │   ├── github_roast.py  # Fetch profile data for roasting
│   │   ├── github_stalk.py  # Fetch activity data for surveillance
│   │   └── github_watch.py  # Watch targets for new events (ETag + state)
│   └── references/          # (empty, available for future use)
├── docs/                    # Documentation
│   ├── 01-research-and-understanding.md
│   └── 02-architecture-and-setup.md
├── IDEAS.md                 # All brainstormed ideas
└── .gitignore
```

## What Open Claw Handles (we don't build this):
- Telegram/WhatsApp/Discord message routing
- LLM integration (model selection, prompt management)
- Session memory and conversation history
- Gateway service (runs as daemon)
- Cron scheduling (for watches)
- User authentication and allowlists

## What Our Skill Handles:
- GitHub API interaction (3 Python scripts)
- Data formatting for LLM consumption
- Watch state management (ETags, seen event IDs)
- Rate limit awareness

## Setup Steps

### 1. Get a Telegram Bot Token
- Message @BotFather on Telegram
- Send `/newbot`
- Choose a name and username
- Copy the token

### 2. Add Telegram to Open Claw
```bash
openclaw channels add --channel telegram --token <your-bot-token>
```

### 3. Set GitHub Token
```bash
# Create a GitHub PAT (classic) with zero scopes at:
# github.com > Settings > Developer settings > Personal access tokens
export GITHUB_TOKEN="ghp_your_token_here"
# Or add to ~/.openclaw/openclaw.json under env
```

### 4. Install the Skill
Copy the `github-spy/` folder to the Open Claw workspace:
```bash
cp -r github-spy/ ~/.openclaw/workspace/skills/github-spy/
```

### 5. Restart Gateway
```bash
openclaw gateway restart
```

### 6. Test
Send a message to the Telegram bot: "roast torvalds on github"

## Scripts — Zero External Dependencies
All three scripts use ONLY Python stdlib (urllib, json, os, sys, pathlib, datetime). No pip install needed. This was a deliberate choice so the skill works on any machine with Python 3.10+.
