# Verification playbook

Load before saying something works, before a PR, and before a release.

## Levels
| When | What to run |
|---|---|
| While building | Fast, focused checks: the test for the code you touched, typecheck/lint, one manual run |
| Before a PR to `dev` | The repo's standard check command, plus seeing it work in a real environment (local Docker / browser / simulator) |
| Before `dev → main`, a release or a store build | Full suite including goldens and e2e, cross-family review, deploy to DEV and use it in a browser |

## Seeing it work (V1, V2)
- Web UI: open it in a real browser (Playwright / Chrome) and screenshot it in light + dark themes and at phone width. Look at the screenshots.
- Mobile: run it on the local simulator; for a release, the user approves in the simulator before any upload (S1).
- Documents/PDF: render the pages and read them. Text extraction tools can silently drop text, so rendered images are the source of truth.
- APIs: call the real endpoint and check the response body, not just the status code.

## Honest reporting (V4, V5)
Report in this shape:
- **Done and verified:** <what> (how: command / screenshot / URL)
- **Done, not verified:** <what> (why not)
- **Not done:** <what>

Before stating a number, check what it counts, where it came from and how fresh it is. CI that didn't run, or that is known-red for unrelated reasons, is "CI not checked", never "CI passed".

## Good tests (V6)
- New regression test: break the code on purpose and confirm the test fails (mutation check).
- No assertions that can never fail; no swallowing errors to go green.
- Golden/snapshot changes: open the images and compare them before accepting.
- Check the account-switch / tenant-isolation case wherever user data is shown (the most common serious bug class).

## Long commands (V7)
Run builds and suites in the background with output to a log file; poll with bounded waits; read the exit code. Never `| tail` a long build in the foreground.
