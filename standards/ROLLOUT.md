# Cleanup plan: bring repos and machines in line with the master standard

Found during the 2026-11-20 audit (Mac + 8 servers). Nothing has been changed yet.

## A. Global config (Mac + every server)
1. `~/.claude/CLAUDE.md` is missing and `~/.codex/AGENTS.md` is empty (0 bytes) → symlink both to `standards/` via an install script.
2. `~/.claude/rules/context7.md` → folded into W7; delete after install, along with the duplicate `skills-disabled/find-docs`.
3. `~/.claude/settings.json` → `autoMode.environment` holds an ask_nithyananda_app-only paste (secret paths, "no Node on this machine") → move it into that repo's `.claude/settings.json`.
4. `~/.codex/rules/default.rules` → 53 auto-accumulated allow rules; ~30 are one-off `zsh -lc` commands that read `server.env` passwords → prune them to generic prefixes.
5. `~/.codex/config.toml` → ~25 trust entries for throwaway `~/Documents/Codex/<date>/…` dirs → remove them.
6. Leftovers to remove: `skills/*/SKILL.md.orig`, 12 single-member `~/.claude/teams/session-*`.
7. Memory: delete the self-marked stale entries (`dev-server-deploy-procedure`, `claude-builds-until-nov16`, `only-humans-deploy-rule`, `db-schema-map`, `runpod-access`, `v4-pace-is-inference-artifact`). Merge the duplicate memory dirs `~/Documents/Projects/{soma-v2,causing-portal}` into the X10Pro ones. Trim the soma_v2 `MEMORY.md` index (17 KB, at risk of truncation).
8. `history.jsonl` contains a pasted live session token → rotate that token.

## B. Repos: adopt `AGENTS.md` + one-line `CLAUDE.md` (`@AGENTS.md`)
Already correct: causing_portal (with a CI line-budget gate), rc-android, kailasa-store-v3 storefront, the V4 app worktrees under `~/wt`.
To convert:
- **ask_nithyananda_app**: the AGENTS.md is a stale find-and-replace clone ("Codex.ai/code", `.Codex/`, 7 languages). The 250-line CLAUDE.md has route trees that belong in `docs/`, and a release skill that says "this machine is Windows" and uses the dead `mac-build` alias.
- **soma_v2**: the two root files have drifted (AgentOS vs FastAPI, `.Codex/rules`, a missing `dhi/AGENTS.md`). `dhi/CLAUDE.md` is 47 KB (146 KB on one branch) and should move to docs. The **PROD deploy rules exist only on branches and on `~/ref/soma_v2`, not in the main checkout** → merge them. The kapali `/home/soma_v2` "Only humans deploy" line → replace with S6.
- **book_editor**: 41 KB of defect post-mortems → `docs/`.
- **book_generator**: `settings.local.json` allows `pip install` and has Windows miniconda paths, which contradicts the uv-only rule.
- **oneness-ui**: `.cursorrules` is stale (#F97316 vs #FF7200) → delete it.
- **social-publishing-app**: the CLAUDE.md says "not a git repo yet" and contains a real admin email.
- **N-Pedia** (`npedia:/opt/n-pedia/CLAUDE.md`): still documents Payload/Astro/pnpm, but the live stack is Bun/TanStack.
- **causing_portal** (on the servers): an old `/root/kailasa/causing_portal/CLAUDE.md`, plus GEMINI/QWEN stubs that describe MySQL/Keycloak. The "Never use Opus" and "never push without permission" lines → remove them (D2, G3).
- **lokh-sabha, nandi-rs**: Windows-path allow rules in `settings.local.json`.
- **No agent docs at all**: jnanalaya, kailasa-calls, nandi-rs, nithyananda-tv*, punya-portal, GemOCR, swamiji-tts. Create a minimal AGENTS.md for each from `templates/repo-AGENTS.md`.

## C. Branch migration (G0: dev → main)
- causing_portal, N-Pedia: `master` → `main` (+ create `dev`).
- ask_nithyananda_app: `central/dev` → `dev`.
- ecitizen and others on `main` only → add `dev`.
- SOMA uses merge commits → switch to squash (G5).

## D. Disk clutter (ask before deleting)
- About 40 `ask_nithyananda_app-*` dirs, 6 `soma_v2-*` full clones, 134 soma_v2 worktrees, and about 18 jnanalaya validation dirs on X10Pro.
- Old release worktrees on `causing` and `/opt/soma_v2-dev-*` copies on `omkar`. **Caution:** some of these still back running prod containers.

## E. Rules moved out of the master (2026-11-20) → put them here
- "iOS first, Android in a final phase" → ask_nithyananda_app AGENTS.md
- "Prefer soft-delete for user data" → nandi-rs / ecitizen AGENTS.md
- "Heavy caches and Docker data on /Volumes/X10Pro; check mount + df when installs fail" → playbooks/servers.md (machine notes: the owner's Mac)
- "User-facing copy says Agent, never skill" → dropped entirely (owner: no need to keep)

## F. Server questions for the owner
- Fleet deploy policy: causing (operator-run Compose from `master`), npedia (scripts), kailasa-calls and erp (local Compose) differ from "Dokploy + `main`". Which exceptions are official, and who owns each?
- kapali: where is the Dokploy controller, and is the Redis checkout on `nadi/dev` intentional?
- kapali: which release records explain checkout HEAD differing from live image revisions (web, dhi, vidyakosha)?
- causing: which manifest is authoritative across the eight live working dirs, and what serializes operator releases?
- causing: what should replace the missing NocoDB and ClamAV release dirs, and what is the recovery procedure?
- npedia: who owns `np-visual-app`, `npbuntest` and `np73db`, and are they still needed?
- npedia: which release record ties the public wiki bind tree to its image and current checkout?
- kailasa-calls: is it demo/QA only or does it carry production tenants, and is the dormant eCitizen upstream on port 7456 intentional?
- kailasa-calls: which release is authoritative, and what serializes deploys there?
- erp: are the local SOMA stack and `npedia-mongodb-prod` DEV, staging or prod, and where are the compose sources for Mongo, old Social and Punya?
- omkar: which Dokploy controller manages the labelled projects, which eCitizen projects take production traffic, and what is the redeploy source for the Agno project?
- mac5/mac6: what enforces reservations and heavy-job serialization, and what triggers the mac6 `com.v4.window.stop/resume` jobs?
