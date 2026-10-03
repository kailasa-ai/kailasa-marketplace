# KAILASA Marketplace

KAILASA's private [Claude Code plugin marketplace](https://code.claude.com/docs/en/plugin-marketplaces). It is the one place where the organization stores and publishes skills, plugins, subagents, slash commands, hooks and MCP servers.

Marketplace name: **`kailasa`**. Plugins are installed as `<plugin>@kailasa`.

## Install

You need read access to `kailasa-ai/kailasa-marketplace` on GitHub. Claude Code uses your existing git credentials, so `gh auth login` is enough.

```bash
# inside Claude Code
/plugin marketplace add kailasa-ai/kailasa-marketplace
/plugin install codex-subagent@kailasa

# or from a shell
claude plugin marketplace add kailasa-ai/kailasa-marketplace
claude plugin install codex-subagent@kailasa
```

To browse everything available, run `/plugin` and open the **Discover** tab.

To pull new versions, run `/plugin marketplace update kailasa`. You can also turn on auto-update for `kailasa` in `/plugin` → **Marketplaces**. Auto-update is off by default for third-party marketplaces.

### Background auto-update for private repos

Claude Code updates marketplaces in the background at startup, and those updates can't use interactive git credentials. If you want background updates to work, export a token in your shell profile:

```bash
export GITHUB_TOKEN=ghp_xxx   # needs read access to kailasa-ai repos
```

### Auto-register the marketplace in a project

Commit the following to a project's `.claude/settings.json`. Anyone who trusts the folder will then be prompted to add the marketplace and install the plugins listed under `enabledPlugins`:

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

On a Claude Team or Enterprise plan, the same keys can go into managed settings so that they apply to every member.

## Catalog

| Plugin | What it does | Source |
|---|---|---|
| `codex-subagent` | Delegate tasks from Claude Code to OpenAI Codex agents (headless `codex exec`, sandboxing, resumable threads) | [kailasa-ai/codex-subagent-plugin](https://github.com/kailasa-ai/codex-subagent-plugin) |

## Layout

```
kailasa-marketplace/
├── .claude-plugin/marketplace.json   # the catalog: every plugin must be listed here
├── plugins/                          # plugins that live in this repo, one folder per plugin
│   └── <name>/
│       ├── .claude-plugin/plugin.json
│       ├── skills/<name>/SKILL.md    # skills
│       ├── agents/*.md               # subagents (optional)
│       ├── commands/*.md             # slash commands (optional)
│       ├── hooks/hooks.json          # hooks (optional)
│       └── .mcp.json                 # MCP servers (optional)
├── templates/skill-plugin/           # template used by scripts/new-plugin.sh
└── scripts/new-plugin.sh             # scaffolds a plugin and registers it
```

## Adding something

**Convention: one plugin per skill.** Each skill ships as its own plugin with the same name, so people install only what they need.

### A new skill

```bash
# start from scratch
scripts/new-plugin.sh hourly-updates "Formats hourly work updates and EOD reports"

# or import an existing skill folder (must contain SKILL.md)
scripts/new-plugin.sh npedia-fetch "Fetch and search nithyanandapedia.org" \
  --from ~/.claude/skills/npedia-fetch --category research
```

The script creates `plugins/<name>/` and adds the plugin to `marketplace.json`. Next, edit `SKILL.md`, then run the validator and open a PR. Write the `description` in the frontmatter carefully, because Claude uses it to decide when to load the skill.

### An agent, command, hook or MCP server

Put it inside the plugin it belongs to:

- `agents/<name>.md`
- `commands/<name>.md`
- `hooks/hooks.json`
- `.mcp.json`

Refer to files inside the plugin with `${CLAUDE_PLUGIN_ROOT}`. If you don't want to use the script, you can create a plugin folder by hand under `plugins/`.

### A plugin that lives in its own repo

Add an entry to `marketplace.json` with a `github` source. `codex-subagent` is listed this way:

```json
{
  "name": "my-plugin",
  "description": "...",
  "source": { "source": "github", "repo": "kailasa-ai/my-plugin", "ref": "main" }
}
```

### Releasing changes

Bump `version` in the plugin's `plugin.json` whenever you change it. Users only receive an update when the version changes.

## Validate

```bash
claude plugin validate . --strict             # marketplace
claude plugin validate plugins/<name> --strict  # one plugin
```

CI (`.github/workflows/validate.yml`) runs the same checks on every PR and on every push to `main`.

## Test locally before publishing

```bash
/plugin marketplace add /Volumes/X10Pro/code/kailasa-marketplace
/plugin install <name>@kailasa
```
