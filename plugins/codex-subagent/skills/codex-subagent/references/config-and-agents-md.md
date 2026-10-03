# Config, profiles, and AGENTS.md

## Contents
- [Where config lives](#where-config-lives)
- [Per-call overrides with `-c`](#per-call-overrides-with--c)
- [Profiles](#profiles)
- [AGENTS.md](#agentsmd)
- [Rules and execpolicy](#rules-and-execpolicy)
- [Making a delegation hermetic](#making-a-delegation-hermetic)

## Where config lives

`$CODEX_HOME/config.toml`, defaulting to `~/.codex/config.toml`. Setting
`CODEX_HOME` relocates the whole Codex state directory — config, auth, sessions.

Commonly relevant keys:

```toml
model = "gpt-5.6-sol"
model_reasoning_effort = "xhigh"
approval_policy = "never"
sandbox_mode = "danger-full-access"
notify = ["/path/to/hook", "turn-ended"]

[features]
memories = true
```

Two of these are worth checking before delegating, because they change what a
delegated run does:

- **`sandbox_mode`** — may be `danger-full-access`. Always override with `-s`.
- **`notify`** — fires an external hook on turn end. A delegation will trigger the
  user's desktop notifications unless suppressed.

## Per-call overrides with `-c`

`-c key=value` overrides any config key, including nested ones via dotted paths.
The value is parsed as **TOML**, so strings need quotes:

```bash
-c model_reasoning_effort="high"        # string — quotes required
-c features.memories=false              # bool — no quotes
-c 'sandbox_permissions=["disk-full-read-access"]'   # array
```

If the value fails to parse as TOML it is used as a literal string, which hides
typos — `-c model_reasoning_effort=high` silently becomes the string `high`
rather than erroring. Quote deliberately.

`--enable <F>` / `--disable <F>` are shorthand for `-c features.<F>=true|false`.

## Profiles

`-p <name>` layers `$CODEX_HOME/<name>.config.toml` on top of the base config.
Useful for a dedicated delegation profile — a pinned model, reasoning effort, and
disabled notifications — without touching the user's interactive defaults.

## AGENTS.md

Codex's equivalent of `CLAUDE.md`. A delegated run **picks up `AGENTS.md` from
the target repo**, so the instructions Codex receives are the task prompt *plus*
whatever that repo already tells Codex to do.

This cuts both ways. It is usually desirable — the repo's conventions get
respected for free. But it means a delegation is not fully described by its
prompt, and a surprising result may be coming from a repo-level `AGENTS.md`
rather than from the prompt. When a delegation behaves oddly, check for one.

`~/.codex/AGENTS.md` provides global instructions across all repos.

## Rules and execpolicy

`.rules` files (user and project level) define execpolicy — which commands Codex
may run without escalation. `--ignore-rules` skips them, which is appropriate for
automation that has already vetted what it is asking for, and inappropriate when
the rules are the safety mechanism.

## Making a delegation hermetic

For a reproducible run that ignores the user's environment entirely:

```bash
codex exec --ignore-user-config --ignore-rules --strict-config \
  -m gpt-5.6-sol -s read-only -C /repo --skip-git-repo-check \
  -o out.md "<task>" < /dev/null
```

The tradeoff is real: `--ignore-user-config` drops the user's model choice,
plugins, memories, and notify hooks. Every setting that matters must then be
re-specified. Auth still resolves through `CODEX_HOME`, so this does not break
authentication.

Use it for CI and reproducible benchmarks. For everyday delegation, overriding
just `-s` and `-m` is usually the better balance — the user's plugins and
conventions are typically an asset, not contamination.
