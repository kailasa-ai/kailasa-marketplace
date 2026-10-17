# Publishing and presentation

These details describe the nithyananda.ai implementation established in October 2026. Verify the current repository instructions, API documentation, and component behavior before changing or publishing. Adapt to the actual system; do not assume another site uses the same API.

## Existing website

- Production origin: `https://nithyananda.ai`; deployed branch: `main`.
- Conversation CTA: `https://ask.nithyananda.ai`.
- Main uses the site's content store and Puck editor. The obsolete Payload template on `master` is not the deployed site. Do not prescribe Payload authentication or migrations for this publishing workflow.
- Admin dashboard: `/studio`. Publishing requires an approved admin using the site's existing authentication.
- Author: `Nithyananda AI`. AI authors use `/hero/ai_logo.png`; human authors retain their own identity.
- Article kicker: `a blog by KAILASA's Nithyananda AI`.
- Blog index heading: `Blogs`; no visible subtitle.
- Approved homepage/social-card tagline: `Avatar's Intelligence reaching you through Artificial Intelligence`.
- Homepage hero has one Google Play download button. Do not restore “Other platforms” or “See all features” there. This is a homepage rule, not an instruction to put a download button inside every article.

## Prepare the content

Read the repository's `docs/blog-api.md` and local instructions when available. For structural code questions use the repository's preferred code-intelligence tools; a text-only article update does not require a frontend redesign.

Prepare:

- title, assertive excerpt, author, tags, and the intended status;
- structured `bodyMarkdown` with working links;
- `sources`, each with `title` and full HTTP(S) `url`;
- SEO title, description, canonical URL, and image where available;
- a real publication date for a new article, or the unchanged original date for a revision.

The existing article renderer prefers `bodyMarkdown`; `body` is its legacy paragraph fallback. When updating both representations, remove rejected text from both. Keep the source library intact.

## API workflow

1. Use an authorized authenticated session. The established session cookie is `askni_session`; it is not a Payload JWT. A WordPress cookie, Cloudflare clearance cookie, or CSRF cookie alone does not grant publishing access.
2. Keep session values and CSRF tokens in runtime memory or an appropriate secret store. Never commit credentials, put them in the skill, print them to logs, or include them in published artifacts.
3. For a revision, `GET /api/page/blog-<slug>` returns an envelope whose `data` is the complete Puck document. Save a content-only backup and edit the requested fields. Preserve unrelated blocks, IDs, metadata, publication date, canonical URL, sources, and other authors' work.
4. Obtain a fresh CSRF token with `GET /api/auth/csrf` in the same session. Preserve its `askni_csrf` cookie and send the returned token in `x-csrf-token` for writes when enforcement is enabled. A cookie-aware client is preferable.
5. For a new post, `POST /api/posts` accepts the simplified article input. Draft is the default; use `status: "published"` only when publication is authorized. Supply `bodyMarkdown` and `sources` where supported. Drafts require the database in this implementation.
6. For an existing post, `PUT /api/page/blog-<slug>` publishes the **complete Puck document**, not the simplified creation input. `PATCH` saves a draft where supported. Check the current endpoint contract rather than interchanging these bodies.
7. Check the actual response. Success is normally HTTP 201 for creation or HTTP 200 with `success: true` for an update. A 401 or 403 requires valid approved access; request that access rather than retrying indefinitely or bypassing the admin gate. Resolve 409 conflicts by reading the existing document instead of overwriting it blindly.
8. Read the public article and index after publishing. Verify the revised text, removed text, excerpt, working links, source coverage, authorship, and CTA. The content publication path should revalidate the article, index, and sitemap.
9. If a tracked content seed exists, update it to match the approved revision so a later file-mode deployment does not restore old copy. Commit and push only within the user's authorized repository/branch scope. Respect local changes and normal required checks.

Use the publishing API when requested. Do not detour into browser automation for a write the API supports. Fetch a fresh document before making a later revision; an older local seed can overwrite intervening changes.

## SEO and social checks

- Set a useful, specific title and description. Keep the visible standfirst, listing excerpt, and metadata in the same editorial voice. Do not leave an old “SPH's teachings” intermediary description in the share preview.
- Preserve established slugs and canonicals during text edits. Use the production origin for absolute canonical, source-independent share-image, and sitemap URLs.
- Check Open Graph and Twitter metadata, image dimensions and accessibility text, and the generated image itself. In the current site, the default social card is generated by `src/app/opengraph-image.tsx`; changing article text does not change text drawn into that image.
- Include appropriate article and breadcrumb structured data. Nithyananda AI is an organization/brand author in this site's schema; do not invent a human author profile or credentials.
- Published, indexable, self-canonical posts belong in the blog index and sitemap. Draft previews should remain noindex. Do not promise indexing or ranking.
- Calculate reading time from article text, excluding hidden reference lists and URL strings. Preserve the original publication date on revisions; use an actual modification date where the platform supports it.
- Social services can cache a previous share preview. Verify the origin's current metadata/image before attributing an old cached card to a failed edit.

## Rendering and code changes

Use the existing safe Markdown renderer and scoped reading styles. Check semantic headings, visible link styling, safe external links, responsive tables, keyboard access, and no horizontal overflow on phone and desktop widths. Preserve the approved navigation, logo, byline, credit, and closing CTA.

A copy-only API update does not require code deployment. A renderer, homepage-button, or generated-social-image change does. Run checks appropriate to any code change and report what is live separately from what has only been pushed for deployment. Do not request deployment approval when the user has already authorized deployment; do not claim deployment from a Git push alone.
