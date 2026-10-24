#!/usr/bin/env python3
"""Locate CapCut compounds and restore verified standalone MP4s locally.

BDVE format/constraint approach adapted from pikadexofc/capcut-cache-recover.
See ../references/NOTICE.txt for the upstream MIT notice.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile


MAX_STEP = 5_000_000
KNOWN_PROFILES = ((1_022_554, 311_610), (102_303, 89_230))
CHUNK = 4 * 1024 * 1024


class RecoveryError(RuntimeError):
    pass


def fingerprint(path: Path) -> tuple[int, int]:
    stat = path.stat()
    return stat.st_size, stat.st_mtime_ns


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(CHUNK), b""):
            digest.update(block)
    return digest.hexdigest()


def run(command: list[str]) -> str:
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode:
        raise RecoveryError(f"{command[0]} failed: {result.stderr[-4000:].strip()}")
    # Error-level diagnostics are failures even if a tolerant decoder exits 0.
    if result.stderr.strip():
        raise RecoveryError(f"{command[0]} reported errors: {result.stderr[-4000:].strip()}")
    return result.stdout


def probe(path: Path) -> dict:
    return json.loads(run([
        "ffprobe", "-v", "error", "-show_format", "-show_streams", "-of", "json", str(path)
    ]))


def footer(path: Path) -> dict | None:
    size = path.stat().st_size
    if size < 4:
        return None
    with path.open("rb") as stream:
        stream.seek(-4, 2)
        length = int.from_bytes(stream.read(4), "big")
        if not 16 <= length <= min(size, 65536):
            return None
        start = size - length
        stream.seek(start)
        data = stream.read(length)
    if data[4:8] != b"bdve":
        return None
    if int.from_bytes(data[:4], "big") != length:
        raise RecoveryError("Invalid BDVE box size")
    cursor = 8
    while cursor + 8 <= len(data):
        child_size = int.from_bytes(data[cursor:cursor + 4], "big")
        kind = data[cursor + 4:cursor + 8]
        if child_size < 8 or cursor + child_size > len(data):
            raise RecoveryError("Invalid BDVE child box bounds")
        if kind == b"crpt":
            if child_size < 48:
                raise RecoveryError("Truncated BDVE cryptor metadata")
            payload = data[cursor + 8:cursor + child_size]
            cryptor_type, version = struct.unpack(">II", payload[:8])
            if cryptor_type != 1:
                raise RecoveryError(f"Unsupported BDVE cryptor type: {cryptor_type}")
            return {"start": start, "size": length, "version": version,
                    "digest": payload[8:40]}
        cursor += child_size
    raise RecoveryError("BDVE footer has no cryptor metadata")


def parameter_digest(step: int, length: int, key: int) -> bytes:
    return hashlib.sha256(struct.pack(">IIB", step, length, key)).digest()


def classify_headers(source: Path, packets: list[dict], key: int) -> list[tuple[int, bool]]:
    observations = []
    table = bytes(value ^ key for value in range(256))

    def plausible(prefix: bytes, size: int) -> bool:
        return (len(prefix) == 5 and 0 < int.from_bytes(prefix[:4], "big") <= size - 4
                and prefix[4] & 0x80 == 0 and 1 <= prefix[4] & 31 <= 23)

    file_size = source.stat().st_size
    with source.open("rb") as stream:
        for sample in packets:
            if "pos" not in sample or "size" not in sample:
                continue
            pos, size = int(sample["pos"]), int(sample["size"])
            if pos < 0 or size < 5 or pos + size > file_size:
                continue
            stream.seek(pos)
            raw = stream.read(5)
            plain = plausible(raw, size)
            masked = plausible(raw.translate(table), size)
            # Skip ambiguous headers, including boundaries crossing the prefix.
            if plain != masked:
                observations.append((pos, masked))
    return observations


def solve(observations: list[tuple[int, bool]], target: bytes, key: int,
          max_step: int = MAX_STEP) -> tuple[int, int]:
    for step, length in KNOWN_PROFILES:
        if parameter_digest(step, length, key) == target:
            return step, length
    if not observations or not any(not masked for _, masked in observations):
        raise RecoveryError("Insufficient masked/plain sample observations; use native export")
    # Early samples span several periods on typical caches. Retain later samples
    # for verification; the digest, rather than a plausible picture, is decisive.
    stride = max(1, len(observations) // 128)
    constraints = list(dict.fromkeys(observations[:128] + observations[::stride][:128]
                                    + [item for item in observations if not item[1]][:16]))
    key_byte = bytes([key])
    for step in range(1, max_step + 1):
        low, high = 1, step
        for position, masked in constraints:
            remainder = position % step
            if masked:
                low = max(low, remainder + 1)
            else:
                high = min(high, remainder)
            if low > high:
                break
        if low > high:
            continue
        prefix = step.to_bytes(4, "big")
        for length in range(low, high + 1):
            if hashlib.sha256(prefix + length.to_bytes(4, "big") + key_byte).digest() == target:
                if not all((pos % step < length) == masked for pos, masked in observations):
                    raise RecoveryError("Digest matched but sample classifications disagree")
                return step, length
    raise RecoveryError(f"Unsupported cache: no verified period <= {max_step}; use native export")


def preliminary_copy(source: Path, destination: Path, size: int, key: int) -> None:
    table = bytes(value ^ key for value in range(256))
    with source.open("rb") as src, destination.open("wb") as dst:
        remaining = size
        while remaining:
            block = src.read(min(CHUNK, remaining))
            if not block:
                raise RecoveryError("Source was truncated while reading")
            dst.write(block.translate(table))
            remaining -= len(block)


def restore(source: Path, destination: Path, size: int, step: int, length: int, key: int) -> None:
    table = bytes(value ^ key for value in range(256))
    with source.open("rb") as src, destination.open("wb") as dst:
        remaining = size
        while remaining:
            block = src.read(min(step, remaining))
            if not block:
                raise RecoveryError("Source was truncated while restoring")
            count = min(length, len(block))
            dst.write(block[:count].translate(table))
            dst.write(block[count:])
            remaining -= len(block)


def verify_media(path: Path, expected: dict) -> dict:
    actual = probe(path)
    expected_video = next((s for s in expected["streams"] if s["codec_type"] == "video"), None)
    video = next((s for s in actual["streams"] if s["codec_type"] == "video"), None)
    if not expected_video or not video:
        raise RecoveryError("No video stream in recovered media")
    for field in ("width", "height", "codec_name", "nb_frames"):
        if expected_video.get(field) is not None and video.get(field) != expected_video[field]:
            raise RecoveryError(f"Recovered video {field} does not match cached render")
    numerator, denominator = video.get("avg_frame_rate", "0/1").split("/")
    fps = float(numerator) / float(denominator) if float(denominator) else 0
    tolerance = max(0.002, 1 / fps) if fps else 0.034
    if abs(float(actual["format"]["duration"]) - float(expected["format"]["duration"])) > tolerance:
        raise RecoveryError("Recovered duration does not match cached render")
    expected_audio = [s for s in expected["streams"] if s["codec_type"] == "audio"]
    actual_audio = [s for s in actual["streams"] if s["codec_type"] == "audio"]
    if len(expected_audio) != len(actual_audio):
        raise RecoveryError("Audio stream count changed during recovery")
    run(["ffmpeg", "-nostdin", "-v", "error", "-xerror", "-i", str(path),
         "-map", "0:v:0", "-map", "0:a?", "-f", "null", "-"])
    return actual


def publish(staged: Path, output: Path, overwrite: bool) -> None:
    if overwrite:
        os.replace(staged, output)
    else:
        # Same-filesystem hard link publishes atomically and refuses collisions,
        # including a destination that appeared after the initial existence check.
        os.link(staged, output)
        staged.unlink()


def copy_verified(source: Path, directory: Path, overwrite: bool) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    output = directory / source.name
    if output.resolve() == source.resolve():
        return source
    if output.exists():
        if sha256_file(output) == sha256_file(source):
            return output
        if not overwrite:
            raise RecoveryError(f"Copy destination already contains a different file: {output}")
    with tempfile.TemporaryDirectory(prefix=".capcut-copy-", dir=directory) as work:
        staged = Path(work) / source.name
        shutil.copy2(source, staged)
        if sha256_file(staged) != sha256_file(source):
            raise RecoveryError("Destination copy hash mismatch")
        publish(staged, output, overwrite)
    return output


def recover(source: Path, output: Path, *, overwrite: bool = False,
            copy_to: Path | None = None) -> dict:
    source = source.expanduser().resolve()
    output = output.expanduser().absolute()
    if not source.is_file():
        raise RecoveryError(f"Source does not exist: {source}")
    if source.name.lower().endswith(".alpha.mp4"):
        raise RecoveryError("This is the alpha mask; select the main _video.mp4 cache")
    if source == output.resolve():
        raise RecoveryError("Source and output must differ; never overwrite the CapCut cache")
    if copy_to and (copy_to.expanduser() / output.name).resolve() == source:
        raise RecoveryError("Additional copy would overwrite the source cache")
    if output.suffix.lower() != ".mp4":
        raise RecoveryError("Choose a .mp4 output filename")
    if output.exists() and not overwrite:
        raise RecoveryError(f"Output already exists: {output}; use --overwrite only if authorized")
    for binary in ("ffmpeg", "ffprobe"):
        if not shutil.which(binary):
            raise RecoveryError(f"{binary} is required on PATH")
    output.parent.mkdir(parents=True, exist_ok=True)
    before = fingerprint(source)
    metadata = footer(source)
    with tempfile.TemporaryDirectory(prefix=".capcut-recover-", dir=output.parent) as work:
        work = Path(work)
        params = None
        if metadata:
            with source.open("rb") as stream:
                key = stream.read(1)[0]
                stream.seek(4)
                header = stream.read(4)
            if bytes(value ^ key for value in header) != b"ftyp":
                raise RecoveryError("Unsupported masked container header; use native export")
            params = next(((step, length) for step, length in KNOWN_PROFILES
                           if parameter_digest(step, length, key) == metadata["digest"]), None)
            if params is None:
                preliminary = work / "preliminary.mov"
                preliminary_copy(source, preliminary, metadata["start"], key)
                try:
                    # Fatal-only logging is intentional here: the preliminary
                    # payload is not decoded and may contain unmasked slices.
                    result = subprocess.run([
                        "ffprobe", "-v", "fatal", "-select_streams", "v:0", "-show_packets",
                        "-show_entries", "packet=pos,size", "-of", "json", str(preliminary)
                    ], capture_output=True, text=True)
                    if result.returncode:
                        raise ValueError("unreadable preliminary table")
                    packets = json.loads(result.stdout)["packets"]
                    observations = classify_headers(source, packets, key)
                    params = solve(observations, metadata["digest"], key)
                except (ValueError, KeyError) as exc:
                    raise RecoveryError("No usable preliminary sample table; use native export") from exc
                preliminary.unlink()
            restored = work / "restored.mov"
            restore(source, restored, metadata["start"], *params, key)
            media = restored
        else:
            media = source
        expected = probe(media)
        staged = work / "validated.mp4"
        run(["ffmpeg", "-nostdin", "-v", "error", "-i", str(media), "-map", "0:v:0",
             "-map", "0:a?", "-c", "copy", "-movflags", "+faststart", str(staged)])
        actual = verify_media(staged, expected)
        source_hash = sha256_file(source)
        if before != fingerprint(source):
            raise RecoveryError("Source changed during recovery; wait for preprocessing to finish")
        output_hash = sha256_file(staged)
        publish(staged, output, overwrite)
    video = next(s for s in actual["streams"] if s["codec_type"] == "video")
    report = {
        "source": str(source), "output": str(output), "source_sha256": source_hash,
        "output_sha256": output_hash, "size_bytes": output.stat().st_size,
        "duration_seconds": float(actual["format"]["duration"]),
        "width": video["width"], "height": video["height"],
        "audio_streams": sum(s["codec_type"] == "audio" for s in actual["streams"]),
        "reencoded": False, "full_decode": "passed", "source_unchanged": True,
        "bdve": {"step": params[0], "length": params[1], "digest_verified": True,
                 "footer_version": metadata["version"]} if params else None,
    }
    if copy_to:
        report["copy"] = str(copy_verified(output, copy_to.expanduser(), overwrite))
    return report


def project_roots() -> list[Path]:
    home = Path.home()
    candidates = [
        home / "Movies/CapCut/User Data/Projects/com.lveditor.draft",
        home / "Library/Containers/com.lemon.lvoverseas/Data/Movies/CapCut/User Data/Projects/com.lveditor.draft",
    ]
    if os.environ.get("LOCALAPPDATA"):
        candidates.append(Path(os.environ["LOCALAPPDATA"]) / "CapCut/User Data/Projects/com.lveditor.draft")
    return list(dict.fromkeys(p.resolve() for p in candidates if p.is_dir()))


def list_projects(roots: list[Path], name: str | None) -> list[dict]:
    found = []
    seen = set()
    for root in roots:
        for project in sorted(root.expanduser().iterdir()):
            if not project.is_dir() or project.resolve() in seen:
                continue
            seen.add(project.resolve())
            meta = {}
            try:
                meta = json.loads((project / "draft_meta_info.json").read_text(encoding="utf-8"))
            except (OSError, ValueError):
                pass
            project_name = meta.get("draft_name", project.name)
            if name and name not in (project.name, project_name):
                continue
            caches = []
            for cache in sorted((project / "Resources/combination").glob("*_video.mp4")):
                stat = cache.stat()
                caches.append({"path": str(cache), "combination_id": cache.name[:-10],
                               "size_bytes": stat.st_size, "modified_ns": stat.st_mtime_ns})
            found.append({"name": project_name, "path": str(project),
                          "project_id": meta.get("draft_id"),
                          "duration_us": meta.get("tm_duration"), "caches": caches})
    return found


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    locator = commands.add_parser("list", help="Locate projects and main compound caches")
    locator.add_argument("--root", action="append", type=Path, help="Custom com.lveditor.draft root")
    locator.add_argument("--project", help="Exact project folder or display name")
    recovery = commands.add_parser("recover", help="Restore, validate, and copy a compound cache")
    recovery.add_argument("--input", required=True, type=Path)
    recovery.add_argument("--output", required=True, type=Path)
    recovery.add_argument("--overwrite", action="store_true")
    recovery.add_argument("--copy-to", type=Path, help="Additional destination directory")
    recovery.add_argument("--report", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "list":
            roots = args.root or project_roots()
            report = {"roots": [str(p) for p in roots],
                      "projects": list_projects(roots, args.project)}
        else:
            protected = {args.input.expanduser().resolve(), args.output.expanduser().resolve()}
            if args.copy_to:
                protected.add((args.copy_to.expanduser() / args.output.name).resolve())
            if args.report and args.report.expanduser().resolve() in protected:
                raise RecoveryError("Report must not replace the input or output media")
            report = recover(args.input, args.output, overwrite=args.overwrite, copy_to=args.copy_to)
            if args.report:
                args.report.expanduser().write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report, indent=2))
        return 0
    except (RecoveryError, OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
