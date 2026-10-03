# codex-subagent

Use **OpenAI Codex agents as subagents from Claude Code.**

Claude Code delegates to its own subagents natively. This plugin lets it delegate
to Codex instead — running `codex exec` headless, capturing structured output,
and returning a distilled result without flooding the main context window.

The point is not "another way to run a model." It's that Codex is a *different
model family*, so its conclusions are genuinely independent. When Claude and
Codex agree on a diagnosis, that's corroboration. When they disagree, you've
found the spot worth a human's attention.

## What you get

| Component | What it does |
|---|---|
| `codex-subagent` skill | Teaches Claude when and how to delegate, with safe defaults |
| `codex-delegate` agent | Runs the delegation in an isolated context, returns only the result |
| `codex_run.sh` | Wrapper handling the flags, timeout, and capture that are easy to get wrong |
| `codex_parse.py` | Turns the JSONL event stream into answer + thread id + token spend |
| 5 reference docs | CLI flags, event schema, sandbox model, config, delegation patterns |

## Requirements

- [Claude Code](https://claude.com/claude-code)
- [Codex CLI](https://github.com/openai/codex) on your `PATH`, authenticated
  (`codex login`). Built and verified against **codex-cli 0.147.0**.
- Python 3 (for the event parser)
- macOS or Linux. On Linux, sandboxing needs `bubblewrap` (`bwrap`) installed —
  without it, `read-only` mode is not actually enforced.

Check your setup with `codex doctor`.

## Install

From the KAILASA marketplace (see the [marketplace README](../../README.md)):

```
/plugin marketplace add kailasa-ai/kailasa-marketplace
/plugin install codex-subagent@kailasa
```

Restart Claude Code after installing.

## Using it

Just ask. The skill triggers on natural phrasing:

- "get a second opinion from Codex on this bug"
- "have Codex review the auth changes"
- "delegate this refactor to Codex"
- "ask Codex to audit these three repos in parallel"

Or call the wrapper directly:

```bash
CODEX_SKILL=~/.claude/skills/codex-subagent   # or $CLAUDE_PLUGIN_ROOT

"$CODEX_SKILL/scripts/codex_run.sh" \
  --task "Trace how session tokens are refreshed. Cite file:line." \
  --dir /path/to/repo --mode read
```

It prints `exit_code`, `out_dir`, `thread_id`, and `result_file`.

## Safety model

**This is the part worth reading before you share it with your team.**

Codex reads `sandbox_mode` from `~/.codex/config.toml`. Plenty of people set that
to `danger-full-access` with `approval_policy = "never"` — reasonable when *they*
are at the keyboard watching each command scroll past.

That reasoning does not survive delegation. When Claude launches Codex, nobody is
watching, and headless runs have no approval flow at all — there is no one to
answer a prompt. So the sandbox is the entire safety story.

This plugin therefore **passes the sandbox flag explicitly on every call** rather
than inheriting your config:

| Task | `--mode` | Sandbox |
|---|---|---|
| Research, analysis, review | `read` (default) | `read-only` |
| Editing code in one repo | `write` | `workspace-write` |
| Unrestricted disk/network | `full` | `danger-full-access` |

`full` is never chosen automatically — the skill surfaces the command and asks.

Verified, not assumed: a `read` delegation attempting a write gets
`Operation not permitted` and no file is created.

One sharp edge the skill handles for you: **`codex review` has no `-s` flag** and
silently inherits `config.toml`. On a `danger-full-access` machine, a delegated
review runs completely unsandboxed. The skill always passes
`-c sandbox_mode="read-only"`.

## Optional: fewer permission prompts

Every delegation triggers a Bash permission prompt by default. To pre-approve,
add to `~/.claude/settings.json`:

```json
{
  "permissions": {
    "allow": [
      "Bash(codex exec:*)",
      "Bash(codex review:*)"
    ]
  }
}
```

This is a real loosening — it lets Claude start Codex runs without asking. The
sandbox still constrains what those runs can do. Opt in deliberately.

## Layout

```
plugins/codex-subagent/
├── .claude-plugin/
│   └── plugin.json          # plugin manifest
├── agents/
│   └── codex-delegate.md    # context-isolating wrapper agent
├── skills/codex-subagent/
│   ├── SKILL.md
│   ├── references/          # cli, json-events, sandbox, config, patterns
│   └── scripts/             # codex_run.sh, codex_parse.py
└── README.md
```

## Notes for maintainers

Flags move between Codex versions. `codex help <subcommand>` is the source of
truth for the build you have installed. Three traps documented in
`references/cli-reference.md` that cost real debugging time:

- `codex exec` has **no** `-a/--ask-for-approval` (TUI-only; exit 2 if passed)
- `codex exec resume` rejects `-s`, `-C`, and `--add-dir`
- `codex review` has no `-s`, `-C`, `-o`, or `--json`

Validate changes with `claude plugin validate --strict plugins/codex-subagent`, and bump `version` in `plugin.json` so installed copies update.

## License

MIT — see [LICENSE](LICENSE).
