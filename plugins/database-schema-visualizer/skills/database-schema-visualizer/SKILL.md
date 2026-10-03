---
name: database-schema-visualizer
description: 'Build an interactive, explorable database schema map — not a static
  diagram. Use when asked to "visualize the schema", "show me the DB schema", "see
  the tables", or to turn a Prisma/Diesel/SQL schema or a design doc into something
  navigable. Produces a structured schema.json plus a generated HTML page with a
  pan/zoom canvas, per-table detail, search and cluster filtering, published as an
  artifact.

  '
allowed-tools: Read, Write, Edit, Bash, Grep, Glob, Artifact
version: 2.0.0
license: MIT
tags:
- database
- diagrams
- visualization
compatibility: Claude Code
---

# Database Schema Visualizer

## What "visualize the schema" means here

Not a mermaid `erDiagram` in a markdown file. Mermaid is a picture: it does not scale past
~15 tables, cannot be searched, and shows column comments only if they fit. What is wanted is
an **explorable map** — a canvas you can pan, zoom, filter and click into, where every column,
type, owner and note is reachable without editing the source.

Mermaid stays useful for one focused cluster inside a document. It is not the deliverable
when someone says "let me see the schema".

## The two-file shape

Always split data from rendering:

1. **`schema.json`** — the machine-readable schema, checked into the repo next to the design
   docs. This is what a human edits.
2. **A generator script** — reads `schema.json`, emits a single self-contained HTML file.
   Never hand-edit the HTML; it is a build output and belongs in `.gitignore`.

Then publish the HTML with the Artifact tool.

If the project already has a generated docs page (see the identity-v4 setup in
`ecitizen-web`), add the map as a tab in that page rather than creating a second artifact.
Scattered artifacts are the problem this is meant to solve.

## schema.json

```jsonc
{
  "schema": "identity",
  "clusters": [
    { "key": "spine", "name": "Account spine", "round": "1",
      "colour": "#0f6e5e", "status": "specified" }
  ],
  "tables": [
    {
      "name": "users",
      "cluster": "spine",
      "state": "new | reshaped | unchanged",
      "note": "why this table exists, in one or two sentences",
      "columns": [
        { "name": "id", "type": "int4", "key": "PK", "null": false,
          "owner": "ecitizen", "state": "new", "sensitive": false,
          "ref": "other_table.column", "note": "why this column is here" }
      ],
      "dropped":  [{ "name": "password_hash", "why": "…" }],
      "movedOut": [{ "name": "city, state, zip_code", "to": "person_address" }]
    }
  ],
  "relations": [
    { "from": "person_email", "to": "person", "kind": "n-1",
      "label": "person_id", "optional": false }
  ],
  "layout": { "users": { "x": 2, "y": 0 } }
}
```

- `layout` is grid coordinates — column index and order within the column, **not pixels**.
  Heights are measured in the browser; guessing them produces overlapping boxes.
- `owner` matters whenever more than one system writes the table. Colour it in the detail
  panel; it is usually the single most useful fact on the page.
- `sensitive: true` marks anything excluded from projections, exports or logs. Badge it.
- `state` on both tables and columns is what makes a *change* legible rather than just a
  schema — before/after is the usual reason someone asked.

## What the page must do

Build these. Each exists because leaving it out makes the map decorative:

| Feature | Why |
|---|---|
| Pan, wheel zoom, **Fit** button | 20+ tables never fit at 100% |
| Draggable tables | The generated layout is a starting point, not a truth |
| **Click a table to focus** — dim unrelated tables, light its edges | The whole point: "what touches this?" |
| Detail panel: every column, type, null, key, owner, note | The canvas cannot show 16 annotated columns legibly |
| Clickable relations in the detail panel | Walking the graph beats hunting the canvas |
| Search across table **and column** names | "where is `verified_at`?" is the most common question |
| Cluster/domain filter chips | Isolating one round or one bounded context |
| **Keys only** toggle | Dense schemas need a structural view |
| **Full screen** toggle | A canvas in a 700px column is unusable |
| Empty-canvas click clears focus, Esc exits | Otherwise the user is stuck in a focused state |

### Interaction traps that actually bite

- **`setPointerCapture` retargets later events.** After capturing on the stage, `pointerup`
  reports the *stage* as `e.target`, never the node — so `e.target.closest('.node')` returns
  null and click-to-focus silently does nothing. Record the pressed element on `pointerdown`
  and read it back on `pointerup`. This is the single most likely bug in this build.
- **Distinguish click from drag** by accumulated movement (`< 4px` is a click), not by
  whether a `pointermove` fired.
