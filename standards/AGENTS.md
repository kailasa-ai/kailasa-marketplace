# KAILASA Agent Standard (master AGENTS.md)

<!-- REVIEW DRAFT. Every rule has an ID (e.g. G3) so you can say "keep / cut / change".
     ‹src: …› / ‹decided …› tags show where a rule came from; they are stripped before publishing. -->

Applies to every AI coding agent (Claude Code, Codex) working on KAILASA machines,
servers and repositories, for every team member. This file is the single source of
truth: `CLAUDE.md` only imports it. Repo files (`<repo>/AGENTS.md`) add repo-specific
rules and **win on conflicts** about that repo; this file wins on safety (§5, §6).

Playbooks in `~/.kailasa/standards/playbooks/` (load only when relevant):
`delegation.md` · `git.md` · `verification.md` · `deploy-and-prod.md` · `servers.md` · `repo-docs.md`

---

## 1. How to work

- **W1. Do exactly what was asked.** No extra features, refactors, or "improvements". Never re-add something the user removed; if it seems needed, ask. ‹src: recurring "why is X still here" corrections, ~20 prompts›
- **W2. Plan first for non-trivial work.** If the user says "plan only" or "don't start yet", produce the plan and stop. ‹src: causing_portal AGENTS, ~15 prompts›
- **W3. Honour holds and gates literally.** "Don't merge", "don't start phase 2", "only analyze" stay in force until the user lifts them. Time-boxed overrides ("no Codex till 10 AM") expire at the stated time. ‹src: ~52 prompts, 6 feedback memories›
- **W4. Autonomy once authorised.** When told to "keep going / loop through the phases", continue without check-ins; stop only for a decision, a credential, or an approval gate (§5). ‹src: ~72 prompts›
- **W5. Reuse before creating.** Wire existing routes, tables, components and design tokens before adding new ones. Prefer existing metadata fields over a new table. ‹src: crm-wire-existing-only, SOMA web "never hardcode hex"›
- **W6. Fix root causes.** Never hide a bug or weaken a test to get a gate green. ‹src: causing_portal, V4 CODEX-PROTOCOL›
- **W7. Use current docs.** For any library, SDK, CLI or cloud API, fetch current docs (Context7, or the vendor's skill/SDK docs) instead of answering from memory. ‹src: ~/.claude/rules/context7.md, telnyx correction›

## 2. Delegation and models  → `playbooks/delegation.md`

- **D1. The main session orchestrates and verifies.** Heavy, long or mechanical work goes to Codex CLI or cheaper subagents. The main session writes the scoped brief, reviews the diff, runs verification, and reports. ‹src: 8 feedback memories, ~60 prompts — strongest rule found›
- **D2. Cheapest tier that can do the job, always the latest model of that tier** (check the model list; never hardcode model IDs in docs).
  - mechanical / lookup → smallest tier (Haiku, Codex low tier)
  - routine, well-specified change → mid tier (Sonnet, Codex mid tier)
  - hard design, tricky debugging, final judging → top tier (Opus, Codex top tier)
  - Repos must not ban a tier outright. ‹decided 2026-11-20; removes causing_portal "Never use Opus"›
- **D3. Independent review by the other model family before anything reaches `main`.** Every `dev → main` promotion and release gets a Codex review (Claude-written code) or a Claude review (Codex-written code). On everyday PRs to `dev` it is optional unless the user asks. ‹decided 2026-11-20›
- **D4. A review that didn't run is not a clean review.** Empty output, out-of-credits or a missing result file = "review not done". Say so.
- **D5. Fallback.** If Codex is unavailable or out of credits, continue with Claude subagents; don't stop to ask.
- **D6. One owner per worktree.** Never let two agents edit the same worktree or race the same task.

## 3. Git  → `playbooks/git.md`

- **G0. Branch model: `dev` = integration, `main` = production.** Feature PRs target `dev`; `main` changes only through a `dev → main` promotion PR. Repos still on `master` / `central/dev` are being migrated; until then their AGENTS.md names the current branches. ‹decided 2026-11-20›
- **G1. Work in a git worktree,** never in the main checkout. Branch from fresh `origin/dev`; name it `feat/…`, `fix/…`, `chore/…` or `refactor/…`. ‹src: causing_portal feedback, 33 prompts, worktree.baseRef›
- **G2. Never push to, or merge into, `dev` or `main` directly.** Everything lands through a PR.
- **G3. Push your own feature branch and open a PR freely.** Merging needs the user's go-ahead. ‹decided 2026-11-20›
- **G4. Before showing work, run `git status` and `git diff --stat`** and re-read your own diff.
- **G5. Squash-merge PRs.** One commit per PR on `dev`, titled as a Conventional Commit with `(#PR)`. Rebase on `origin/dev` before merge; no merge commits on feature branches. ‹decided 2026-11-20›
- **G6. Never `git stash`** (shared across worktrees and agents). Never `--no-verify`. `--force-with-lease` only, and only on your own branch.
- **G7. Commits: Conventional Commits with a scope,** e.g. `fix(chat): keep draft on account switch`. Subject describes the user-visible effect in plain language. A ticket ID goes in the scope or body when one exists.
- **G8. AI attribution.** Every agent-written commit ends with a `Co-Authored-By:` trailer for the model that wrote it (Claude or Codex); every agent-opened PR ends with a "Generated with …" footer. ‹decided 2026-11-20›
- **G9. Before promoting `dev → main`,** run `git log origin/main..origin/dev` and stop to ask if there are commits you don't recognise. ‹src: dev-to-main-promotion-check›
- **G10. `git fetch` and compare with origin** before trusting any local checkout's state.

## 4. Verification  → `playbooks/verification.md`

- **V1. Verify it yourself, in a real environment, before reporting done.** Run it locally (Docker, browser, simulator) or deploy to DEV and use it in a browser. ‹src: ~125 prompts — strongest user expectation›
- **V2. Look at what you built.** For any UI, render it and inspect screenshots (light + dark, phone width) before showing it. For documents/PDFs, render and read the output; passing checks are not enough. ‹src: render-before-showing-ui, book_editor›
- **V3. Light checks while building, full suite at the end.** Smoke-test during development; run the full suite (incl. goldens) before any merge to `main`, release build or promotion. ‹src: book_editor, SOMA, full-golden-before-builds›
- **V4. Report facts, not hopes.** Built / uploaded / merged / CI-passed / deployed / live are different facts; claim only what you verified, and state what was *not* verified.
- **V5. Check provenance before stating numbers:** what it counts, which source, how fresh. When asked to verify, audit everything; don't spot-check.
- **V6. Tests must be able to fail.** No success-only tests; mutation-check new regression tests; never accept golden-image changes without opening them.
- **V7. Long commands go to a log file in the background;** poll with bounded waits; wait for the real exit code (never pipe a long build through `tail`).
- **V8. Browser testing has side effects.** Only open/observe irreversible controls (call, send, pay, delete); never click them unless that is the task.

## 5. Safety, production and approvals  → `playbooks/deploy-and-prod.md`

Ask first and wait for an explicit yes before:
- **S1.** Store actions that reach users: TestFlight/Play upload (only after the user approves in a local simulator), going live, Android production track, withdrawing a build in review.
- **S2.** Any production DB mutation, production data deletion, or bulk send (email/SMS/push/WhatsApp).
- **S3.** Anything outward-facing or irreversible: messages to real people, app-review requests, DNS (the owner does DNS), spending money, rotating/revoking credentials.

Standing rules:
- **S4. Production is read-only by default.** Read-only diagnosis (`SET default_transaction_read_only=on`) is fine; writes need S2.
- **S5. Never copy production user data into DEV** or test runners.
- **S6. Who deploys:** agents deploy **DEV** on their own. For **PROD** the agent prepares everything (branch, migration plan, backup, exact steps) and runs it **only after an explicit yes** in the current conversation, then watches logs/health until stable. ‹decided 2026-11-20; replaces "only humans deploy" lines›
- **S7. How to deploy:** via Dokploy; SSH only for what Dokploy can't do (say so). Take the host deploy lock, deploy from `main`, no merges to `main` during a deploy, graceful stops (`docker stop -t 90`, never kill). ‹src: SOMA PROD rules after 2026-10-30 incident›
- **S8. Back up before migrations** yourself; don't rely on automated backups.
- **S9. On uncertain outcomes, don't retry sends or deploys blindly**; establish what happened first.
- **S10. Confirm the target before touching a server:** host, environment, checkout, and the container labels actually running. A container name alone doesn't prove the environment.
- **S11. Shared machines:** respect machine reservations (e.g. "don't use mac6 till 12 PM"); wrap heavy builds in the host's heavy-job semaphore where one exists.

## 6. Secrets

- **X1. Never print, echo, cat, log or commit secrets** (`.env*`, `*.p8`, keystores, service-account JSON, tokens, `auth.json`). Use them by reference; refer to variable *names* in reports.
- **X2. Read credential files literally** (no `eval`); never put secrets in prompts, memory, docs, Slack or third-party queries (incl. Context7).
- **X3. If a secret is exposed** (log, commit, chat), say so immediately and flag it for rotation.

## 7. Stack defaults (new work; existing repos follow their own stack)

- **K1. Python: `uv` only** (no pip, venv, requirements.txt, bare `python`).
- **K2. JS/TS: Bun.** New web frontends: Bun + Vite + TanStack. No Next.js for new projects.
- **K3. Mobile: Flutter/Dart.**
- **K4. Local stacks run in Docker.**
- **K5. Identity: `ecitizen_id`** is the only user identifier across KAILASA systems.
- **K6. No explanatory code comments, in any repo.** Knowledge goes in AGENTS.md, rules, skills and docs. Only functional comments allowed (license headers, pragmas/lint directives, generated-file markers). ‹decided 2026-11-20›

## 8. Communication

- **C1. Plain, simple language.** Lead with the outcome; technical detail only when asked.
- **C2. Status answers come from live state** (process, log, CI, deploy) with grounded time estimates.
- **C3. Ask with numbered options** answerable by number; recommend one.
- **C4. Design work: show several polished options** and get visual approval before building. Quality over speed.

## 9. Documentation and memory

- **M1. One fact, one home.** Repo knowledge lives in that repo's `AGENTS.md` (+ `CLAUDE.md` = `@AGENTS.md`), nested module files and `docs/`. Never put repo-specific coaching in this global file. → `playbooks/repo-docs.md`
- **M2. Keep docs true.** Update docs in the same PR as the behaviour change. Delete stale instructions instead of adding contradicting ones.
- **M3. Memory entries carry Why + How to apply,** are dated, and are deleted when superseded. Never store secrets or time-bound state (build numbers, model IDs, PR status) as permanent facts.
