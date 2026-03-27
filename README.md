# OpenClaw GitHub Spy Bot

A Telegram bot that spies on GitHub developers — roast profiles, stalk activity, summarize skills, and monitor repos for real-time alerts. Built as an [OpenClaw](https://docs.openclaw.ai) skill, powered by a local LLM via Ollama.

## What It Does

- **Summarize** — Instant developer profile: languages, project domains, top repos, skill signals
- **Roast** — Savage, data-driven roasts based on actual GitHub stats
- **Stalk** — Surveillance reports with coding hours, active days, event patterns
- **Watch** — Background monitoring with alerts when a user pushes code, opens PRs, releases, etc.
- **Compare** — Side-by-side developer comparison
- **Deny** — Sassy rejection for anything not GitHub-related

All data comes from GitHub's REST API. Scripts use **only Python stdlib** — zero pip dependencies.

## Requirements

- **Python 3.10+**
- **Node.js 22+** (for OpenClaw)
- **Ollama** with a tool-calling model (qwen2.5:3b recommended)
- **OpenClaw** (installed via npm)
- **Telegram Bot Token** (from @BotFather)
- **GitHub PAT** (optional, for 5000 req/hr instead of 60)

## Hardware

Tested on:
- **CPU-only (i5, 16GB RAM):** Works but slow (~4 min/response with qwen2.5:3b)
- **GPU (i5 12th gen + RTX 3050, 4-8GB VRAM):** Fast (~2-5 sec/response)

qwen2.5:3b uses ~2GB VRAM. Any machine with 4GB+ VRAM will run this comfortably. You can bump to qwen2.5:7b (~4.5GB VRAM) for better quality on 8GB cards.

## Setup on a New Machine

### 1. Install Ollama

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull qwen2.5:3b
```

### 2. Install OpenClaw

```bash
npm install -g openclaw
openclaw onboard
```

During onboard, select:
- Gateway: **Local**
- Model provider: **Ollama** (`http://127.0.0.1:11434`)
- Model: **qwen2.5:3b**

### 3. Create a Telegram Bot

1. Open Telegram, search **@BotFather**, send `/newbot`
2. Pick a name and username
3. Copy the token

### 4. Add Telegram Channel

```bash
openclaw channels add --channel telegram --token <YOUR_BOT_TOKEN>
```

Then set the DM policy to open so anyone can message it:

```bash
openclaw config set channels.telegram.dmPolicy open
openclaw config set channels.telegram.allowFrom '["*"]'
```

### 5. (Optional) Set GitHub Token

Without a token you get 60 API requests/hour. With a token: 5000/hr.

Create a PAT at: GitHub > Settings > Developer settings > Personal access tokens > Tokens (classic). **No scopes needed.**

```bash
export GITHUB_TOKEN="ghp_your_token_here"
```

Or add it to your shell profile (`~/.bashrc` or `~/.zshrc`).

### 6. Install the Skill

```bash
git clone git@github.com:RitamDas30/OpenClaw_Bot_Demo.git
mkdir -p ~/.openclaw/workspace/skills/
cp -r OpenClaw_Bot_Demo/github-spy/ ~/.openclaw/workspace/skills/github-spy/
```

### 7. Slim Down the Workspace (Recommended)

OpenClaw loads workspace files into every LLM prompt. For faster responses on smaller models, keep them minimal:

```bash
echo '- **Name:** GitHub Spy
- **Vibe:** Sassy intelligence agent' > ~/.openclaw/workspace/IDENTITY.md

echo 'You are GitHub Spy. You ONLY do GitHub-related tasks. Be short, sassy, and direct. Max 150 words per response.' > ~/.openclaw/workspace/SOUL.md

echo 'User communicates via Telegram. Keep responses short for mobile.' > ~/.openclaw/workspace/USER.md
```

### 8. Set Minimal Tools Profile

```bash
openclaw config set tools.profile minimal
```

### 9. Start the Gateway

```bash
openclaw gateway restart
```

### 10. Test

Open your Telegram bot and send:
- `torvalds` — get a quick summary
- `roast torvalds` — savage profile roast
- `stalk torvalds` — surveillance report
- `watch torvalds/linux` — start background monitoring
- `what's the weather?` — get denied

## Project Structure

```
github-spy/
  SKILL.md              # OpenClaw skill definition (triggers + instructions)
  scripts/
    github_api.py       # Shared API client with 5-min cache + URL parsing
    github_roast.py     # Fetch profile data for roasting
    github_stalk.py     # Fetch activity data for surveillance
    github_summarize.py # Developer skills/project analysis
    github_watch.py     # Watch targets for new events (ETag + state)
docs/
  01-research-and-understanding.md
  02-architecture-and-setup.md
IDEAS.md                # All brainstormed ideas
```

## Architecture

```
[Phone / Telegram]
       |
  Telegram Bot API
       |
  OpenClaw Gateway (port 18789)
       |
  Ollama (local LLM) ←→ SKILL.md (instructions)
       |                      |
  Interprets message    Runs scripts/
       |
  GitHub REST API (api.github.com)
```

## Troubleshooting

**Bot not responding?**
```bash
openclaw channels status        # Check if Telegram is running
openclaw logs --follow --local-time  # Watch live logs
```

**Model too slow?**
- Use a GPU machine, or
- Switch to qwen2.5:1.5b (faster but dumber): `openclaw models set ollama/qwen2.5:1.5b`

**Rate limited?**
- Set `GITHUB_TOKEN` for 5000 req/hr
- Watch polling uses ETags — 304 responses don't count against the limit

## License

MIT
