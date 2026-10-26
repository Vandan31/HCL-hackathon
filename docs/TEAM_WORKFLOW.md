# Team workflow: branches, pushing, and no-clash rules

Vandan (integrator) + 4 teammates, each with their own AI agent. Everyone works on **their own branch and their own
folder**, so two people never edit the same file. Then `main` only ever receives clean merges.

---

## 1. Who owns what (fill this in once the components are decided)

| Teammate | GitHub username | Component | Branch | Folder they own |
|----------|-----------------|-----------|--------|-----------------|
| Vandan (integrator) | Vandan31 | Planning, integration, GPU jobs | `comp/integration` | `docs/`, root config, `requirements.txt` |
| Member 2 | | e.g. Backend / API | `comp/api` | `src/api/`, `tests/api/` |
| Member 3 | | e.g. AI / model | `comp/model` | `src/model/`, `tests/model/` |
| Member 4 | | e.g. UI | `comp/ui` | `src/ui/`, `tests/ui/` |
| Member 5 | | e.g. Data, tests, pitch | `comp/data` | `data/fixtures/`, `docs/pitch/` |

**Golden rule:** you only edit files inside *your* folder. Need a change somewhere else? Write it
on `docs/BOARD.md` under "Shared-file change notices" and the owner makes it.

**Shared files have one owner, the integrator (Vandan):** `CLAUDE.md`, `AGENTS.md`,
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

Then open Claude Code in the folder and say: **"start session, I own component <name>"**.
The agent reads `CLAUDE.md` and follows these rules. It commits locally; **you push**.

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
4. **The integrator (Vandan) reviews and merges**, one PR at a time. After each merge, everyone
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
