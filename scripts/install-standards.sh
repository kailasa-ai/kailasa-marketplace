#!/usr/bin/env bash
set -euo pipefail

SRC="$(cd "$(dirname "$0")/.." && pwd)"
STAMP="$(date +%Y%m%d-%H%M%S)"

link_all() {
  local khome="$HOME/.kailasa" stamp="$1"
  mkdir -p "$HOME/.claude" "$HOME/.codex"
  for pair in "standards/CLAUDE.md:.claude/CLAUDE.md" "standards/AGENTS.md:.codex/AGENTS.md"; do
    local target="$khome/${pair%%:*}" dest="$HOME/${pair##*:}"
    if [[ -e "$dest" && ! -L "$dest" && -s "$dest" ]]; then
      mv "$dest" "$dest.pre-standards-$stamp"
      echo "backed up $dest -> $dest.pre-standards-$stamp"
    fi
    ln -sfn "$target" "$dest"
    echo "linked $dest -> $target"
  done
}

if [[ "${1:-}" == "--push" ]]; then
  shift
  for host in "$@"; do
    echo "== $host"
    git -C "$SRC" archive --format=tar HEAD standards | ssh -o BatchMode=yes "$host" \
      'rm -rf ~/.kailasa/standards.new && mkdir -p ~/.kailasa/standards.new && tar -C ~/.kailasa/standards.new --strip-components=1 -xf - && rm -rf ~/.kailasa/standards && mv ~/.kailasa/standards.new ~/.kailasa/standards'
    ssh -o BatchMode=yes "$host" "bash -s -- $STAMP" < <(declare -f link_all; echo 'link_all "$1"')
  done
else
  mkdir -p "$HOME/.kailasa"
  ln -sfn "$SRC/standards" "$HOME/.kailasa/standards"
  link_all "$STAMP"
fi
