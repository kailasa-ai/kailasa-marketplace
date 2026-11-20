#!/usr/bin/env bash
set -euo pipefail

REPO_URL="git@github.com:kailasa-ai/kailasa-marketplace.git"
KHOME="$HOME/.kailasa"
STAMP="$(date +%Y%m%d-%H%M%S)"

if [[ "${1:-}" == "--remote" ]]; then
  SRC="$KHOME/kailasa-marketplace"
  if [[ -d "$SRC/.git" ]]; then git -C "$SRC" pull --ff-only -q; else git clone -q "$REPO_URL" "$SRC"; fi
else
  SRC="$(cd "$(dirname "$0")/.." && pwd)"
fi

mkdir -p "$KHOME" "$HOME/.claude" "$HOME/.codex"
ln -sfn "$SRC/standards" "$KHOME/standards"

link() {
  local target="$1" dest="$2"
  if [[ -e "$dest" && ! -L "$dest" && -s "$dest" ]]; then
    mv "$dest" "$dest.pre-standards-$STAMP"
    echo "backed up $dest -> $dest.pre-standards-$STAMP"
  fi
  ln -sfn "$target" "$dest"
  echo "linked $dest -> $target"
}

link "$KHOME/standards/CLAUDE.md" "$HOME/.claude/CLAUDE.md"
link "$KHOME/standards/AGENTS.md" "$HOME/.codex/AGENTS.md"
