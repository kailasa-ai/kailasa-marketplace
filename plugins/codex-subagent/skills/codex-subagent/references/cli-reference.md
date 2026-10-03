# Codex CLI reference (for delegation)

Verified against **codex-cli 0.147.0** on macOS (darwin 25.6.0). Flags move
between versions — `codex help <subcommand>` is the source of truth. Note that
`codex <sub> --help` fails with `stdin is not a terminal` in a non-TTY shell;
use `codex help <sub>` instead, which works everywhere.

## Contents
- [Subcommands](#subcommands)
- [`codex exec` — the delegation primitive](#codex-exec--the-delegation-primitive)
- [`codex exec resume`](#codex-exec-resume)
- [`codex review`](#codex-review)
- [Flags that do NOT exist where you expect](#flags-that-do-not-exist-where-you-expect)
- [Exit codes](#exit-codes)
- [Other subcommands](#other-subcommands)

## Subcommands

| Command | Purpose |
|---|---|
| `exec` (alias `e`) | Run Codex non-interactively. **The one that matters for delegation.** |
| `review` | Run a code review non-interactively |
| `resume` / `fork` | Resume or fork a previous *interactive* session |
| `mcp` | Manage external MCP servers for Codex |
| `mcp-server` | Start Codex itself as an MCP server (stdio) |
| `app-server` | [experimental] App server + protocol tooling |
| `exec-server` | [experimental] Standalone exec-server service |
| `sandbox` | Run an arbitrary command inside Codex's sandbox |
| `apply` | `git apply` the latest diff from a Codex cloud task |
| `cloud` | [experimental] Browse Codex Cloud tasks |
| `plugin`, `features`, `debug`, `doctor` | Plugin/feature-flag/diagnostic tooling |
| `login` / `logout` | Credentials |

## `codex exec` — the delegation primitive

```
codex exec [OPTIONS] [PROMPT]
codex exec [OPTIONS] <resume|review> [ARGS]
```

The prompt comes from the argument, or from stdin if omitted or given as `-`.
If stdin is piped *and* a prompt argument is given, stdin is appended as a
`<stdin>` block.

**This is the stdin trap:** if stdin is neither closed nor a terminal, `codex
exec` prints `Reading additional input from stdin...` and waits. Always redirect
`< /dev/null` when the prompt is an argument.

### Output control
| Flag | Effect |
|---|---|
| `--json` | Stream JSONL events to stdout (see `json-events.md`) |
| `-o, --output-last-message <FILE>` | Write the final agent message to a file |
| `--output-schema <FILE>` | Force the final message to conform to a JSON Schema |
| `--color <always\|never\|auto>` | Colour handling |

`--json` and `--output-schema` compose: the schema-conforming JSON appears both
in `-o` output and as the last `agent_message` item's `.text`.

### Permissions
| Flag | Effect |
|---|---|
| `-s, --sandbox <read-only\|workspace-write\|danger-full-access>` | Sandbox policy |
| `--add-dir <DIR>` | Extra writable dir alongside the workspace |
| `--approve-for-me` | Route approvals through automatic review (workspace-write) |
| `--dangerously-bypass-approvals-and-sandbox` | No sandbox, no prompts |
| `--dangerously-bypass-hook-trust` | Run hooks without persisted trust |

### Scope and environment
| Flag | Effect |
|---|---|
| `-C, --cd <DIR>` | Working root for the agent |
| `--skip-git-repo-check` | Allow running outside a git repo |
| `--ephemeral` | Don't persist session files — **breaks `resume`** |
| `--ignore-user-config` | Ignore `$CODEX_HOME/config.toml` (auth still uses `CODEX_HOME`) |
| `--ignore-rules` | Ignore user/project execpolicy `.rules` files |
| `--strict-config` | Error on unrecognised config keys |

### Model
| Flag | Effect |
|---|---|
| `-m, --model <MODEL>` | Model override |
| `-p, --profile <NAME>` | Layer `$CODEX_HOME/<name>.config.toml` over base config |
| `-c, --config <key=value>` | Override any config key; value parsed as TOML |
| `--enable/--disable <FEATURE>` | Shorthand for `-c features.<name>=true/false` |
| `--oss`, `--local-provider <lmstudio\|ollama>` | Use a local provider |
| `-i, --image <FILE>...` | Attach images to the prompt |

`-c` values are TOML, so strings need quotes: `-c model_reasoning_effort="high"`.

## `codex exec resume`

```
codex exec resume [OPTIONS] [SESSION_ID] [PROMPT]
```

`SESSION_ID` is the `thread_id` from `thread.started`, or a thread name.
`--last` picks the newest recorded session; `--all` disables cwd filtering.

Resume accepts most `exec` flags, but **not** `-s/--sandbox` or `-C/--cd` — it
inherits the original session's working root. It **does** still require
`--skip-git-repo-check` if the original run needed it; omitting it fails with
`Not inside a trusted directory and --skip-git-repo-check was not specified.`

Sessions live at `~/.codex/sessions/YYYY/MM/DD/rollout-<ts>-<thread_id>.jsonl`.

## `codex review`

```
codex review [OPTIONS] [PROMPT]
```

| Flag | Effect |
|---|---|
| `--base <BRANCH>` | Review changes against a base branch |
| `--uncommitted` | Review staged, unstaged, and untracked changes |
| `--commit <SHA>` | Review one commit |
| `--title <TITLE>` | Commit title for the summary |

Requires a real git repo. Has **no** `-C`, **no** `--json`, **no** `-o` — `cd`
into the repo and capture stdout.

Critically, it also has **no `-s`**, so the sandbox comes from `config.toml`.
Verified: with `sandbox_mode = "danger-full-access"` set, the review banner
reports `sandbox: danger-full-access`. Constrain it explicitly:

```bash
codex review -c sandbox_mode="read-only" --base main
```

That override is honoured — the banner then reports `sandbox: read-only`.

## Flags that do NOT exist where you expect

These cause real, confusing failures:

- **`-a` / `--ask-for-approval` is not valid on `codex exec`.** It exists only on
  the top-level (TUI) command. Passing it gives
  `error: unexpected argument '-a' found` and exit 2. Headless runs have no
  approval flow at all — the sandbox is the control.
- **`-s` / `--sandbox` is not valid on `codex exec resume`.** The resumed session
  keeps its original policy.
- **`--json` is not valid on `codex review`.**
- **`-C` is not valid on `codex review`.**
- **`-s` is not valid on `codex review`** — it inherits `config.toml`. Use
  `-c sandbox_mode="read-only"`.

## Exit codes

| Code | Meaning |
|---|---|
| 0 | Success |
| 1 | Runtime error (bad session id, untrusted directory, auth failure) |
| 2 | Argument parsing error |
| 124 | Timeout — imposed by `codex_run.sh`, not by codex itself |
| 127 | `codex` not found on PATH |

## Other subcommands

- `codex mcp-server` — runs Codex as an MCP server over stdio. An alternative
  integration route: register it in Claude Code's MCP config and Codex becomes a
  native tool. Trades per-call flag control for a cleaner call surface.
- `codex sandbox [COMMAND]...` — runs an arbitrary command under Codex's sandbox.
  Useful for testing what a given policy actually permits.
- `codex doctor` — diagnoses install, config, auth, and runtime health. First
  thing to run when delegations fail for no obvious reason.
- `codex debug models` — dumps the raw model catalog as JSON; the reliable way to
  find valid `-m` values for the installed build.
