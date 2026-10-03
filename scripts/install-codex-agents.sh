#!/usr/bin/env bash
# Install Codex custom agents shipped in plugins/*/codex-agents/*.toml.
#
# Codex plugins cannot carry agents (Codex loads agents only from ~/.codex/agents
# or <repo>/.codex/agents), so they are copied there from a clone of this repo.
#
# Usage:
#   scripts/install-codex-agents.sh [--project <repo-dir>] [--uninstall] [plugin...]
#
#   No plugin names = every plugin that has codex-agents/.
#   --project <dir>  install into <dir>/.codex/agents instead of ~/.codex/agents
#   --uninstall      remove the agents instead of installing them
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEST="${CODEX_HOME:-$HOME/.codex}/agents"
UNINSTALL=0
PLUGINS=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --project) DEST="$2/.codex/agents"; shift 2 ;;
    --uninstall) UNINSTALL=1; shift ;;
    -h|--help) sed -n '2,12p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) PLUGINS+=("$1"); shift ;;
  esac
done

if [[ ${#PLUGINS[@]} -eq 0 ]]; then
  for d in "$ROOT"/plugins/*/codex-agents; do
    [[ -d "$d" ]] && PLUGINS+=("$(basename "$(dirname "$d")")")
  done
fi
if [[ ${#PLUGINS[@]} -eq 0 ]]; then
  echo "No plugins ship Codex agents."; exit 0
fi

mkdir -p "$DEST"
for p in "${PLUGINS[@]}"; do
  src="$ROOT/plugins/$p/codex-agents"
  [[ -d "$src" ]] || { echo "error: plugins/$p has no codex-agents/ directory" >&2; exit 1; }
  for f in "$src"/*.toml; do
    [[ -e "$f" ]] || continue
    if [[ $UNINSTALL -eq 1 ]]; then
      rm -f "$DEST/$(basename "$f")" && echo "removed $DEST/$(basename "$f")"
    else
      cp "$f" "$DEST/" && echo "installed $DEST/$(basename "$f")"
    fi
  done
done
[[ $UNINSTALL -eq 1 ]] || echo "Restart Codex to pick up new agents."
