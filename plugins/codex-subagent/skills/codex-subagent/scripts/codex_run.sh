#!/usr/bin/env bash
# codex_run.sh — canonical wrapper for delegating a task to a Codex agent.
#
# Why this exists: every delegation needs the same half-dozen flags, a portable
# timeout (macOS ships no `timeout` binary), stdin closed (codex blocks reading
# stdin otherwise), and the thread_id extracted so the run can be resumed. Doing
# that by hand each time is how flags drift and runs hang.
#
# Usage:
#   codex_run.sh --task "<prompt>"   --dir <path> --mode read|write|full [opts]
#   codex_run.sh --task @<file>      --dir <path> --mode read
#   codex_run.sh --resume <thread_id> --task "<follow-up>" --dir <path> --mode read
#
# Options:
#   --task <text|@file>  Task prompt, or @path to read the prompt from a file. (required)
#   --dir <path>         Working root for the agent. (required)
#   --mode <m>           read | write | full. Default: read.
#   --resume <id>        Continue an existing thread instead of starting a new one.
#   --schema <file>      JSON Schema file; final message is forced to conform.
#   --model <name>       Override the model (e.g. gpt-5.6-sol).
#   --effort <level>     minimal | low | medium | high | xhigh.
#   --add-dir <path>     Extra writable dir (repeatable, write mode only).
#   --timeout <secs>     Wall-clock limit. Default: 900.
#   --out <dir>          Where to put artifacts. Default: a fresh mktemp dir.
#
# Artifacts written to <out>: events.jsonl, last.md (or last.json), stderr.log, thread_id
# Exit codes: 0 ok | 1 codex runtime error | 2 bad usage | 124 timeout

set -uo pipefail

TASK="" DIR="" MODE="read" RESUME="" SCHEMA="" MODEL="" EFFORT="" TIMEOUT=900 OUT=""
ADD_DIRS=()

die() { printf 'codex_run: %s\n' "$1" >&2; exit 2; }

while [ $# -gt 0 ]; do
  case "$1" in
    --task)    TASK="${2:-}"; shift 2 ;;
    --dir)     DIR="${2:-}"; shift 2 ;;
    --mode)    MODE="${2:-}"; shift 2 ;;
    --resume)  RESUME="${2:-}"; shift 2 ;;
    --schema)  SCHEMA="${2:-}"; shift 2 ;;
    --model)   MODEL="${2:-}"; shift 2 ;;
    --effort)  EFFORT="${2:-}"; shift 2 ;;
    --add-dir) ADD_DIRS+=("${2:-}"); shift 2 ;;
    --timeout) TIMEOUT="${2:-}"; shift 2 ;;
    --out)     OUT="${2:-}"; shift 2 ;;
    -h|--help) sed -n '2,30p' "$0"; exit 0 ;;
    *) die "unknown argument: $1" ;;
  esac
done

[ -n "$TASK" ] || die "--task is required"
[ -n "$DIR" ]  || die "--dir is required"
[ -d "$DIR" ]  || die "--dir does not exist: $DIR"
command -v codex >/dev/null 2>&1 || die "codex not found on PATH"

# @file form: read the prompt from a file. Keeps huge prompts off the argv limit.
case "$TASK" in
  @*) TASK_FILE="${TASK#@}"
      [ -f "$TASK_FILE" ] || die "task file not found: $TASK_FILE"
      TASK="$(cat "$TASK_FILE")" ;;
esac

case "$MODE" in
  read)  SANDBOX="read-only" ;;
  write) SANDBOX="workspace-write" ;;
  full)  SANDBOX="danger-full-access" ;;
  *) die "--mode must be read, write, or full (got: $MODE)" ;;
esac

if [ -z "$OUT" ]; then
  OUT="$(mktemp -d "${TMPDIR:-/tmp}/codex-run-XXXXXX")"
else
  mkdir -p "$OUT"
fi

EVENTS="$OUT/events.jsonl"
ERRLOG="$OUT/stderr.log"
if [ -n "$SCHEMA" ]; then LAST="$OUT/last.json"; else LAST="$OUT/last.md"; fi

# Build argv. Note: `codex exec` has NO -a/--ask-for-approval flag (that is
# TUI-only). Approval policy is irrelevant headless anyway — the sandbox is what
# constrains the run, so we set it explicitly rather than inheriting whatever
# ~/.codex/config.toml says (which may be danger-full-access).
ARGS=(exec)
if [ -n "$RESUME" ]; then
  # `codex exec resume` rejects -s/--sandbox, -C/--cd and --add-dir: the resumed
  # session keeps the sandbox policy and working root it was created with.
  # Passing them anyway is an argument error (exit 2).
  ARGS+=(resume "$RESUME" --json --skip-git-repo-check -o "$LAST")
else
  ARGS+=(--json --skip-git-repo-check -s "$SANDBOX" -C "$DIR" -o "$LAST")
  for d in ${ADD_DIRS+"${ADD_DIRS[@]}"}; do ARGS+=(--add-dir "$d"); done
fi
[ -n "$SCHEMA" ] && ARGS+=(--output-schema "$SCHEMA")
[ -n "$MODEL" ]  && ARGS+=(-m "$MODEL")
[ -n "$EFFORT" ] && ARGS+=(-c "model_reasoning_effort=\"$EFFORT\"")
ARGS+=("$TASK")

# stdin MUST be closed: with a pipe or tty on stdin, codex blocks on
# "Reading additional input from stdin..." and the delegation hangs forever.
codex "${ARGS[@]}" < /dev/null > "$EVENTS" 2> "$ERRLOG" &
PID=$!

WAITED=0
while kill -0 "$PID" 2>/dev/null; do
  if [ "$WAITED" -ge "$TIMEOUT" ]; then
    # Braces + redirect suppress the shell's "Terminated: 15" job notice,
    # which otherwise pollutes the caller's output on every timeout.
    { kill -TERM "$PID" 2>/dev/null; sleep 2; kill -KILL "$PID" 2>/dev/null; \
      wait "$PID"; } 2>/dev/null
    printf 'codex_run: timed out after %ss\n' "$TIMEOUT" >&2
    printf 'out_dir=%s\n' "$OUT"
    exit 124
  fi
  sleep 1
  WAITED=$((WAITED + 1))
done
wait "$PID"; RC=$?

# thread_id enables follow-up turns via --resume. Emitted on thread.started.
THREAD_ID="$(sed -n 's/.*"thread_id":"\([^"]*\)".*/\1/p' "$EVENTS" 2>/dev/null | head -1)"
[ -n "$THREAD_ID" ] && printf '%s\n' "$THREAD_ID" > "$OUT/thread_id"

printf 'exit_code=%s\n' "$RC"
printf 'out_dir=%s\n' "$OUT"
printf 'thread_id=%s\n' "${THREAD_ID:-none}"
printf 'result_file=%s\n' "$LAST"

if [ "$RC" -ne 0 ]; then
  printf -- '--- stderr ---\n' >&2
  tail -20 "$ERRLOG" >&2
fi
exit "$RC"
