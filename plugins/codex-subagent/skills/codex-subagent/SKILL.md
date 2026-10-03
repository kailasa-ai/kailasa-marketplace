---
name: codex-subagent
description: Delegate coding, analysis, and review tasks to OpenAI Codex agents from Claude Code by driving the `codex` CLI's headless `codex exec` mode, with sandboxed permissions, structured JSON output, and resumable multi-turn threads. Use this whenever the user wants to "ask Codex", "delegate to Codex", "run this by Codex", "get a second opinion", or have Codex review, investigate, or implement something; whenever they want to cross-check Claude's own work against a different model; whenever they want work fanned out across several repos or worktrees in parallel; or whenever a large mechanical refactor would otherwise burn Claude's context window. Also use when writing scripts or CI that shell out to `codex exec`, or when debugging codex CLI flags, sandbox modes, JSONL event output, or session resume.
---

# Codex as a subagent

This skill lets Claude Code hand work to OpenAI Codex and get a clean result back,
the same way it delegates to its own `Agent` subagents.

The primitive is `codex exec` — Codex's non-interactive mode. It runs headless,
streams structured JSONL events, can be forced to return JSON conforming to a
schema, and can be resumed for multi-turn work. That is exactly the contract a
subagent needs.

## When delegating to Codex is actually worth it

Delegation costs a subprocess, real API spend on the user's OpenAI account, and
wall-clock time. It earns that back when:

- **A second, independent opinion matters.** Codex is a different model family.
  For a subtle bug, a disputed design call, or a security question, disagreement
  between two model families is genuine signal — far more useful than asking
  Claude to double-check its own reasoning, which mostly re-derives it.
- **The task would flood Claude's context.** A mechanical refactor over 200 files
  produces enormous intermediate output. Codex can do that work in its own
  process and hand back a summary.
- **Work can run in parallel.** Several repos, several worktrees, several
  independent investigations — launch them concurrently instead of serially.
- **The user explicitly asked for Codex.** Just do it.

Do **not** delegate small things. A one-file edit, a quick grep, a question Claude
can answer directly — doing those in-process is faster and cheaper. A delegation
that takes 90 seconds to do what Claude could do in one tool call is a loss.

## Use the wrapper script

`scripts/codex_run.sh` is the intended entry point. Prefer it over hand-writing
`codex exec` invocations — it handles four things that are easy to get wrong and
that fail in confusing ways:

- **stdin must be closed.** With a pipe or TTY on stdin, `codex exec` blocks on
  `Reading additional input from stdin...` and the delegation hangs forever.
- **macOS has no `timeout` binary,** so a runaway agent needs a portable
  watchdog. The script polls and kills at `--timeout` (default 900s, exit 124).
- **The sandbox flag must be explicit** (see safety below).
- **The `thread_id` must be captured** or the run cannot be resumed.

```bash
# Locate this skill's own directory. Works whether it was installed as a plugin,
# as a skills-dir plugin, or copied straight into ~/.claude/skills/.
CODEX_SKILL="${CLAUDE_PLUGIN_ROOT:-$HOME/.claude/skills/codex-subagent}"
[ -f "$CODEX_SKILL/skills/codex-subagent/SKILL.md" ] && CODEX_SKILL="$CODEX_SKILL/skills/codex-subagent"
```

Then invoke it:

```bash
# Read-only investigation — the default and the right choice for most delegations
"$CODEX_SKILL/scripts/codex_run.sh" \
  --task "Trace how session tokens are refreshed. Cite file:line for each step." \
  --dir /path/to/repo --mode read

# Let Codex actually change code
"$CODEX_SKILL/scripts/codex_run.sh" \
  --task "Migrate src/api/*.js from callbacks to async/await. Keep tests green." \
  --dir /path/to/repo --mode write --timeout 1800
```

It prints `exit_code`, `out_dir`, `thread_id`, and `result_file`. Read
`result_file` for the answer; pass `out_dir/events.jsonl` to
`scripts/codex_parse.py` for token spend and an item inventory.

Long prompts go in a file and get passed as `--task @/path/to/prompt.md`, which
keeps them off the argv length limit and out of shell-quoting trouble.

## Safety: always set the sandbox explicitly

This matters more than it looks. A user's `~/.codex/config.toml` may set
`sandbox_mode = "danger-full-access"` and `approval_policy = "never"` — a
perfectly reasonable choice for a human driving Codex interactively, who sees
every command. Inherited by a run *Claude* triggers, it means unsandboxed writes
anywhere on disk with nobody watching.

So capability is a per-call decision, never an inherited default:

| Task | `--mode` | Sandbox |
|---|---|---|
| Research, analysis, review, second opinion | `read` | `read-only` |
| Editing code in one repo | `write` | `workspace-write` |
| Editing across repos | `write` + `--add-dir <other>` | `workspace-write` |
| Anything needing unrestricted disk or network | `full` | `danger-full-access` |

**Default to `--mode read`.** Reach for `write` only when the task genuinely is
to change files. Never use `--mode full` on your own initiative — show the user
the exact command and let them decide, because it removes the filesystem and
network boundary entirely.

The sandbox genuinely holds. A `read` delegation attempting a write gets
`operation not permitted` and the file is not created — verified, not assumed.

