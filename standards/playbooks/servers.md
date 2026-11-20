# Servers playbook

Only for people who have been given access to these hosts. Load when working on one of them.

**Access is not assumed.** The aliases below are the names used in the owner's `~/.ssh/config`; yours may differ or not exist. Check `~/.ssh/config` and test with `ssh -o BatchMode=yes <alias> true`. If you have no access, stop and tell the requester. Never look for, copy or guess credentials or keys.

Audit basis: read-only SSH snapshot of 2026-11-20. Re-verify before acting (S10). Approval and deploy steps live in `deploy-and-prod.md` (S6-S11); this file only adds per-host facts.

## Fleet table

| Alias | OS / user | Role | Environment | Deploys via | Biggest danger |
|---|---|---|---|---|---|
| kapali | Ubuntu 24.04 / root | SOMA app, gateway, data stores | PROD | Dokploy (controller not located), PR to `main` | Second Dhi/worker on prod Redis/Postgres; killing Dhi |
| causing | Ubuntu 24.04 / root | Causing Portal, Celery, eCitizen mirror | PROD | `tasks/deploy_release_worktree.sh` (release worktrees from `master`) | Running `deploy.sh`, compose `down`, or `manage.sh` restore/migrate/eCitizen ops |
| npedia | Ubuntu 20.04 / root | Public wiki, auto-upload stack, preview site | PROD + preview mixed | `/opt/n-pedia/deploy/*.sh` scripts; `npm run docker:prod` for auto-upload | Pointing tests/dev at the prod wiki DB; replacing the public bind from the preview checkout |
| kailasa-calls | Ubuntu 24.04 / root | Calls API, worker, demo host | Unverified (demo enabled, real telephony capable) | Local Compose in `/opt/kailasa-calls/deploy` | Placing real calls or provisioning tenants/numbers as a test |
| erp | Ubuntu 22.04 / root | Shared dev, UAT, media processing | DEV / UAT (some stacks unclassified) | Local Compose per repo (no Dokploy) | Recreating from missing compose/bind paths; pruning the shared daemon |
| omkar | Ubuntu 20.04 / root | eCitizen apps, rehearsal, Calls DEV, Store DEV, shared services | Mixed (DEV + hosted prod-like services) | Dokploy-labelled projects + separate Compose dirs | Host-wide Docker cleanup or bulk restart; touching shared DBs or live gateway |
| mac5 | macOS 26 / hetzner | iOS/Flutter build + device QA, NTV media workers | build/QA | Local scripts, launchd | Interrupting the NTV queue; overwriting signing assets |
| mac6 | macOS 27 / hetzner | V4 simulator, judge-tour, Flutter QA | build/QA | Local builds, launchd | Touching `~/YOUTUBE-BACKUP-DO-NOT-TOUCH`; stopping someone else's run |

## kapali
- SOMA production: 23 containers across 17 Compose projects (web, nadi, dhi, gateway, vidyakosha, jm, suchana, medha, jnanalaya, upanishads, subscriptions, arogya, bots, plus db/qdrant/neo4j/redis stacks). Gateway `soma-gateway` publishes 80/443.
- Each project is a Dokploy tree: Git root `/etc/dokploy/compose/<project>/code`, compose file in a subdirectory (e.g. `code/dhi`, `code/web`, `code/db/postgres`). Compose files are `docker-compose.yml`.
- Deploy: PR to `main`, then Dokploy deployment. No Dokploy/Traefik container runs locally; the controller location is unverified.
- Lock: exclusive directory `/root/soma-deploy.lock` with an `owner` record (absent at audit). Also check for an active Dokploy deploy. No merges to `main` during a deploy. Watch Dhi 15 minutes afterwards (durable-run completion, 5xx, worker recovery errors).
- Never attach a second Dhi or candidate worker to prod Redis/Postgres (it can claim real chat jobs). Never kill or force-remove Dhi; authorized stop uses `docker stop -t 90`.
- Protect Postgres, Redis, Neo4j, Qdrant and their backup/healthwatch services.
- Checkout HEAD differs from live image revision for web, dhi, vidyakosha. Redis checkout sits on `nadi/dev`, not `main`. `/opt/soma` exists without a Git checkout.

