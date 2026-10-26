# AGENTS.md

All AI coding agents (Claude Code, Cursor, Codex, Copilot, etc.) working in this repo must follow
**[CLAUDE.md](CLAUDE.md)**. It covers the session start ritual, code commenting standard, multi-agent
claim/release protocol, git rules and component tracking.

Minimum before editing anything:
1. Read `docs/COMPONENTS.md` and `docs/BOARD.md`.
2. Claim your component on `docs/BOARD.md`; don't edit components claimed by others.
3. Comment code using the CLAUDE.md §2 tags (`DEMO-KNOB:`, `PANEL:`, `MOCK:`, `FALLBACK:`).
4. When done: update `docs/COMPONENTS.md`, release your claim with a handoff note, commit on `comp/<name>`.
