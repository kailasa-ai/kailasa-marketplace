# Deploy and production playbook

Load before any deploy, migration, production query or user-reaching action.

**Access varies by person.** If you don't have access to the target (Dokploy, the host, the store console, the database), get as far as "prepared" (branch, backup plan, exact steps) and hand off to someone who does (W0).

## Approval matrix
| Action | DEV | PROD |
|---|---|---|
| Deploy | Agent, on its own | Agent, **after an explicit yes** in this conversation |
| Read-only DB query | Yes | Yes, in a read-only transaction |
| DB write / migration | Yes | Yes + backup first + yes |
| Bulk send (email/SMS/push/WhatsApp) | Test audience only | Yes required; freeze the audience first |
| Store upload (TestFlight/Play internal) | n/a | After the user approves in the simulator |
| Go live / production track / withdraw a build | n/a | Separate explicit yes |
| DNS | Whoever owns the domain | Whoever owns the domain |

An approval covers the action it was given for, not the next one.

## Deploy steps (S6, S7)
1. Confirm the target: host, environment, Dokploy project, and the running containers' compose labels (S10).
2. Take the host deploy lock named in the repo's docs, if there is one. If someone else holds it, stop and ask.
3. Back up the database yourself if there is any migration (S8).
4. Deploy through Dokploy (or the repo's documented mechanism) from `main` (PROD) or `dev` (DEV). Use SSH only for what Dokploy can't do, and say so.
5. No merges to `main` while a deploy is running.
6. Stop services gracefully (`docker stop -t 90`); never `kill`.
7. Never run a second instance of a stateful worker against PROD (e.g. a second dhi).
8. After the deploy: watch logs, health and a real user flow; report what you observed and for how long.
9. Release the lock.

## Production data
- Diagnose with `SET default_transaction_read_only=on`.
- Never restore or copy prod user data into DEV, test runners or evals. If a DEV eval must be prod-derived, blank the telemetry keys (Langfuse/Sentry).
- On an uncertain outcome (timeout during a send or deploy), find out what happened before retrying (S9).

## Changing env or config
A restart doesn't always pick up changes: changed env vars need the container recreated (`docker compose up -d <svc>`), and some gateways need Stop → Start. Check the repo's runbook for the exact operation.
