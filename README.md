# KAILASA Marketplace

KAILASA's private marketplace of skills, plugins, agents, commands, hooks and MCP servers. One repo works in both **Claude Code** and **Codex**.

The marketplace is called **`kailasa`**. Plugins install as `<plugin>@kailasa` in both tools.

## Install

You need read access to `kailasa-ai/kailasa-marketplace` on GitHub. Both tools clone the repo with your normal git credentials, so `gh auth login` is enough.

### Claude Code

```bash
# inside Claude Code
/plugin marketplace add kailasa-ai/kailasa-marketplace
/plugin install codex-subagent@kailasa

# or from a shell
claude plugin marketplace add kailasa-ai/kailasa-marketplace
claude plugin install codex-subagent@kailasa
```

- **Browse:** `/plugin` → **Discover**.
- **Update:** `/plugin marketplace update kailasa`, or turn on auto-update for `kailasa` in `/plugin` → **Marketplaces**.
- **Background updates:** Claude Code updates marketplaces in the background at startup, which can't prompt for credentials. Set `GITHUB_TOKEN` in your shell profile so it can read the private repo.

### Codex (CLI and app)

```bash
codex plugin marketplace add kailasa-ai/kailasa-marketplace
codex plugin add codex-subagent@kailasa
```

- **Browse:** `/plugins` in the TUI, or `codex plugin list --marketplace kailasa`.
- **Update:** `codex plugin marketplace upgrade kailasa`.
- **Codex agents:** these can't be installed through plugins. See [Codex agents](#codex-agents).
- **Workspace admins:** you can import this repo once for everyone under **ChatGPT Admin → Plugins → Import marketplace**, which re-syncs it daily.

### Other agents (skills only)

Cursor, Copilot, OpenCode and similar agents can install just the skills:

```bash
npx skills add kailasa-ai/kailasa-marketplace
```

### Auto-register in a project (Claude Code)

Commit this to a project's `.claude/settings.json`. Anyone who trusts the folder is then prompted to add the marketplace and install the plugins listed:

```json
{
  "extraKnownMarketplaces": {
    "kailasa": {
      "source": { "source": "github", "repo": "kailasa-ai/kailasa-marketplace" },
      "autoUpdate": true
    }
  },
  "enabledPlugins": {
    "codex-subagent@kailasa": true
  }
}
```

## Catalog

| Plugin | What it does | Claude Code | Codex |
|---|---|---|---|
| [`codex-subagent`](plugins/codex-subagent) | Delegate tasks from Claude Code to OpenAI Codex agents (headless `codex exec`, sandboxing, resumable threads) | skill + agent | skill only. It's built for driving Codex *from Claude*, but Codex can still use it to start separate sandboxed runs. |

## How one repo serves both tools

There is one catalog, `.claude-plugin/marketplace.json`. Claude Code reads it natively. Codex also reads it, falling back to this file when there's no `.agents/plugins/marketplace.json`, so there is nothing to keep in sync.

Each part of a plugin works in each tool as follows:

| Plugin part | Claude Code | Codex |
|---|---|---|
| `.claude-plugin/plugin.json` | ✅ | ✅ |
| `skills/<name>/SKILL.md` | ✅ | ✅ Same open Agent Skills format. Invoke with `$name`. |
| `skills/<name>/agents/openai.yaml` | ignored | ✅ Optional Codex display name, icon and invocation policy |
| `.mcp.json` | ✅ | ✅ |
| `hooks/hooks.json` | ✅ | ✅ The user must trust each hook in `/hooks`, and tool matchers differ between tools, so test in both. |
| `commands/*.md` | ✅ | ⚠️ Converted to skills, but only if the command has a `description` and doesn't use `$ARGUMENTS`, `$1`, `!` shell or `@file`. |
| `agents/*.md` | ✅ | ❌ Use `codex-agents/*.toml` instead. |
| `codex-agents/*.toml` | ignored | ✅ Installed with `scripts/install-codex-agents.sh` |

