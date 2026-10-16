---
name: push-satsang
description: Pre-chunk and upload satsang transcript file(s) from Synth_Data_01/SPH_Recent_Transcripts into the SPH_Satsangs_v3 vidyakosha dataset.
---

# Push Satsang

Uploads satsang transcripts into the vidyakosha `SPH_Satsangs_v3` dataset
(id `0b837696-fe9c-4a45-af55-6cc954e5f6c0`), word-boundary pre-chunking each
file into ~2200-char markdown sections before pushing via `create-by-file`
with `indexing_technique=granthatree`. Use this when asked to add, sync, or
pre-chunk satsang transcript file(s) — a new month's folder, a single file,
etc. — from `Synth_Data_01/SPH_Recent_Transcripts/...`.

For small plain-text files where pre-chunking isn't explicitly requested,
`Synth_Data_01/push_raw_transcripts.py` (the existing full-folder sync, which
relies on the backend's own automatic chunker) is simpler and still correct —
prefer pre-chunking only when asked, or for large/non-Latin-script files
where the backend's automatic chunker is more likely to choke.

Requires the `VIDYAKOSHA_API_KEY` environment variable (a vidyakosha API key
with write access to the dataset) to be set before running.

Run:

```bash
VIDYAKOSHA_API_KEY=... python3 scripts/push_satsang.py <file1> [file2 ...]
```

The script word-splits each file, wraps it in a markdown doc, pushes it,
verifies the resulting `processing_status`/`error` after a short settle
delay, and records the source path in
`/home/jovyan/Synth_Data_01/raw_push_state.json` so the plain-text sync
pipeline never re-pushes (and duplicates) the same file. All requests set
`User-Agent: curl/8.5.0` — the default UA gets 403'd on some endpoints.

## Known pitfall: do not `/retry` a just-pushed document

If a document errors with `duplicate key value violates unique constraint
"segments_pkey"` shortly after being pushed, it's because a `/retry` call
hit it while its original enqueue job was still live, creating a duplicate.
Never call `/retry` on a document created in the last few minutes. If it
happens anyway: `DELETE /v1/datasets/{dataset_id}/documents/{doc_id}`,
remove the source path from `raw_push_state.json`, and rerun the script —
a freshly created document gets a new deterministic ID and won't collide.
