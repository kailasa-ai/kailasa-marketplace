@~/.kailasa/standards/AGENTS.md

## Claude Code specifics (things Codex doesn't have)

- Set `model` explicitly on every Agent/subagent call (tiering per D2).
- Use `EnterWorktree` (or `git worktree add`) before editing (G1).
- Run long commands with `run_in_background` and poll the log; don't block (V7).
- Never SendMessage a running Workflow agent; it spawns a duplicate. Put rulings in the script, stop strays, and resume with `resumeFromRunId`.
- Launching Codex from Claude: `codex exec ... < /dev/null` in the background, with an explicit sandbox mode and an output file (`-o`). Without stdin redirected it hangs. See `playbooks/delegation.md`.
- Hooks are convenience, not enforcement: they don't run in Codex or CI. A rule that matters needs a CI gate.
- Write intermediate results somewhere durable, not only the session scratchpad; it can be wiped on restart.