**Rules that keep both tools working:**

- **Plugins live in this repo.** Each catalog entry's `source` must be a `./plugins/<name>` path. Codex skips entries that point at another GitHub repo.
- **Prefer skills over commands.** A skill behaves the same in both tools.
- **Use `${CLAUDE_PLUGIN_ROOT}` to reference a plugin's own files.** Codex sets it too.

## Layout

```
kailasa-marketplace/
├── .claude-plugin/marketplace.json   # the catalog: every plugin is listed here
├── plugins/<name>/                   # one folder per plugin
│   ├── .claude-plugin/plugin.json
│   ├── skills/<name>/SKILL.md        # skills (both tools)
│   ├── agents/*.md                   # Claude Code subagents (optional)
│   ├── codex-agents/*.toml           # Codex custom agents (optional)
│   ├── commands/*.md                 # slash commands (optional)
│   ├── hooks/hooks.json              # hooks (optional)
│   └── .mcp.json                     # MCP servers (optional)
├── templates/skill-plugin/           # used by scripts/new-plugin.sh
└── scripts/
    ├── new-plugin.sh                 # create a plugin and add it to the catalog
    └── install-codex-agents.sh       # copy codex-agents/*.toml into ~/.codex/agents
```

## Adding something

**Convention: one plugin per skill.** The plugin and its skill share a name, so people install only what they need.

### A new skill

```bash
# start from scratch
scripts/new-plugin.sh hourly-updates "Formats hourly work updates and EOD reports"

# or import an existing skill folder (it must contain SKILL.md)
scripts/new-plugin.sh npedia-fetch "Fetch and search nithyanandapedia.org" \
  --from ~/.claude/skills/npedia-fetch --category research
```

The script creates `plugins/<name>/` and adds the plugin to the catalog. Next:

1. Edit `SKILL.md`. Write the frontmatter `description` carefully: both tools use it to decide when to load the skill.
2. Run the validator.
3. Open a PR.

### Agents

- **Claude Code subagent:** `plugins/<name>/agents/<agent>.md`, with `name`, `description` and optional `tools` / `model` frontmatter.
- **Codex agent:** `plugins/<name>/codex-agents/<agent>.toml`, as shown below.

```toml
name = "reviewer"
description = "Reviews diffs for correctness bugs."
developer_instructions = """
You review code changes and report only real bugs...
"""
sandbox_mode = "read-only"     # optional: any config.toml key (model, model_reasoning_effort, ...) works here
```

### Commands, hooks and MCP servers

Put them inside the plugin they belong to, following the layout above.

### Releasing changes

Bump `version` in the plugin's `plugin.json` whenever you change it. Both tools cache installs by version.

## Codex agents

Codex loads agents only from `~/.codex/agents/` or a repo's `.codex/agents/`. To install the agents this repo ships, use a clone:

```bash
git clone https://github.com/kailasa-ai/kailasa-marketplace && cd kailasa-marketplace
scripts/install-codex-agents.sh                       # every plugin's agents, into ~/.codex/agents
scripts/install-codex-agents.sh <plugin>              # one plugin's agents only
scripts/install-codex-agents.sh --project ~/code/app  # into app/.codex/agents
scripts/install-codex-agents.sh --uninstall           # remove them again
```

## Validate and test

```bash
claude plugin validate . --strict                 # catalog
claude plugin validate plugins/<name> --strict    # one plugin

# test a local checkout in each tool
/plugin marketplace add /path/to/kailasa-marketplace          # Claude Code
codex plugin marketplace add /path/to/kailasa-marketplace     # Codex
```

CI (`.github/workflows/validate.yml`) runs on every PR and every push to `main`. It:

- validates the catalog and every plugin with Claude Code
- installs every plugin into a throwaway Codex home
- checks that each Codex agent file has the required keys
