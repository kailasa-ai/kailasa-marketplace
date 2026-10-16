#!/usr/bin/env bash
# Fallback when the mp4 route 403s / video_url is empty: record the decoded audio
# from the player in a Vivaldi tab (via cdpgate) and convert to MP3. Real time (~song length).
# usage: suno-capture.sh <clip-id | suno url> [out-dir]
# prereq: cdpgate running (tray). Profile/domain approval is requested here.
set -euo pipefail
export LC_ALL=C.UTF-8
FFMPEG="${FFMPEG:-ffmpeg}"
PROFILE="${SUNO_PROFILE:-Default}"
P="--profiles $PROFILE --domains suno.com"
id=$(printf '%s' "$1" | grep -oiE '[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}' | head -1)
[ -n "$id" ] || { echo "no clip id in: $1" >&2; exit 1; }
out="${2:-$HOME/Downloads/clip}"; mkdir -p "$out"
tmp=$(mktemp -d)
meta=$(curl -sSf "https://studio-api-prod.suno.com/api/clip/$id")
title=$(printf '%s' "$meta" | sed -n 's/.*"title": *"\([^"]*\)".*/\1/p' | head -1)
title=$(printf '%b' "$title" | sed 's/[\/:*?"<>|]//g'); title="${title:-$id}"

cdpg approve $P --minutes 60 >/dev/null
tid=$(cdpg send Target.createTarget "{\"url\":\"https://suno.com/song/$id\"}" $P | grep -o '"targetId":"[^"]*"' | cut -d'"' -f4)
[ -n "$tid" ] || { echo "createTarget failed" >&2; exit 1; }
ev() { # ev <js-file-or-expr>  -> prints the CDP reply
  local j; j=$(uv run python -c 'import json,sys;print(json.dumps({"expression":sys.argv[1],"returnByValue":True,"userGesture":True}))' "$1")
  cdpg send Runtime.evaluate "$j" --target "$tid" $P | tail -1
}
# wait for the blob audio element (the player must have loaded the clip)
for i in $(seq 1 30); do
  sleep 2
  ev 'document.querySelector("button[aria-label*=Play i]")?.click(); [...document.querySelectorAll("audio")].some(a=>a.src.startsWith("blob:"))' | grep -q '"value":true' && break
done
ev "$(cat "$(dirname "$0")/suno-inject.js")" | grep -q started || { echo "inject failed" >&2; exit 2; }
echo "recording ~$(printf '%s' "$meta" | grep -o '"duration": *[0-9.]*' | head -1 | grep -o '[0-9.]*$')s of playback..." >&2
until ev 'String(window.__done)' | grep -q '"value":"1"'; do sleep 10; done
len=$(ev 'window.__b64.length' | grep -o '"value":[0-9]*' | cut -d: -f2)
: > "$tmp/b64"
for ((o=0; o<len; o+=400000)); do
  ev "window.__b64.slice($o,$((o+400000)))" | grep -o '"value":"[^"]*"' | sed 's/^"value":"//;s/"$//' | tr -d '\n' >> "$tmp/b64"
done
base64 -d "$tmp/b64" > "$tmp/rec.webm"
"$FFMPEG" -hide_banner -loglevel error -y -i "$tmp/rec.webm" -vn -c:a libmp3lame -q:a 2 "$out/$title.mp3"
cdpg send Target.closeTarget "{\"targetId\":\"$tid\"}" $P >/dev/null || true
rm -rf "$tmp"
echo "$out/$title.mp3"
"$FFMPEG" -hide_banner -i "$out/$title.mp3" 2>&1 | grep Duration || true
