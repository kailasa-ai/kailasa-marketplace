# Repo docs playbook

Load when creating or editing a repo's AGENTS.md / CLAUDE.md, or writing memory.

## Layout in every repo
```
AGENTS.md          the repo's agent brief, the only copy (Codex reads it; Claude imports it)
CLAUDE.md          a single line: @AGENTS.md (+ Claude-only notes, if any)
<module>/AGENTS.md module rules, only when a module really differs
.claude/rules/     optional path-scoped rules (Claude only, so never put safety-critical rules only here)
docs/              architecture, runbooks, post-mortems: things read on demand
```
Start from `~/.kailasa/standards/templates/repo-AGENTS.md`. Keep the root AGENTS.md under ~150 lines; move route trees, directory maps and incident write-ups to `docs/` and link to them.

## What goes where
| Fact | Home |
|---|---|
| Applies to every repo | `standards/AGENTS.md` (this repo) |
| Integration/prod branch, commands, stack, deploy target of one repo | that repo's `AGENTS.md` |
| Detailed procedure (release, migration) | that repo's `docs/` or a skill |
| A one-off decision or correction from the user | memory (dated, with Why + How to apply) |

## Rules
- One fact, one home: link instead of copying. Two copies drift (that is how soma_v2 and the app ended up with contradictory files).
- Don't repeat the master standard in repo files; only add to it or override it for that repo.
- Delete stale instructions in the same PR that makes them stale.
- Safety rules that matter need a CI gate, not just a hook (hooks don't run in Codex or CI).