## causing
- Causing Portal PROD: 19 containers, Compose project `causing_portal_prod` (two frontends, Django/Celery, Postgres, Redis, backups, eCitizen mirror, OAuth2 Proxy, MCP server). Container Caddy publishes 80/443; OAuth2 Proxy 4180.
- Main checkout `/opt/causing_portal` on `master`. Running containers mostly point at detached release worktrees under `/opt/causing_portal/.deploy-worktrees/release-<sha12>/deploy-prod`; three point at `/opt/causing-domain-release/deploy-prod`; eCitizen mirror and Redis point at the main checkout's `deploy-prod`.
- Deploy: operator entrypoint `tasks/deploy_release_worktree.sh` (default `origin/master`; clean detached worktree; calls `deploy-prod/deploy.sh`; migrations gated on encrypted, verified DB/media backup). Its dry run still stages files.
- No host-wide deploy lock was found. Establish serialization with the owner before any release.
- `.claude/rules/prod-safety.md` reserves production-changing ops for humans (superseded by S6 only with an explicit yes); AGENTS.md forbids pushing to `master`.
- Never run `deploy.sh`, compose `down`/`down -v` in either deploy dir, `manage.sh` restore/clean/update/migrate or eCitizen apply/bootstrap/replay/reconcile, snapshot promotion, or the restore script. Keep the eCitizen confirmation and risk-acknowledgment gates intact.
- NocoDB and ClamAV containers reference release dirs that no longer exist. Do not recreate them without an approved replacement release; preserve volumes.

## npedia
- Public Nithyanandapedia wiki (`n-pedia-v2` project, `/opt/n-pedia`), preview overlay, production auto-upload stack (`npedia-auto-upload`, `/root/kpedia/npedia-auto-upload`), plus unlabelled `np-visual-app`, `npbuntest`, `np73db`.
- Host `caddy.service` (config in `/etc/caddy`) routes `nithyanandapedia.org` to the `v2org` container, the unclutch dev domain to `v2root`, and the image domain to the upload API on port 3000. Postgres instances bind loopback only.
- Checkouts: `/opt/n-pedia` on a feature branch (`feat/wiki-parity-frontend`), `/opt/n-pedia-oneness-design` on a feature branch, auto-upload on `main`. Public bind is `/opt/n-pedia-v2-root`; preview bind is `/opt/n-pedia-v2-preview`; neither has a Git HEAD.
- Wiki deploy: `/opt/n-pedia/deploy/deploy-v2-root.sh` with `docker-compose.v2.yml` and env file `/opt/n-pedia/.env.v2`. All wiki deploy scripts share the `flock` at `/run/lock/n-pedia-deploy.lock` (waits up to an hour). Build in `oven/bun:1.4.4`.
- Auto-upload: `docker-compose.prod.yml`, `npm run docker:prod`; no lock confirmed.
- Never point tests or dev tools at the prod wiki DB, never replace the public bind from the preview checkout, never run volume-removing commands on either live stack. Keep the auto-upload worker disabled in any test copy.

## kailasa-calls
- Calls API (`calls-server`), `calls-worker`, `demo-host`, Postgres, Redis and a container Caddy under project `kailasa-calls`, working dir `/opt/kailasa-calls/deploy` (files `docker-compose.yml` + `docker-compose.demo.yml`). Host Caddy fronts it.
- Deploy: local Compose; no Dokploy labels, no app systemd unit, no host lock, no agent docs on the host. Follow `docs/OPERATIONS.md` and `docs/PEOPLE-MIGRATIONS.md` in the repo.
- `/opt/kailasa-calls` is a detached HEAD; image labels report a different revision. Other checkouts (`/opt/kailasa-calls-pr9-review`, `/opt/kailasa-calls-releases/<sha>`, `/opt/portal-live`, `/opt/causing_portal`) are not behind running containers.
- Treat as real-telephony capable. Never place a call, mutate carrier/webhook config, provision a tenant or number, or enable recording/transcription as a test. Keep dev and prod provider resources separate.
- The older preview DB's migration history needs reconciliation; do not redeploy or reconcile it as part of unrelated work.

## erp
- Shared DEV/UAT/media host, 52 containers: Forms UAT (`forms_uat_3778708`, disposable `deploy-preview`), Kailasa Social DEV, a local SOMA stack, kailasa-ai, refugee-bot, NTV local CMS DB, eCitizen dev DBs, yarc, Ollama and Nimble (systemd).
- Checkouts under `/root/kailasa/*` and `/opt/dev/*`, often on feature branches. No Dokploy (`/etc/dokploy` absent); no host lock (`/root/soma-deploy.lock` absent).
- NTV: deploys belong to the user; restarting the live transcoder ends streams. Social: use separate test identities and never write to the `ntv-ott` R2 bucket. Causing `prod-safety.md` applies to `/opt/dev/causing_portal`.
- Stale labels: Social proxy/MinIO/Mailpit, the three Punya containers, and `npedia-mongodb-prod` point at missing compose files or bind paths. Never recreate them from those paths.
- `npedia-mongodb-prod` and the local SOMA stack are not classified; do not assume DEV. A DEV job name is not permission to change its data.

