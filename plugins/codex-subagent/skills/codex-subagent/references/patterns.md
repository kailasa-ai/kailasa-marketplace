# Delegation patterns

Worked recipes. `$CODEX_SKILL` is this skill's directory — see the resolver
snippet in `SKILL.md`.

## Contents
- [Second opinion / adversarial cross-check](#second-opinion--adversarial-cross-check)
- [Parallel fan-out across repos](#parallel-fan-out-across-repos)
- [Worktree isolation for parallel edits](#worktree-isolation-for-parallel-edits)
- [Large mechanical refactor](#large-mechanical-refactor)
- [Delegated code review](#delegated-code-review)
- [Multi-turn investigation](#multi-turn-investigation)
- [CI usage](#ci-usage)

## Second opinion / adversarial cross-check

The highest-value pattern, because it uses the one thing Codex has that Claude
does not: independence. Claude re-checking its own reasoning mostly reproduces
it; a different model family genuinely might not.

Give Codex the problem, **not** Claude's answer — priming it with the conclusion
you want checked is how you manufacture false agreement:

```bash
"$CODEX_SKILL/scripts/codex_run.sh" --mode read --dir /repo \
  --task "Users intermittently get logged out after ~15 minutes despite a 24h
token TTL. Investigate src/auth/ and identify the root cause. Cite file:line."
```

Then compare independently-reached conclusions. Agreement is meaningful
corroboration; disagreement is the useful case — it marks the spot worth a human
looking at.

## Parallel fan-out across repos

Launch one Claude subagent per target in a **single message** so they run
concurrently, each shelling out to its own Codex run:

```
Agent 1: codex_run.sh --mode read --dir /repos/api      --task "<audit prompt>"
Agent 2: codex_run.sh --mode read --dir /repos/web      --task "<audit prompt>"
Agent 3: codex_run.sh --mode read --dir /repos/worker   --task "<audit prompt>"
```

Give each `--out` an explicit distinct directory if you want to inspect the raw
captures afterwards; otherwise each gets its own `mktemp` dir automatically.

Pair with `--schema` so the results come back as comparable structured objects
rather than three differently-shaped prose reports.

## Worktree isolation for parallel edits

Concurrent `--mode write` runs in the *same* repo will collide. Give each its own
git worktree:

```bash
git -C /repo worktree add /tmp/wt-feat-a -b codex/task-a
"$CODEX_SKILL/scripts/codex_run.sh" --mode write --dir /tmp/wt-feat-a --task "..."
```

Each Codex agent then has a private checkout, and results are merged
deliberately rather than racing.

## Large mechanical refactor

The context-offloading case. Codex does the bulk edit in its own process; only
the summary returns:

```bash
"$CODEX_SKILL/scripts/codex_run.sh" --mode write --dir /repo --timeout 3600 \
  --task "Convert every callback-style function in src/api/ to async/await.
Preserve behaviour exactly. Run the test suite and report failures. Do not
change public signatures."
```

Raise `--timeout` for these — the 900s default is sized for investigations, not
for a refactor plus a test run.

Delegate this only when the repo is committed or otherwise recoverable. Codex
edits real files, and `--mode write` is not a dry run.

## Delegated code review

```bash
cd /repo && codex review -c sandbox_mode="read-only" --base main > /tmp/review.md
```

`codex review` beats a generic `exec` prompt asking for a review, since it is
purpose-built and diff-aware. Constraints: needs a real git repo, has no `-C`
(so `cd` first), no `--json`, no `-o`, and **no `-s`** — without
`-c sandbox_mode="read-only"` it inherits whatever `config.toml` says, which may
be `danger-full-access`.

Expect it to be slow: a single ~600-line commit ran past 10 minutes at high
reasoning effort. Launch it in the background and collect the file afterwards
rather than blocking a delegation on it.

## Multi-turn investigation

Broad first, narrow after — cheaper than one enormous prompt, and each turn is
informed by the last:

```bash
OUT=$("$CODEX_SKILL/scripts/codex_run.sh" --mode read --dir /repo \
        --task "Map the payment flow end to end.")
TID=$(printf '%s' "$OUT" | sed -n 's/^thread_id=//p')

"$CODEX_SKILL/scripts/codex_run.sh" --resume "$TID" --dir /repo --mode read \
  --task "Where in that flow could a double-charge occur under retry?"
```

The thread keeps prior context, so the follow-up needn't restate anything.

## CI usage

```bash
codex exec --ignore-user-config --skip-git-repo-check \
  -s read-only -m gpt-5.6-sol \
  --output-schema ci/findings-schema.json -o findings.json \
  "Review the diff against main for security regressions." < /dev/null
```

Authenticate with `CODEX_API_KEY` in the environment rather than interactive
login. `--ignore-user-config` keeps a developer's local settings from changing CI
behaviour. Gate the build on parsed fields from `findings.json` rather than on
grepping prose.
