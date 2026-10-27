# Team workflow: branches, pushing, and no-clash rules

A team of 4 (Harsh as integrator, Jaya, Vandan, Vaidehi), each with their own AI agent. Everyone works on
**their own branch and their own folder**, so two people never edit the same file. Then `main`
only ever receives clean merges. Full plan and timeline: `docs/PLAN.md`.

---

## 1. Who owns what (Case 1: Multilingual Citizen Services Assistant)

| Person | GitHub username | Component | Branch | Folders they own |
|--------|-----------------|-----------|--------|------------------|
| A. Harsh (integrator) | | API + answer engine (LLM, citations, refusal); merges all PRs | `comp/api` | `src/api/`, `src/answer/`, `config/answer.py`, `docs/`, root files |
| B. Jaya | | Data + ingestion | `comp/data` | `data/schemes/`, `src/ingest/`, `config/ingest.py` |
| C. Vandan | Vandan31 | Language detection + retrieval + eval; PARAM GPU jobs; repo owner | `comp/retrieval` | `src/lang/`, `src/retrieval/`, `scripts/eval.py`, `data/eval/`, `config/lang.py`, `config/retrieval.py` |
| D. Vaidehi | | UI + voice + eligibility + pitch | `comp/ui` | `src/ui/`, `src/eligibility/`, `config/ui.js`, `config/eligibility.py`, `docs/pitch/` |

Tests live next to the owner: `tests/<component>/`.

**Golden rule:** you only edit files inside *your* folder. Need a change somewhere else? Write it
on `docs/BOARD.md` under "Shared-file change notices" and the owner makes it.

**Shared files have one owner, the integrator (Harsh):** `CLAUDE.md`, `AGENTS.md`,
`docs/COMPONENTS.md` (interfaces section), root config file, `requirements.txt` / `package.json`.

---

## 2. One-time setup (each teammate)

```bash
git clone https://github.com/Vandan31/HCL-hackathon.git
cd HCL-hackathon
git config user.name  "<Your Name>"
git config user.email "<your-github-email>"

# create YOUR branch from the latest main
git switch -c comp/<your-component>
git push -u origin comp/<your-component>
```

Then open Claude Code **or** Antigravity in the folder and say:
**"start session, I own component <name>"**. Claude Code reads `CLAUDE.md`; Antigravity reads
`AGENTS.md` (which includes CLAUDE.md). Both follow these rules, commit locally, and **you push**.

### 2b. Running Claude Code AND Antigravity on the same laptop

Never point both agents at the same folder. Give the second one its own worktree (a second
folder on its own branch, sharing the same git history):

```bash
# from the main repo folder; example: Claude does the API, Antigravity tests the UI
git worktree add ../HCL-hackathon-ui comp/ui          # existing branch
# or for a new branch:  git worktree add -b comp/ui ../HCL-hackathon-ui origin/main
```
Open Claude Code in `HCL-hackathon/` and Antigravity in `HCL-hackathon-ui/`. Each folder gets
its own board claim. Remove it when done: `git worktree remove ../HCL-hackathon-ui`.

---

## 3. Daily loop (no-clash routine)

```bash
# 1) Start of work: get everyone's latest merged code into your branch
git switch comp/<your-component>
git fetch origin
git rebase origin/main          # replays your commits on top of latest main

# 2) Work (you + your agent), commit small and often
git add src/<your-folder>/ tests/<your-folder>/
git commit -m "<component>: <what changed>"

# 3) Push YOUR branch (never main)
git push                        # after a rebase use: git push --force-with-lease
```

- `--force-with-lease` is safe **only on your own branch**. Never force-push `main`.
- Use `git add <your-folder>` instead of `git add -A` so you never commit someone else's files by accident.
- Rebase at least **twice a day** and **always before opening a PR**. Small, frequent syncs = tiny conflicts.

---

## 4. Getting your work into `main` (Pull Request)

1. Make sure it runs and your tests pass on your branch.
2. `git fetch origin && git rebase origin/main`, then re-run the tests, then `git push --force-with-lease`.
3. Open a PR: `gh pr create --base main --head comp/<your-component>` (or on the GitHub website).
   PR description = handoff note (what changed, how to run it, what was tested, known issues).
4. **The integrator (Harsh) reviews and merges**, one PR at a time. After each merge, everyone
   runs step 1 of the daily loop again.
5. Merge with **"Squash and merge"** so `main` keeps one clean commit per feature.

**Merge order** when several PRs are ready: data/fixtures → model → API → UI → docs/pitch.
That way each component merges after the ones it depends on.

---

## 5. Claiming work on the board (so agents don't collide)

`docs/BOARD.md` lives on `main`. Claims are tiny doc-only commits pushed straight to `main`:

```bash
git switch main && git pull --rebase
# edit docs/BOARD.md: add your row under "Active claims"
git commit -am "board: <name> claims <component>"
git push                       # if rejected: git pull --rebase, check nobody else claimed it, push again
git switch comp/<your-component>
```

This is the **only** reason anyone other than the integrator pushes to `main`.
Board edits are one row per person, so a rebase conflict here is trivial to resolve
(keep both rows).

---

## 6. If a conflict happens anyway

```bash
git rebase origin/main         # stops at the conflicting file
git status                     # shows which files conflict
# open the file, keep the right parts, delete the <<<<<<< ======= >>>>>>> markers
git add <file>
git rebase --continue
# give up and go back to how it was before:  git rebase --abort
```
If the conflict is in a file you don't own, **don't resolve it alone**. Ping the owner.

---

## 7. Before the demo

```bash
git switch main && git pull
git tag demo-v1 && git push origin demo-v1     # integrator only: frozen snapshot to fall back to
```
After the code freeze, only the integrator merges, and only fixes.

---

## 8. Recommended GitHub settings (integrator, one time)

Repo → **Settings → Branches → Add rule for `main`**:
- ✅ Require a pull request before merging
- ✅ Require linear history

With this, nobody can accidentally push code straight to `main`. If you enable it, board claims
also go through a quick PR, or keep the board unprotected by leaving this off during the hackathon.
