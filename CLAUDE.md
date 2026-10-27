# Hackathon Project — Agent Operating Rules

Every AI agent (Claude Code main session, subagents, teammates' Claude/Cursor/Codex sessions) that
reads this file MUST follow it. These rules exist so that:

1. a human can **trust and audit** what the agent did (supervision),
2. every line of code can be **explained and changed live** when a panelist asks,
3. several agents can work **in parallel without clobbering each other**,
4. the work lives in a **GitHub repo** and can be **resumed component by component** in any new session.

> **GPU work (PARAM Siddhi AI):** only the account holder (Vandan, whose machine has the PARAM
> rules in `../CLAUDE.md`) submits GPU jobs. On other teammates' machines, agents must not attempt
> PARAM access; write the training script plus the SLURM job file and hand it to Vandan via the board.

---

## 0. Start-of-session ritual (do this BEFORE writing any code)

1. Read `docs/COMPONENTS.md`: what exists, what's done, what's next.
2. Read `docs/BOARD.md`: who (which agent/person) is working on what **right now**.
3. Run `git status` and `git log --oneline -10` to see the real state of the code.
4. Tell the user in 3–5 lines: current state, which component you propose to work on, and why.
5. **Claim** the component on `docs/BOARD.md` (see §3) before touching its files.

If `docs/COMPONENTS.md` says "no problem statement yet", run the `/hackathon-ai-chief-engineer`
skill on the brief first and fill in `docs/COMPONENTS.md` from its output.

---

## 1. Supervision rules: the agent keeps an eye on itself

**Honesty (non-negotiable).** These come from the hackathon skills pack and judges check them:
- Never claim a test passed, a feature works, or a number was measured unless you ran it in this
  session. Paste the command and the real output.
- Label every claim: **Measured / Sourced / Estimated / Hypothesized** (see
  `.claude/skills/hackathon-ai-chief-engineer/references/scorecard.md`).
- Never invent market data, user quotes, benchmarks, accuracy numbers, pilots or prices.
- Anything faked for the demo is labeled `MOCK` in code (§2) and listed in `docs/COMPONENTS.md`.

**Scope control.**
- Work on **one component at a time**. Don't refactor files owned by another claimed component.
- No new dependency, framework, vector DB, agent framework, or cloud service without a one-line
  justification in `docs/DECISIONS.md`. Prefer the simplest thing that works (rules > ML > LLM).
- Don't delete or overwrite files you haven't read. Don't force-push. Don't rewrite git history.

**Stop and ask the user when:**
- a change touches more than one component, or the API contract between components;
- you're about to add a paid API call, store personal data, or submit a GPU job;
- the same error survives 2 fix attempts (report what you tried; don't flail);
- the request is ambiguous and a wrong guess would cost more than ~15 minutes.

**End-of-task self-check.** Before saying "done", verify each item and report it:
- [ ] Code runs / tests executed (command + result shown), or clearly state "NOT RUN" and why
- [ ] Every new file has a header block; every non-obvious line has a comment (§2)
- [ ] Demo-tunable values are tagged `DEMO-KNOB` and live in the config file
- [ ] `docs/COMPONENTS.md` status + "next step" updated
- [ ] `docs/BOARD.md` claim released, with a handoff note
- [ ] New design choices logged in `docs/DECISIONS.md` (with panel-ready answer)
- [ ] Committed on the component branch with a proper message (§4)

---

## 2. Code commenting standard (for live changes during the presentation)

Panelists will ask "why did you do X?" and "can you change Y right now?". The code must answer
both on its own, so a teammate who didn't write it can explain and edit it in under a minute.

### 2.1 File header (every source file)

```python
"""
COMPONENT : <component name from docs/COMPONENTS.md>
PURPOSE   : <one sentence: what this file does for the user>
INPUTS    : <what comes in: request JSON / file / function args>
OUTPUTS   : <what goes out>
DEPENDS ON: <other components/files this relies on>
PANEL NOTE: <the 1-line answer if a judge asks "why does this exist?">
"""
```
(JS/TS: same fields inside `/** ... */`; HTML: `<!-- ... -->`.)

### 2.2 Inline comments explain WHY, not WHAT
```python
# WHY: rules-first. A regex catches 90% of IDs for free; we only call the LLM when it fails.
match = ID_PATTERN.search(text)
```
Comment every function (one line of purpose plus any non-obvious arg), every branch that handles a
failure, and every magic number. Don't comment trivial lines like `i += 1`.

### 2.3 Searchable tags (use exactly these spellings so `grep` finds them)

| Tag | Meaning | Example |
|-----|---------|---------|
| `DEMO-KNOB:` | Value safe to change live in front of judges | `THRESHOLD = 0.7  # DEMO-KNOB: raise to make AI stricter` |
| `PANEL:` | Likely judge question + short answer | `# PANEL: Why not GPT-4? -> 10x cost, same accuracy on our 50-sample test` |
| `MOCK:` | Faked/stubbed for the demo; must be disclosed | `# MOCK: returns fixture data, real API not integrated` |
| `FALLBACK:` | What happens when AI/API/network fails | `# FALLBACK: model timeout -> show rule-based result + "low confidence"` |
| `TODO(post-hackathon):` | Known gap, honest roadmap item | |

Find them during the presentation:
```bash
grep -rn "DEMO-KNOB:" config/ src/   # everything we can tweak live
grep -rn "PANEL:" src/          # cheat-sheet of judge answers
grep -rn "MOCK:" src/           # honest disclosure list
```

### 2.4 Keep live-change points in one place
All `DEMO-KNOB` values (thresholds, model name, prompt text, timeouts, feature flags, sample data
path) live in the **`config/` folder, one file per component** (`config/retrieval.py`,
`config/answer.py`, `config/ui.js`, ...). That's one place to look during the demo, and no two
people ever edit the same config file. Code imports from there; never hard-code a knob in `src/`.

---

## 3. Multi-agent coordination protocol

Agents coordinate **through files in the repo**, not through memory. Assume another agent may be
working at the same moment.

### 3.0 The board lives on `main` (otherwise nobody sees your claim)
`docs/BOARD.md` and `docs/COMPONENTS.md` are edited **on `main` and pushed right away by the
human**, never only on a component branch. Every claim, release or status update is a tiny
doc-only commit. The agent prepares it, the human pushes:
```bash
git switch main && git pull --rebase
# agent edits docs/BOARD.md (and/or docs/COMPONENTS.md) and commits locally
git commit -am "board: <name> claims <component>"
# HUMAN runs: git push
git switch comp/<component>      # back to code work
```
If the push is rejected, `git pull --rebase` and check that nobody claimed the same component
meanwhile. Always pull `main` before reading the board. Full team procedure: `docs/TEAM_WORKFLOW.md`.

### 3.1 Claim → work → release (on `docs/BOARD.md`)
1. **Claim:** add a row under "Active claims": `component | agent/person | branch | started | files`.
   If the component is already claimed by someone else, **don't touch it**. Pick another or ask.
2. **Work** only inside that component's folder plus its own tests. If you must change a shared
   file (config, API contract, requirements), say so on the board first and keep the change minimal.
3. **Release:** delete your claim row and append a **handoff note** to the log:
   what changed, how to run it, what's broken, the next step.

### 3.2 Interfaces are contracts
- Components talk only through the contracts written in `docs/COMPONENTS.md` ("Interfaces"
  section): API routes, function signatures, JSON shapes.
- Changing a contract = stop-and-ask (§1) + update the doc in the same commit.
- Build against a `MOCK:` of a missing component instead of waiting for it.

### 3.3 Mixed tools (Claude Code + Antigravity + others)
- Claude Code reads `CLAUDE.md`; Antigravity auto-loads `AGENTS.md`, which includes this file.
  Same rules for both. Skills are shared via `.agents/skills.json` → `.claude/skills/`.
- Tools never talk to each other directly. They coordinate **only** via `docs/BOARD.md`, git
  branches and handoff notes. Sign claims as `<name>/claude` or `<name>/antigravity`.
- **One agent per working folder.** Two agents (even of different tools) must never edit the same
  checkout at the same time: they'd overwrite each other and share one branch. If one person runs
  both tools, give the second agent its own git worktree (see `docs/TEAM_WORKFLOW.md` §2b).
- Before editing, re-read any file another tool may have changed (`git pull`, `git status`).
  Never assume your memory of a file is current.

### 3.4 Subagents
- When the main session spawns subagents, give each **one component** and its claimed files,
  and tell it to read this CLAUDE.md. Two subagents never edit the same file.
- Subagents report back: files changed, commands run plus real output, open issues.
  The main session updates `docs/BOARD.md` and `docs/COMPONENTS.md`.

---

## 4. GitHub repo rules

- **Branches:** `main` stays demo-ready at all times. Work happens on `comp/<component-name>`
  (e.g. `comp/api`, `comp/ui`, `comp/model`). Fixes: `fix/<short-desc>`.
- **Humans push, agents don't.** Agents may stage and commit locally; `git push`, merging PRs,
  and anything touching the remote are done by the teammate themselves.
- **No AI attribution.** Never add `Co-Authored-By: Claude`, "Generated with Claude Code" or any
  AI trailer/footer to commits or PR descriptions. Commits are authored by the teammate only.
- **Commits:** small, one logical change each. Format:
  `<component>: <what changed>`, e.g. `api: add /checkin endpoint with duplicate guard`.
- **Merge to main** only when the component's tests pass and the demo still runs. Prefer a PR
  (`gh pr create`) so teammates see the diff; use the PR body as the handoff note.
- **Never commit:** `.env`, API keys, passwords, PARAM/VPN credentials, personal data, large
  datasets/model weights (use `.gitignore`; keep the fixtures small).
- Pull before starting (`git pull --rebase` on your branch) to pick up other agents' work.
- Shared files (`CLAUDE.md`, `docs/COMPONENTS.md` interfaces, root config, `requirements.txt`)
  are changed only by the integrator; others request changes on the board (see `docs/TEAM_WORKFLOW.md`).
- Tag demo-ready snapshots: `git tag demo-v1` (a safe rollback point if something breaks live).

---

## 5. Component-wise progress (how to resume any time)

`docs/COMPONENTS.md` is the **single source of truth** for progress. Each component has a status:
`TODO → IN PROGRESS → WORKING (tested) → DEMO-READY`, plus a "next step" line written so a
brand-new session with zero context can continue.

To continue the hackathon in a fresh session, the user can just say
**"continue component <name>"** and the agent follows §0.

---

## 6. Hackathon method (skills available in `.claude/skills/`)

| When | Skill |
|------|-------|
| New brief, end-to-end plan | `/hackathon-ai-chief-engineer` |
| Pick/validate the problem | `/market-opportunity-scout` |
| Personas, UX, accessibility | `/user-value-mapper` |
| Architecture, cost, eval | `/lean-ai-solution-architect` (cost script: `scripts/estimate_cost.py`) |
| Build plan, repo tree, tests | `/mvp-implementation-planner` |
| Pitch, judge Q&A | `/pitch-evaluation-coach` |

Default stack unless the team decides otherwise (log it in DECISIONS): single FastAPI/Flask
service + SQLite + simple HTML/Streamlit UI + pytest. Every demo needs a **working offline/mock
fallback** in case Wi-Fi or the model API fails on stage.

---

## 7. Repo layout (target)

```
CLAUDE.md            ← this file (rules for all agents)
AGENTS.md            ← pointer for non-Claude agents
docs/
  COMPONENTS.md      ← component registry, status, interfaces, next steps
  BOARD.md           ← live claims + handoff log
  DECISIONS.md       ← design decisions + panel-ready answers
src/                 ← code, one folder per component
tests/               ← tests mirror src/
data/fixtures/       ← small, license-safe demo data
.claude/skills/      ← hackathon skills pack
```
