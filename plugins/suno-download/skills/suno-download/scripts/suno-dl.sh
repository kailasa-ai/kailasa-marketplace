#!/usr/bin/env bash
# usage: suno-dl.sh <clip-id | suno url | cloudfront url> [out-dir]
set -euo pipefail
export LC_ALL=C.UTF-8
FFMPEG="${FFMPEG:-/c/Users/Auspicious/Videos/yt-dlp/ffmpeg.exe}"
id=$(printf '%s' "$1" | grep -oiE '[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}' | head -1)
[ -n "$id" ] || { echo "no clip id in: $1" >&2; exit 1; }
out="${2:-$HOME/Downloads/clip}"; mkdir -p "$out"
meta=$(curl -sSf "https://studio-api-prod.suno.com/api/clip/$id")
title=$(printf '%s' "$meta" | sed -n 's/.*"title": *"\([^"]*\)".*/\1/p' | head -1)
title=$(printf '%b' "$title" | sed 's/[\/:*?"<>|]//g'); title="${title:-$id}"
url="https://cdn1.suno.ai/$id.mp4"
curl -sSfL -o "$out/$id.mp4" "$url"
head -c 8 "$out/$id.mp4" | tail -c 4 | grep -q ftyp || { echo "not a valid mp4 from $url" >&2; exit 2; }
"$FFMPEG" -hide_banner -loglevel error -y -i "$out/$id.mp4" -vn -c:a libmp3lame -q:a 2 "$out/$title.mp3"
echo "$out/$title.mp3"
"$FFMPEG" -hide_banner -i "$out/$title.mp3" 2>&1 | grep Duration || true
