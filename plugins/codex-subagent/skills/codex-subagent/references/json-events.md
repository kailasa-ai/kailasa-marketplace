# The `codex exec --json` event stream

Captured empirically from codex-cli 0.147.0, not inferred from docs.

## Contents
- [Shape of the stream](#shape-of-the-stream)
- [Event types](#event-types)
- [Item types](#item-types)
- [Do not depend on command-level telemetry](#do-not-depend-on-command-level-telemetry)
- [Parsing recipes](#parsing-recipes)

## Shape of the stream

One JSON object per line on stdout. A complete successful run:

```json
{"type":"thread.started","thread_id":"01a02458-78be-7893-9a77-15a46bc89224"}
{"type":"turn.started"}
{"type":"item.completed","item":{"id":"item_0","type":"agent_message","text":"OK"}}
{"type":"turn.completed","usage":{"input_tokens":19873,"cached_input_tokens":9984,"cache_write_input_tokens":0,"output_tokens":5,"reasoning_output_tokens":0}}
```

Progress chatter goes to **stderr**, not stdout, so stdout stays clean JSONL.
Keep the two separated when capturing — merging them means non-JSON lines in the
middle of the stream.

## Event types

| `type` | Fields | Notes |
|---|---|---|
| `thread.started` | `thread_id` | First line. **Capture this** — it is the handle for `codex exec resume`. |
| `turn.started` | — | No payload. |
| `item.started` | `item` | Work beginning on an item. Progress only. |
| `item.completed` | `item` | One per completed item; see below. |
| `turn.completed` | `usage` | Last line on success. Token accounting. |

`usage` fields: `input_tokens`, `cached_input_tokens`, `cache_write_input_tokens`,
`output_tokens`, `reasoning_output_tokens`.

`input_tokens` appears to be the total including cached, so cost estimates should
treat `cached_input_tokens` as a discounted subset rather than an addition.

## Item types

Items arrive as `item.started` (work beginning) and `item.completed` (work
finished). Only `item.completed` carries the final state, so parse that and
ignore `item.started` unless you want live progress.

### `agent_message`
Fields: `id`, `type`, `text`.

A run typically emits several — intermediate narration followed by the final
answer. **The last one is the result.** Concatenating them all gives you the
model thinking out loud, which is usually not what you want.

### `command_execution`
Fields: `id`, `type`, `command`, `aggregated_output`, `exit_code`, `status`.

```json
{"type":"item.completed","item":{"id":"item_1","type":"command_execution",
 "command":"/bin/zsh -lc \"rg -n pattern . | head -40\"",
 "aggregated_output":"...","exit_code":0,"status":"completed"}}
```

This is the useful one for auditing: it shows exactly what shell commands the
delegated agent ran, their output, and whether they succeeded.

## Do not depend on command-level telemetry

Item emission is best-effort, not a guarantee. In one verified 0.147.0 run the
agent demonstrably executed shell commands — its final message quoted genuine
`zsh: operation not permitted` output — yet the stream contained **only**
`agent_message` items, with no `command_execution` at all. A near-identical run
against a real repo emitted them normally.

So treat command items as a bonus when present. If you actually need to know
what Codex ran, ask for it in the prompt and have Codex state it in the final
message, or pin it down with `--output-schema`. Building delegation logic that
breaks when `command_execution` is missing will fail intermittently and be
miserable to debug.

`turn.failed` and `error` events are handled defensively by `codex_parse.py` but
were not observed in any successful or failed run here; failures surfaced via
exit code and stderr instead.

## Parsing recipes

Use `scripts/codex_parse.py` rather than re-deriving these:

```bash
python3 scripts/codex_parse.py events.jsonl                # human summary
python3 scripts/codex_parse.py events.jsonl --json         # machine summary
python3 scripts/codex_parse.py events.jsonl --final-only   # just the answer
```

Ad-hoc equivalents with `jq`:

```bash
# thread id, for resuming
jq -r 'select(.type=="thread.started") | .thread_id' events.jsonl

# final agent message
jq -r 'select(.type=="item.completed" and .item.type=="agent_message") | .item.text' \
  events.jsonl | tail -1

# token usage
jq -c 'select(.type=="turn.completed") | .usage' events.jsonl
```

If `--output-schema` was used, the final `agent_message.text` is a JSON *string*
containing the schema-conforming object, so it needs a second parse:

```bash
jq -r 'select(.item.type=="agent_message") | .item.text' events.jsonl \
  | tail -1 | jq .
```

Simpler: pass `-o out.json` and read that file directly — it holds the same
object already unwrapped.
