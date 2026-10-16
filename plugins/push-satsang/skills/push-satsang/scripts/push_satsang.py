#!/usr/bin/env python3
"""Pre-chunk and push satsang transcript file(s) into the SPH_Satsangs_v3 vidyakosha dataset.

Usage:
    push_satsang.py <file1> [file2 ...] [--tag TAG ...] [--max-chars N]

Each file is word-boundary split into ~max-chars sections, wrapped in a markdown
doc (H1 = file stem, H2 per section), and pushed via create-by-file with
indexing_technique=granthatree. The source path is recorded in raw_push_state.json
so Synth_Data_01/push_raw_transcripts.py never re-pushes (and duplicates) it.
"""
import argparse
import json
import os
import sys
import time
from pathlib import Path

import requests

BASE = "https://api7.nithyananda.ai/vidyakosha"
KEY = os.environ["VIDYAKOSHA_API_KEY"]
DATASET_ID = "0b837696-fe9c-4a45-af55-6cc954e5f6c0"  # SPH_Satsangs_v3
PUSH_STATE = Path("/home/jovyan/Synth_Data_01/raw_push_state.json")


def split_by_words(text, max_chars):
    words = text.split(" ")
    chunks, current, current_len = [], [], 0
    for w in words:
        wl = len(w) + 1
        if current_len + wl > max_chars and current:
            chunks.append(" ".join(current))
            current, current_len = [], 0
        current.append(w)
        current_len += wl
    if current:
        chunks.append(" ".join(current))
    return chunks


def build_markdown(stem, src_path, max_chars):
    raw = src_path.read_text(encoding="utf-8-sig")  # strips BOM if present
    full_text = " ".join(raw.split())
    sections = split_by_words(full_text, max_chars)
    lines = [f"# {stem}", ""]
    for i, sec in enumerate(sections, 1):
        lines += [f"## Section {i}", "", sec, ""]
    return "\n".join(lines), len(sections)


def push_doc(session, name, text, tags):
    resp = session.post(
        f"{BASE}/v1/datasets/{DATASET_ID}/documents/create-by-file",
        files={"file": (f"{name}.md", text.encode("utf-8"), "text/markdown")},
        data={
            "indexing_technique": "granthatree",
            "process_rule": json.dumps({"mode": "automatic"}),
            "tags": json.dumps(tags),
            "name": name,
        },
        timeout=90,
    )
    resp.raise_for_status()
    return resp.json().get("id")


def verify(session, doc_id, settle_seconds=12):
    time.sleep(settle_seconds)
    resp = session.get(f"{BASE}/v1/datasets/{DATASET_ID}/documents/{doc_id}", timeout=30)
    resp.raise_for_status()
    d = resp.json()
    return d.get("processing_status"), d.get("error")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("files", nargs="+", help="Source transcript file paths")
    ap.add_argument("--tag", action="append", default=["sph", "satsang"], help="Repeatable; defaults to sph, satsang")
    ap.add_argument("--max-chars", type=int, default=2200)
    args = ap.parse_args()

    session = requests.Session()
    session.headers["Authorization"] = f"Bearer {KEY}"
    session.headers["User-Agent"] = "curl/8.5.0"  # default UA gets 403'd on some endpoints

    state = json.loads(PUSH_STATE.read_text()) if PUSH_STATE.exists() else []

    for f in args.files:
        src = Path(f).resolve()
        if str(src) in state:
            print(f"skip (already pushed): {src.name}")
            continue
        if not src.exists():
            print(f"skip (not found): {src}", file=sys.stderr)
            continue

        stem = src.stem
        md_text, n_sections = build_markdown(stem, src, args.max_chars)
        print(f"{stem}: {n_sections} sections, {len(md_text)} chars")

        doc_id = push_doc(session, stem, md_text, args.tag)
        print(f"  pushed {doc_id}")

        status, error = verify(session, doc_id)
        print(f"  status={status} error={error}")
        if status == "error":
            print(
                "  WARNING: left in raw_push_state as pushed; if this is a "
                "segments_pkey collision, delete the doc, remove this path from "
                "raw_push_state.json, and rerun.",
                file=sys.stderr,
            )

        state.append(str(src))
        PUSH_STATE.write_text(json.dumps(state, indent=2))


if __name__ == "__main__":
    main()
