#!/usr/bin/env bash
# Scaffold a one-skill plugin under plugins/<name> and register it in marketplace.json.
#
# Usage:
#   scripts/new-plugin.sh <name> "<description>" [--from <existing-skill-dir>] [--category <category>]
#
# Examples:
#   scripts/new-plugin.sh hourly-updates "Formats hourly work updates and EOD reports"
#   scripts/new-plugin.sh npedia-fetch "Fetch data from nithyanandapedia.org" --from ~/.claude/skills/npedia-fetch --category research
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
MARKETPLACE="$ROOT/.claude-plugin/marketplace.json"
TEMPLATE="$ROOT/templates/skill-plugin"

usage() { sed -n '2,10p' "$0" | sed 's/^# \{0,1\}//'; exit 1; }

[[ $# -ge 2 ]] || usage
NAME="$1"; DESCRIPTION="$2"; shift 2
FROM=""; CATEGORY="productivity"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --from) FROM="$2"; shift 2 ;;
    --category) CATEGORY="$2"; shift 2 ;;
    *) usage ;;
  esac
done

if [[ ! "$NAME" =~ ^[a-z0-9]+(-[a-z0-9]+)*$ ]]; then
  echo "error: name must be kebab-case (lowercase letters, digits, hyphens)" >&2; exit 1
fi
DEST="$ROOT/plugins/$NAME"
if [[ -e "$DEST" ]]; then
  echo "error: $DEST already exists" >&2; exit 1
fi
if jq -e --arg n "$NAME" '.plugins[] | select(.name == $n)' "$MARKETPLACE" >/dev/null; then
  echo "error: '$NAME' is already listed in marketplace.json" >&2; exit 1
fi

mkdir -p "$DEST/.claude-plugin" "$DEST/skills"
jq --arg n "$NAME" --arg d "$DESCRIPTION" '.name = $n | .description = $d' \
  "$TEMPLATE/.claude-plugin/plugin.json" > "$DEST/.claude-plugin/plugin.json"

if [[ -n "$FROM" ]]; then
  [[ -f "$FROM/SKILL.md" ]] || { echo "error: $FROM/SKILL.md not found" >&2; rm -rf "$DEST"; exit 1; }
  cp -R "$FROM" "$DEST/skills/$NAME"
else
  mkdir -p "$DEST/skills/$NAME"
  # Escape for a double-quoted YAML string, then for a sed replacement.
  esc_desc=$(printf '%s' "$DESCRIPTION" | sed -e 's/[\\"]/\\&/g' -e 's/[&|\\]/\\&/g')
  sed -e "s|__NAME__|$NAME|g" -e "s|__DESCRIPTION__|$esc_desc|g" \
    "$TEMPLATE/skills/__NAME__/SKILL.md" > "$DEST/skills/$NAME/SKILL.md"
fi

tmp="$(mktemp)"
jq --arg n "$NAME" --arg d "$DESCRIPTION" --arg c "$CATEGORY" \
  '.plugins += [{name: $n, description: $d, source: ("./plugins/" + $n), category: $c}]' \
  "$MARKETPLACE" > "$tmp" && mv "$tmp" "$MARKETPLACE"

echo "Created plugins/$NAME and registered it in marketplace.json"
echo "Next: edit plugins/$NAME/skills/$NAME/SKILL.md, then run: claude plugin validate . --strict"
