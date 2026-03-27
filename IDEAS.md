# Open Claw Agent — Ideas Brainstorm

## Core Platform
- **Telegram bot** running on home machine 24/7
- **Ollama** (local LLM) as the AI brain
- **Python** (FastAPI) backend

## Demo Mode: Hack The Agent (CTF)
Live prompt injection CTF for the tech talk. Students try to extract hidden flags by tricking the AI via Telegram. Leaderboard projected on screen. Competitive, educational, chaotic.

- Hidden flags at multiple difficulty levels inside a sandboxed environment
- Scoring system + live leaderboard (web page)
- Hint system (costs points)
- Sandboxed execution (allowlisted commands, jailed filesystem)
- No access to personal files — everything runs in a `sandbox/` jail

---

## Utility Mode Ideas (runs 24/7 after the talk)

### 1. GitHub Activity Spy ⭐ (SELECTED)
Monitor GitHub users/repos via Telegram. Get alerts on pushes, new issues, PRs, releases, stars. Summarize activity. Useful for open-source contributors and students following projects.

### 2. Personal Server / Downloader Bot
Send YouTube/torrent links → downloads to home PC. Check download progress from phone. Basically a remote NAS controller.

### 3. Exam / Placement Prep Bot
Daily coding problems from LeetCode/GFG. Reply with code, bot runs it against test cases. Tracks streaks and progress.

### 4. Price Tracker + Deal Hunter
Track Amazon/Flipkart product prices. Alert when price drops below threshold. Also gold/silver/crypto/stocks.

### 5. Remote PC Controller
Screenshot desktop, check processes, start/stop apps, system stats, wake-on-LAN — all from Telegram. Friendly SSH.

### 6. College Notice / Attendance Tracker
Scrape college website for notices, results, exam schedules. Alert on new postings. Track attendance percentage.

### 7. AI Study Group Bot
Add to Telegram group. Answers doubts, explains code, generates flashcards from lecture PDFs. 24/7 TA.

### 8. Personal Knowledge Base / Second Brain
Send articles, notes, PDFs → bot indexes everything. Search later with natural language queries. Private, on-device.