- **`preventDefault()` on `pointerdown`, and set `user-select: none` on the stage.**
  Otherwise the browser starts a native text selection over the canvas and fires
  `pointercancel` part-way through, so the pan dies mid-gesture. It reads as "dragging works
  sometimes", and it is worst where there is the most empty canvas — full screen.
- **End the drag when `e.buttons === 0` in `pointermove`.** A `pointerup` released outside an
  uncaptured stage never arrives, and the canvas keeps panning with nothing held down.
  Wrap `setPointerCapture` in try/catch — it throws if the pointer is already gone — and
  ignore any button but the left one.
- **Normalise wheel delta before zooming.** A mouse notch reports ~100, a trackpad 1-10, and
  `deltaMode` 1 and 2 report lines and pages. Scale exponentially
  (`k * Math.exp(-delta * 0.0006)`) and cap one event at a few percent, or the same code that
  feels right on a mouse rockets past the whole schema on a trackpad.
- **Full screen: use a fixed overlay, not `requestFullscreen`.** Artifacts render in an
  iframe where the Fullscreen API is commonly blocked. Toggle a class with
  `position: fixed; inset: 0`, lock `body` scroll, restore both on Esc *and* on tab switch —
  a stranded overlay over another tab looks like a broken page.
- **Measure node heights after insertion** and lay out columns by accumulating those
  measurements. Fixed row-height math breaks the moment one table has more columns.
- **Recompute edges on every drag, filter and layout change.** Anchor to node rectangles;
  pick the side (left or right) by comparing centre-x so the curve never crosses its own box.
- Zoom around the pointer: `state.x = px - (px - state.x) * (k2 / k1)`. Zooming around the
  origin feels broken.

### Rendering

Plain DOM nodes plus one SVG layer for edges, both inside a single transformed `.world`
element. No library. D3/cytoscape are not on the artifact CDN allowlist for anything but
scripts, and hand-rolled is ~250 lines with no version pinning.

## Live schemas: parse, never transcribe

For a schema that already exists, read it from the source of truth at build time —
`prisma/schema.prisma`, migrations, or `information_schema` — and never hand-copy it into a
diagram. A transcription is wrong the first time someone runs `prisma migrate dev`, and
nothing tells you it is wrong.

When a project has many schemas, one canvas with a schema picker beats one tab each.

Prisma-specific notes, all of which bite:

- Field-level `@map("user_id")` and table-level `@@map("users")` are different attributes;
  matching `@map` naively finds `@@map` too. Keep both the Prisma field name and the mapped
  column name — relations reference the *field*, the canvas shows the *column*.
- Only the side of a relation carrying `@relation(fields: [...])` is the foreign key. Drawing
  both sides doubles every edge.
- `@db.VarChar(20)` is a better type label than `String`.
- Verify the parse before trusting it: `grep -c '^model '` and `grep -c '@relation(fields'`
  per file, and check those numbers against what the parser produced. It takes a minute and
  it is the only thing standing between you and a confident, wrong picture.

## Sections beat a flat list

Once there is more than a handful of pages, a flat sidebar hides the thing a reader most
needs to know: whether a page is a **specification** that code will be written from, or a
**tracking** page that is still being argued about. Group the nav — spec, tracking,
reference — and name each tab for what it contains, not for what it was called while it was
being written.

## Drift is the real failure

If `schema.json` restates something a design document also states in prose, the two **will**
disagree within a week, and the pretty page becomes the lie people trust.

Make the generator compare them and exit non-zero on a mismatch. Then verify the check reads
real data — a regex that silently matches nothing passes every time. Print what it extracted
once and confirm the count.

If the schema is live rather than designed, generate `schema.json` from the source of truth
(`prisma/schema.prisma`, `\d+` output, `information_schema`) instead of hand-writing it.

## Order of work

1. Find the source: Prisma schema, migrations, design docs, or a live database.
2. Write `schema.json`. Include every column with its note — a map without notes is a
   diagram, and they already have one.
3. Write or extend the generator. Add the drift check.
4. Run it. Confirm placeholders were substituted and the JSON embedded.
5. Publish with the Artifact tool. Redeploy the same file path to keep the URL.
6. Say plainly what is unverified. Canvas geometry cannot be confirmed from the HTML source;
   if the page was not opened in a browser, say so rather than implying it was checked.

## Reference implementation

`ecitizen-web`: `scripts/build-identity-v4-doc.mjs` renders
`build-specs/identity-v4/schema.json` (23 tables) as the landing tab of a multi-document
workspace page, with a `PostToolUse` hook that regenerates on every edit to that folder.
