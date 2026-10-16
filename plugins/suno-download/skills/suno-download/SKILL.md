---
name: suno-download
description: Download a Suno song (suno.com/song/<id> link, a bare clip id, or a cloudfront .m4a clip URL) as a playable MP3 using the public clip API and ffmpeg. Use whenever the user gives a Suno link or clip id, or a d2lwuy8qc234o3.cloudfront.net/1/clip/<id>.m4a URL, and wants the audio downloaded, converted, or made playable.
---

# Download a Suno song as MP3

## Key facts (verified 2026-10-16)

- The `.m4a` at `https://d2lwuy8qc234o3.cloudfront.net/1/clip/<id>.m4a` (the `media_urls` entry, `m4a-opus`) is encrypted. It has no `ftyp`/`moov` header and ffmpeg fails with "moov atom not found". Do not try to repair it.
- `https://studio-api-prod.suno.com/api/clip/<id>` is public and needs no login. Its `audio_url` is `.../api/forbidden`, but `video_url` (`https://cdn1.suno.ai/<id>.mp4`) is a normal downloadable MP4 with the full audio track.
- `https://cdn1.suno.ai/<id>.mp3` returns 403. Do not use it.
- So: download the mp4, then extract the audio with ffmpeg. No browser or cdpgate capture is needed.

## Steps

1. Get the clip id: the UUID in `suno.com/song/<id>` or in the cloudfront URL.
2. Run the script (ffmpeg path defaults to `C:\Users\Auspicious\Videos\yt-dlp\ffmpeg.exe`):

   ```
   bash ~/.claude/skills/suno-download/scripts/suno-dl.sh <clip-id-or-url> [out-dir]
   ```

   Default out-dir is `~/Downloads/clip`. Output is `<Title>.mp3` (libmp3lame, VBR q2, about 190 kbps) plus the source `<id>.mp4`.
3. Report the output path and duration.

## If it fails (empty `video_url`, mp4 403, or not a valid mp4): capture playback

Verified 2026-10-16: some clips have `video_url: ""`. The only served file is the encrypted cloudfront `.m4a`, which the page decrypts into a `blob:` MSE `<audio>` element. netrec cannot see the decoded audio. So record it in-page:

1. Needs cdpgate + cdpg + Vivaldi (browser CDP gateway). If `cdpg profiles` says cdpgate is not running, start the `cdpgate` tray app and wait ~8s.
2. Run in the background (real time, about the song length):

   ```
   bash ~/.claude/skills/suno-download/scripts/suno-capture.sh <clip-id-or-url> [out-dir]
   ```

   It approves profile `Default` + `suno.com` (override with `SUNO_PROFILE`), opens a NEW tab (never navigates the user's tabs), clicks Play, injects `scripts/suno-inject.js` (`audio.captureStream()` + `MediaRecorder`, opus webm, restarts from 0), waits for `ended`, pulls the base64 back in chunks, converts to MP3 with ffmpeg, closes the tab.
3. Several songs can run in parallel, one script per clip. Don't pause the tab.
4. Output is a re-encode of the stream (opus to mp3), so slightly lossy. Mention that.

Don't use netrec for the song file. `cdn-o.suno.com/sil-100.mp3` is just silence priming.
Only extract audio the user is entitled to download.