## omkar
- Mixed host, 96 containers: eCitizen per-app Dokploy projects (`/etc/dokploy/compose/<name>/code`), an unlabelled `ecrehearsal-slice2-*` rehearsal stack, Calls DEV (`/opt/kailasa-calls-dev/deploy`), Store DEV (`/home/kailasa-store-v3`), and shared services (Bitwarden, Authentik, Forgejo, Portainer, RustDesk, WordPress sites, 18_kingdoms).
- Swarm active (no services). Dokploy controller unverified; no local Dokploy container. Systemd: `nimble`, `archive-review`, `ccrelay`.
- eCitizen: production reconciliation needs explicit acknowledgement plus a direct session advisory lock (`AGENTS.md:106`). After route changes do a deliberate gateway stop/start. Confirm the project's route and DB before acting; rehearsal names give no authority over shared DBs or the live gateway.
- Store: demo seeds/tests on disposable data only; import, deploy, commits and publication need separate authorization.
- The Agno project's compose file is missing; `uskfoundation-ste` compose lives under Portainer's bind (`/home/portainer/portainer_data/compose/83`).
- Never run host-wide Docker cleanup or a bulk restart.

## mac5
- Shared iOS/Flutter build and device-QA Mac (user `hetzner`) that also runs NTV media workers via launchd (`ai.ntv.metal-queue`, `ai.ntv.cached-audio-repair`) from `~/ntv-subtitles`; also zoom-translate agents.
- Entry points: `~/ios_build.sh`, `~/v4_interim_build.sh`, worktree `~/wt-v4-interim` (detached). Run `tool/gen.sh` before analysis/builds; `legacy/` is reference-only; give an explicit device ID for the watch companion.
- No Docker CLI on the SSH PATH, no deploy lock or heavy-job semaphore found. Confirm the ref and simulator target before building.
- Never interrupt the NTV queue, reboot, reload shared agents, overwrite signing assets, or upload a store build without approval.

## mac6
- Shared V4 simulator, judge-tour and Flutter QA Mac (user `hetzner`); Xcode at `/Applications/Xcode-27.1.0.app`. Host Caddy via launchd.
- Entry points: `~/tour.sh`, QA/tour worktrees under `~/wt/` (e.g. `qa-v4-82049f46b`), main checkout `~/code/ask_nithyananda_app-rebuild-v4`.
- `com.v4.window.stop` / `.resume` launchd jobs exist (trigger unverified); check the reservation window before heavy jobs.
- iOS signing rules are in the repo AGENTS.md: preserve the signed IPA and embedded profile. Simulator testing and store upload are separate actions.
- Never touch `~/YOUTUBE-BACKUP-DO-NOT-TOUCH`, erase simulators or QA artifacts, or stop someone else's run. A result file's existence is not a test outcome.

## Machine notes
- **Owner's Mac.** Heavy caches and Docker data live on `/Volumes/X10Pro` (symlinked from `~/.mac-offload`-style paths). If an install or build fails, check the disk is mounted and run `df` first. Flutter builds can fill the internal disk.
- **mac5 / mac6.** Shared Flutter/iOS build and QA Macs. Respect owner reservations (e.g. "don't use mac6 till 12 PM"). No heavy-job semaphore was found on either at audit; if one exists, wrap heavy builds in it, and check running Xcode/Flutter/simulator processes first (S11). Keep worktrees and simulator targets isolated.

## Fleet-wide gotchas
- **Running containers can reference deleted dirs.** causing (NocoDB, ClamAV), erp (Social, Punya, Mongo) and omkar (Agno) run from compose/bind paths that no longer exist. Before removing any old worktree or release dir, check `com.docker.compose.project.working_dir` and bind sources of running containers. Never recreate from a missing file.
- **Release worktrees back prod.** causing's `.deploy-worktrees/release-*` and `/opt/causing-domain-release` serve live containers; omkar `/opt/soma_v2*` copies may too. Do not clean up without checking labels.
- **Checkout HEAD is not what's running.** Image revision labels differ from on-disk HEAD on kapali, kailasa-calls and npedia; some bind trees have no Git at all. Compare the image revision label before using a SHA as evidence.
- **Branch surprises.** Several prod checkouts sit on feature or detached branches (kapali Redis, npedia, erp, omkar). Treat unexpected branches as a stop point.
- **Env changes need recreate, not restart.** Use `docker compose up -d <svc>`; some gateways need a deliberate stop/start.
- **Dokploy labels do not prove a controller.** kapali, omkar and kailasa-calls show Dokploy-style paths with no Dokploy container locally. Verify how a project is really deployed.
- **Locks differ per host.** `/root/soma-deploy.lock` (kapali), `/run/lock/n-pedia-deploy.lock` (npedia), advisory DB lock (omkar eCitizen). causing, kailasa-calls, erp and the Macs have none: agree on serialization first.
- **Container names do not prove environment** (`npedia-mongodb-prod` runs on erp). Confirm host, project and labels (S10).
- **Diagnose read-only.** Use field-specific `docker inspect --format`, never full inspect or resolved compose config (they leak env). Report secret locations or variable names only.
- **No shared-daemon prune, bulk restart, `down -v`, or smoke-test sends/dials/migrations.** On an unclear outcome, find out what happened before retrying (S9).
