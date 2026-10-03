#!/usr/bin/env python3
"""Summarise a `codex exec --json` JSONL event stream.

Why: the raw stream is noisy to eyeball and the interesting bits (thread id for
resuming, the final answer, token spend) are scattered across different event
types. This collapses it to the few facts a delegating agent actually needs.

Usage:
    codex_parse.py <events.jsonl>              # human-readable summary
    codex_parse.py <events.jsonl> --json       # machine-readable summary
    codex_parse.py <events.jsonl> --final-only # just the final agent message
"""
import json
import sys


def parse(path):
    thread_id = None
    messages = []
    usage = {}
    items = []
    errors = []

    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                # Non-JSON lines can appear if stderr was merged into the file.
                errors.append(line[:200])
                continue

            etype = event.get("type")
            if etype == "thread.started":
                thread_id = event.get("thread_id")
            elif etype == "turn.completed":
                usage = event.get("usage", {}) or {}
            elif etype == "turn.failed" or etype == "error":
                errors.append(json.dumps(event)[:500])
            elif etype == "item.completed":
                item = event.get("item", {}) or {}
                items.append(item.get("type", "unknown"))
                if item.get("type") == "agent_message":
                    messages.append(item.get("text", ""))

    return {
        "thread_id": thread_id,
        "final_message": messages[-1] if messages else "",
        "message_count": len(messages),
        "item_types": items,
        "usage": usage,
        "errors": errors,
    }


def main():
    args = [a for a in sys.argv[1:]]
    if not args:
        print(__doc__)
        return 2
    path = args[0]
    flags = set(args[1:])

    try:
        result = parse(path)
    except FileNotFoundError:
        print(f"codex_parse: no such file: {path}", file=sys.stderr)
        return 1

    if "--final-only" in flags:
        print(result["final_message"])
        return 0

    if "--json" in flags:
        print(json.dumps(result, indent=2))
        return 0

    u = result["usage"]
    print(f"thread_id : {result['thread_id'] or 'none'}")
    print(f"items     : {len(result['item_types'])} ({', '.join(result['item_types']) or 'none'})")
    if u:
        total_in = u.get("input_tokens", 0)
        cached = u.get("cached_input_tokens", 0)
        print(
            f"tokens    : in={total_in} (cached {cached}) "
            f"out={u.get('output_tokens', 0)} "
            f"reasoning={u.get('reasoning_output_tokens', 0)}"
        )
    if result["errors"]:
        print(f"errors    : {len(result['errors'])}")
        for e in result["errors"][:3]:
            print(f"  ! {e}")
    print("--- final message ---")
    print(result["final_message"] or "(no agent message produced)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
