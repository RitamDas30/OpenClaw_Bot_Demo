# Research & Understanding Log

## What is Open Claw?

**Source**: https://openclaw.ai/ and CLI exploration

Open Claw is an **open-source personal AI assistant** that runs on your machine (Mac, Windows, Linux). It's NOT something we build from scratch — it's a framework/platform we extend with **custom skills**.

### Key Facts:
- Installed via `curl -fsSL https://openclaw.ai/install.sh | bash` or `npm i -g openclaw`
- Version installed: **2026.3.24**
- Config lives at: `~/.openclaw/openclaw.json`
- Skills directory: `~/.openclaw/workspace/` (or within skill folders)
- Connects to **30+ chat platforms**: WhatsApp, Telegram, Discord, Slack, Signal, etc.
- Supports **multiple LLM providers**: OpenAI, Claude, local models
- Has **50+ built-in skills** and a skill marketplace (ClawHub)
- Has a **gateway service** that runs as a daemon on your machine

### What We Already Had Configured:
- WhatsApp channel: enabled with allowlist for +918240563942
- Auth: OpenAI Codex (OAuth) with GPT-5.4 as primary model
- Tools profile: "coding"
- Gateway: running on port 18789, loopback mode

## How Skills Work (from SKILL.md spec)

Skills are **modular packages** that extend Open Claw's capabilities. Structure:

```
skill-name/
├── SKILL.md          # Required: YAML frontmatter + markdown instructions
├── scripts/          # Optional: executable code (Python/Bash)
├── references/       # Optional: docs loaded into context as needed
└── assets/           # Optional: files used in output (templates, etc.)
```

### Skill Creation Process:
1. Understand the skill with concrete examples
2. Plan reusable contents (scripts, references, assets)
3. Initialize with `init_skill.py <name> --path <dir>`
4. Edit SKILL.md + add resources
5. Package with `package_skill.py <path>`
6. Iterate based on usage

### Key Principle:
The SKILL.md `description` field in frontmatter is what triggers the skill. The body is only loaded AFTER triggering. So the description must be comprehensive about WHEN to use the skill.

## Connecting Telegram

Command: `openclaw channels add --channel telegram --token <bot-token>`

We need a Telegram Bot Token from @BotFather first, then add it to Open Claw. The gateway handles all the message routing automatically.

## Architecture Decision: Open Claw vs Custom Bot

### Before (Custom Python Bot):
- We were building everything from scratch: FastAPI, polling, Ollama client, formatters
- ~9 Python files, manual Telegram integration, custom tool loop

### Now (Open Claw + Custom Skill):
- Open Claw handles: chat platform integration, message routing, LLM calls, memory, gateway
- We only build: a custom **GitHub Spy skill** with scripts for GitHub API interaction
- Much less code, more impressive demo ("I just wrote a skill and the AI agent learned it")

### What Changes:
- Delete the custom `bot/` code (it's now redundant)
- Create a skill: `github-spy/SKILL.md` + scripts
- Connect Telegram via `openclaw channels add`
- The demo shows: "Here's how you extend an AI agent with a custom skill"

## Demo Narrative

The tech talk is about **how to use Open Claw to build agents**. The demo flow:
1. Show Open Claw running on the home machine
2. Connect to Telegram live
3. Show the GitHub Spy skill in action (roast, stalk, watch)
4. Optionally: create a new skill LIVE during the talk using Open Claw itself
