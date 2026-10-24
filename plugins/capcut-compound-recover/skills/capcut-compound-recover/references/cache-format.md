# Cache format and recovery limits

Read this when a compound cache does not open normally or the helper rejects it.

## What was verified

A preprocessed compound can have a main `<id>_video.mp4` cache plus an `.alpha.mp4` mask. The main cache may use a BDVE trailer and periodic byte masking, even though its filename ends in `.mp4`. This does not mean the media is missing or that the cache needs a new render.

BDVE Type 1 uses a single-byte XOR key over selected byte ranges. At absolute file offset `p`, the byte is masked when `p % step < length`. The intervening bytes remain unchanged. The key can be inferred from the masked ISO BMFF header; the helper never reads CapCut's key stores or account data.

The trailing `bdve` box identifies a `crpt` child with type/version fields and a SHA-256 digest of `big_endian_u32(step) + big_endian_u32(length) + u8(key)`. Footer size and box boundaries must be checked before using those fields. The observed footer version may be 3 even though its cryptor type is 1.

If the digest does not match a known profile, sample-table offsets can provide masked/plain header observations. The bounded solver finds parameters consistent with those observations and accepts them only when the exact footer digest matches. It then checks all classified video sample headers, restores the byte ranges, remuxes with `-c copy`, and performs a full video/audio decode. No guessed output is published.

## Failure modes

- **Full-file XOR:** headers may open, but originally unmasked slices become corrupted.
- **Whole-packet XOR:** NAL headers can look valid while picture data breaks where a masking boundary crosses a packet.
- **Probe-only validation:** duration and dimensions can be correct despite broken frames. Treat a nonempty FFmpeg error log as failure.
- **Alpha mask:** white or grayscale video is not the composition, even if it has an AAC audio stream.
- **Incomplete render:** changing size or modification time means CapCut is still writing; wait for preprocessing to finish.
- **Unsupported layout:** the helper handles ordinary ISO BMFF media and BDVE Type 1 with a usable preliminary sample table and a period up to 5,000,000 bytes. A different cryptor, mixed preliminary `moov`, or no solvable sample table requires native export or a separately verified decoder.

## Provenance

The BDVE footer, parameter digest, known profiles, and constraint approach were adapted from [CapCut Cache Recover's cryptor](https://github.com/pikadexofc/capcut-cache-recover/blob/3107af9f3314dcc004759d8763ee9e1adfc89962/capcut_cache_recover/cryptor.py), reviewed at commit `3107af9f3314dcc004759d8763ee9e1adfc89962`. Its MIT notice is retained in [NOTICE.txt](NOTICE.txt).

The packaged helper independently adds project discovery, bounded-memory payload restoration, source-change checks, strict full-decode validation, atomic publication, and hash-verified destination copies. No upstream GUI, installer, telemetry, or network execution is bundled.
