# Git playbook

Load when branching, committing, opening PRs or promoting.

## Branch model (G0)
- `dev`: integration. Every feature PR targets it.
- `main`: production. It changes only through a `dev → main` promotion PR.
- Branch names: `feat/<short>`, `fix/<short>`, `chore/<short>`, `refactor/<short>` (a ticket ID may go in the name: `fix/JF-512-account-switch`).

## Start work
```bash
git fetch origin
git worktree add -b feat/<name> ../<repo>-<name> origin/dev
```
Never edit in the main checkout. Never `git stash` (stashes are shared across worktrees).

## Commit
```
fix(chat): keep the draft when switching accounts

<why, in one or two lines if not obvious>

Co-Authored-By: <model that wrote it> <noreply@…>
```
Conventional Commit types: feat, fix, chore, refactor, docs, test, perf, ci. Scope = the area of the app.

## Open the PR
1. `git status` and `git diff --stat`, then re-read the full diff yourself.
2. Rebase on `origin/dev` (`git rebase origin/dev`; push with `--force-with-lease` on your own branch only).
3. Push the branch and open the PR to `dev`. The PR body has: what changed, how it was verified (commands + results), what was NOT verified, and the "Generated with …" footer.
4. Do not merge without the user's go-ahead. Merges are **squash**, titled `<conventional subject> (#PR)`.

## Promote dev → main
1. `git fetch && git log --oneline origin/main..origin/dev`. If there are commits you don't recognise, stop and ask.
2. Full test suite (V3) + independent cross-family review (D3).
3. Open the promotion PR; merge only with a yes; deploy per `deploy-and-prod.md`.

## Never
`--no-verify`; plain `--force`; pushing to `dev`/`main`; rewriting someone else's branch; committing `.env*`, keys or build artifacts.