Note that headless runs have no approval flow: nobody is there to answer a
prompt. The sandbox, not a human in the loop, is what makes the run safe. This
is also why `codex exec` has **no** `-a/--ask-for-approval` flag — passing one is
an argument error (exit 2).

## Keep Codex's output out of the main context

A delegation can produce a lot of intermediate text. Piping it straight into the
main conversation defeats half the purpose of delegating.

Run the delegation inside a Claude subagent so only the distilled result comes
back. If `agents/codex-delegate.md` has been installed to `~/.claude/agents/`,
use `subagent_type: "codex-delegate"`. Otherwise use a `general-purpose` agent
and give it this brief:

> Run the `codex_run.sh` from this skill's `scripts/` directory with
> `--task <task>`, `--dir <dir>`, `--mode read`. When it finishes, read the
> `result_file` it names. Return only Codex's findings plus the reported
> `thread_id` — do not include the raw event stream or your own commentary.

For genuinely parallel work, launch one such subagent per repo in a single
message so they run concurrently.

## Structured output when you need to parse the result

Prose is fine for a human-facing answer. When Claude needs to *act* on the
result — filter findings, count them, route them — force a schema. The final
message is then guaranteed-parseable JSON rather than prose you have to regex:

```bash
cat > /tmp/findings.json <<'EOF'
{
  "type": "object",
  "properties": {
    "risk_level": {"type": "string", "enum": ["low", "medium", "high"]},
    "findings": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "file": {"type": "string"},
          "line": {"type": "integer"},
          "issue": {"type": "string"}
        },
        "required": ["file", "line", "issue"],
        "additionalProperties": false
      }
    }
  },
  "required": ["risk_level", "findings"],
  "additionalProperties": false
}
EOF

"$CODEX_SKILL/scripts/codex_run.sh" --task "Audit src/auth for injection risks." \
  --dir /path/to/repo --mode read --schema /tmp/findings.json
```

The result lands in `out_dir/last.json`. Every property must be listed in
`required` and `additionalProperties` must be `false` — the API rejects looser
schemas.

## Multi-turn: keeping a Codex thread alive

Codex remembers a thread across invocations, so a delegation can be a
conversation rather than a one-shot. Capture the `thread_id` from the first run
and pass it back:

```bash
OUT=$("$CODEX_SKILL/scripts/codex_run.sh" --task "Analyse the caching layer." \
        --dir /repo --mode read)
TID=$(printf '%s' "$OUT" | sed -n 's/^thread_id=//p')

"$CODEX_SKILL/scripts/codex_run.sh" --resume "$TID" \
  --task "Now propose a fix for the invalidation bug you identified." \
  --dir /repo --mode read
```

Two traps: resume needs the *same* flags re-passed (notably
`--skip-git-repo-check`, which the wrapper always sends), and a session started
with `--ephemeral` leaves nothing on disk to resume. The wrapper never passes
`--ephemeral` for this reason. Sessions persist under
`~/.codex/sessions/YYYY/MM/DD/rollout-<timestamp>-<thread_id>.jsonl`.

## Delegated code review

`codex review` is a purpose-built reviewer and generally beats a generic
`codex exec` prompt asking for review. It requires a real git repo:

```bash
cd /path/to/repo
codex review -c sandbox_mode="read-only" --base main      # vs a base branch
codex review -c sandbox_mode="read-only" --uncommitted    # staged + unstaged + untracked
codex review -c sandbox_mode="read-only" --commit <sha>   # one commit
```

**`codex review` has no `-s` flag, so it inherits `sandbox_mode` from
`config.toml`.** On a machine configured with `danger-full-access`, a delegated
review runs completely unsandboxed — verified: the run banner printed
`sandbox: danger-full-access`. A review only needs to read, so always constrain
it with `-c sandbox_mode="read-only"`, which does take effect.

It also has no `-C` (so `cd` first) and no `--json` (so capture stdout directly).

Reviews of large diffs are slow — a single commit touching ~600 lines exceeded
10 minutes at high reasoning effort. Run them in the background rather than
blocking on them.

## Reference material

Read these as needed rather than upfront:

- `references/cli-reference.md` — subcommands and flags, and which flags exist on
  which subcommand (they differ in ways that cause real errors)
- `references/json-events.md` — the verified JSONL event schema and parsing recipes
- `references/sandbox-permissions.md` — sandbox modes, network rules, platform notes
- `references/config-and-agents-md.md` — `config.toml`, `-c` overrides, profiles,
  `AGENTS.md`, and how to make a delegation hermetic
- `references/patterns.md` — worked recipes: parallel fan-out, adversarial
  cross-check, worktree isolation, CI usage

## When something goes wrong

| Symptom | Cause |
|---|---|
| Hangs, stderr says `Reading additional input from stdin` | stdin not closed; use the wrapper or add `< /dev/null` |
| `error: unexpected argument '-a' found` (exit 2) | `-a` is TUI-only; `codex exec` has no approval flag |
| `Not inside a trusted directory and --skip-git-repo-check was not specified` | add `--skip-git-repo-check`, including on `resume` |
| `operation not permitted` on a write | working as intended in `--mode read`; switch to `write` if edits are the point |
| Resume can't find the thread | session was `--ephemeral`, or the id is wrong |
| Exit 127 | `codex` not on PATH |

Verify assumptions against the installed build with `codex help <subcommand>` —
it is the source of truth, and flags move between versions.
