# Sandbox modes and permissions

## Contents
- [The three modes](#the-three-modes)
- [Why explicit beats inherited](#why-explicit-beats-inherited)
- [Approvals do not apply headless](#approvals-do-not-apply-headless)
- [Network access](#network-access)
- [Platform enforcement](#platform-enforcement)
- [Verifying a policy](#verifying-a-policy)

## The three modes

Set with `-s` / `--sandbox` on `codex exec` (or `--mode` on `codex_run.sh`).

| Mode | `--mode` | Permits |
|---|---|---|
| `read-only` | `read` | Inspect files and run read-only commands. No edits. |
| `workspace-write` | `write` | Read anywhere, edit within the workspace, run routine local commands inside that boundary. |
| `danger-full-access` | `full` | No filesystem or network boundary at all. |

`workspace-write` scopes writes to the `-C` directory. Additional writable roots
need `--add-dir <path>`, repeatable.

## Why explicit beats inherited

`sandbox_mode` in `~/.codex/config.toml` sets the default. Users who drive Codex
interactively often set `danger-full-access` with `approval_policy = "never"` —
reasonable, because they watch every command scroll past.

That reasoning does not transfer to a delegated run. When Claude launches Codex,
nobody is watching, and inheriting full access means unsandboxed writes anywhere
on disk. Passing `-s` explicitly on every call makes capability a decision about
*this task* rather than a property of the user's interactive setup.

This is a real difference in kind, not caution theatre: the interactive default
is safe because of the human, and the human is exactly what a delegation removes.

## Approvals do not apply headless

Codex's approval policies (`untrusted`, `on-request`, `never`) decide when the
agent pauses to ask permission. A headless run has nobody to ask — a prompt
would simply hang until the watchdog kills it.

This is why `codex exec` has **no** `-a/--ask-for-approval` flag; passing one is
an argument error. The sandbox, not an approval prompt, is the whole of the
safety story for delegated runs. Choose it accordingly.

`--approve-for-me` exists and routes approvals through automatic review using the
workspace-write sandbox. It is not a substitute for choosing the right sandbox.

## Network access

Under `read-only` and `workspace-write`, network access is not freely available —
it goes through the approval path, which headless means it is effectively
unavailable. Only `danger-full-access` gives unrestricted network.

Practical consequence: **a delegated task that needs to install packages, hit an
API, or fetch a URL will fail under `read` or `write`.** Either avoid such tasks,
pre-install dependencies before delegating, or surface the `full`-access command
to the user and let them approve it.

Separately, `codex exec --search` (top-level `--search`) enables the native web
search tool without per-call approval — a narrower option than opening the whole
network boundary.

## Platform enforcement

| Platform | Mechanism |
|---|---|
| macOS | Built-in Seatbelt |
| Linux / WSL2 | `bubblewrap` (`bwrap`) must be installed |
| Windows | Native Windows Sandbox, or the Linux path under WSL2 |

On Linux without `bwrap`, sandboxing cannot be enforced — check before assuming a
`read` delegation is actually constrained there.

## Verifying a policy

Don't trust the flag, test it. A `read-only` delegation asked to write gets:

```
zsh:2: operation not permitted: blocked.txt
```

and the file is not created. `codex sandbox <command>` runs an arbitrary command
under a policy, which is a quick way to check what a given configuration permits
without spending a model call.
