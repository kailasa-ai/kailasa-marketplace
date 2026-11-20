# Delegation playbook

Load when you are about to hand work to Codex or a subagent.

## Who does what
| Work | Goes to |
|---|---|
| Lookups, listing, file moves, archiving | Smallest tier (Haiku / Codex low tier) |
| Well-specified implementation, tests, mechanical refactors | Codex mid tier, or Sonnet |
| Hard design, cross-module debugging, final judging, release review | Top tier (Opus / Codex top tier) |
| Orchestration, briefs, diff review, verification, talking to the user | The main session |

Always use the latest model of the chosen tier. List the current models first (Codex: `~/.codex/models_cache.json` or `codex` model list) rather than copying an ID from an old doc.

## Writing a brief
A good brief is the only context the worker gets. Include:
1. Goal, plus what "done" means (the exact checks that must pass).
2. Worktree path and branch (one owner per worktree, D6).
3. Files to read first, and what has already been ruled out.
4. Hard limits: no push / no deploy / no prod access / don't touch X.
5. Where to write the result (a file path), so the result survives restarts.

## Running Codex from a script or from Claude
```bash
codex exec --skip-git-repo-check -s workspace-write -C <worktree> \
  -o <worktree>/.agent/last.md - < brief.md > <worktree>/.agent/log.txt 2>&1 &
```
- Always redirect stdin (`< file` or `< /dev/null`), or Codex hangs.
- Choose the sandbox explicitly: `read-only` for research and review, `workspace-write` for edits, and `danger-full-access` only when the task needs network or SSH (say why).
- Codex's sandbox has no network: use the repo's existing venv (`.venv/bin/python -m pytest`) rather than `uv run` that downloads.
- Continue a thread with `codex exec resume <thread_id>`.

## Reviews (D3, D4)
- A review counts only if it produced output: a thread id plus a list of what was checked. Empty output, a crash or out-of-credits means "review not done"; report it that way.
- Treat agreement between model families as corroboration; disagreement marks what to look at yourself.
- Verify every finding before acting on it; reviewers are confidently wrong sometimes.

## Overrides
The user may say "no Codex until 10 AM" or "build it yourself today". Follow the override until the stated time, then return to the default. If Codex isn't installed or is out of credits, fall back to Claude subagents without asking (D5).
