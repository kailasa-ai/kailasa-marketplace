---
name: capcut-compound-recover
description: Find local CapCut projects and recover their preprocessed compound clips as playable MP4s. Use when a user asks where a compound clip was cached, to copy an already rendered clip, or to recover a cache that ordinary players cannot open.
---

# CapCut compound clip recovery

Find the user's project, match its compound clip to its cached render, and produce a verified standalone copy. Prefer the existing render so CapCut's compositing, masks, backgrounds, logos, speed changes, and audio survive intact.

## Locate the clip

Use Python 3.10+, FFmpeg, and FFprobe. The helper uses only Python's standard library and runs locally; no API keys or media uploads are needed.

```sh
python3 "${CLAUDE_PLUGIN_ROOT}/skills/capcut-compound-recover/scripts/capcut_cache.py" list --project "PROJECT NAME"
```

The locator checks the usual macOS and Windows project roots. Supply `--root "/custom/Projects/com.lveditor.draft"` if the user stores projects elsewhere. A missing result does not prove no project exists: inspect CapCut's configured project folder or search the filesystem for the named folder before asking the user.

Inspect `draft_meta_info.json` for the exact project name and ID. Inspect the active `draft_info.json` and `materials.drafts[].combination_id` to match the named compound clip to:

```text
<project>/Resources/combination/<combination_id>_video.mp4
```

Nested compound drafts can be embedded in `materials.drafts[].draft`; inspect `subdraft/` and `Timelines/` when the active draft does not explain a candidate. Match identifiers and duration, not filenames alone. If several compounds are plausible, report their names and durations and clarify which one to copy.

The `.alpha.mp4` sibling is an opacity mask, often entirely white. It can contain audio and valid dimensions but is not the finished color video. Do not deliver it as the clip.

## Recover and copy

```sh
python3 "${CLAUDE_PLUGIN_ROOT}/skills/capcut-compound-recover/scripts/capcut_cache.py" recover \
  --input "/project/Resources/combination/ID_video.mp4" \
  --output "/destination/Project-compound.mp4"
```

The helper accepts a normal video or a supported BDVE Type 1 cache. It validates the cache's parameter digest, restores the periodic byte masking, remuxes video and audio with stream copy, and decodes the complete result before publishing it. See [the format notes](references/cache-format.md) when investigating an unsupported cache or a recovery failure.

- Preserve the project and source cache. Work outside CapCut's project folders. A source file that changes during processing must be retried after preprocessing finishes.
- Choose a readable output name and the user's requested destination. Existing destinations are refused unless the user authorized replacement; use `--overwrite` for that case. Publication is atomic, after validation.
- For an additional copy, use `--copy-to "/destination/directory"`. The helper checks SHA-256 equality. Avoid silently overwriting a different file.
- Use `--report "/work/recovery.json"` if a detailed provenance and validation report is useful. Keep reports, media, absolute user paths, and cache identifiers out of the published skill repository.

Do not assume a full-file XOR, a fixed key, or a packet-by-packet transformation works. Those approaches can produce a readable container with corrupted pictures. A successful probe or extracted frame is insufficient; the helper requires a clean full decode and matching duration, dimensions, frame count, and audio stream presence.

## Finish

Inspect representative opening, middle, and closing frames and compare the layout with the project cover or preview. Report the playable output link, original cache location, duration, dimensions, audio presence, and whether recovery reused the render without re-encoding.

If there is no completed cache, ask CapCut to preprocess the compound clip or use its native export workflow when app control is available and the task authorizes rendering. If the cache format is unsupported, report the exact limitation and offer native export. Do not approximate the composition from its JSON or present a failed recovery as a usable clip.
