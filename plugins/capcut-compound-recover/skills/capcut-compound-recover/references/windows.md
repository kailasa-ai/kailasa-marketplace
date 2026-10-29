# Windows project discovery and export

The end-to-end recovery was tested on macOS. These are Windows operating instructions, not a claim that recovery/export has already passed on Windows. Verify each Windows run against the actual local files.

## Find the actual project path

Check the installed Python interpreter (3.10+), FFmpeg, and FFprobe. PowerShell can locate them with:

```powershell
Get-Command py, python, ffmpeg, ffprobe -ErrorAction SilentlyContinue
```

Use `py -3` below if the Python launcher is installed; otherwise use the actual Python 3 interpreter. Do not treat a Microsoft Store alias as a working interpreter without checking its version.

The helper checks this candidate when `LOCALAPPDATA` is set:

```powershell
$Candidate = Join-Path $env:LOCALAPPDATA 'CapCut\User Data\Projects\com.lveditor.draft'
Test-Path -LiteralPath $Candidate
```

CapCut's configured save location, a relocated draft folder, or a Store installation can differ. First inspect the project's folder or the project/save location shown by CapCut. If necessary, search the relevant local folder for `draft_meta_info.json` or the named project. Do not search only the macOS paths or silently conclude that the project is absent when the default candidate is missing.

Set `$ProjectRoot` to the **discovered directory containing project folders**, not to a guessed path. Use the installed plugin's script path:

```powershell
$ProjectRoot = 'D:\actual\CapCut-projects\com.lveditor.draft'
$SkillScript = Join-Path $env:CLAUDE_PLUGIN_ROOT 'skills\capcut-compound-recover\scripts\capcut_cache.py'
py -3 $SkillScript list --root $ProjectRoot --project 'PROJECT NAME'
```

The `D:\actual\...` value is a placeholder: replace it with the existing path found on that machine. If `CLAUDE_PLUGIN_ROOT` is unavailable in a manually opened shell, resolve `$SkillScript` from the installed skill's location instead of inventing a plugin path.

Read the matching project's metadata and active draft, and match `combination_id` to the main file in `Resources\combination`. Check its size and modification time to ensure preprocessing has finished. Exclude the `.alpha.mp4` mask.

## Export a normal MP4 and copy it

Use the actual cache path and the user's requested output/copy locations, with quoted Windows paths. Do not assume Downloads is on `C:` or beneath a particular username; use the folder's actual location in Explorer when it is redirected or stored elsewhere.

```powershell
$CacheFile = 'D:\actual\CapCut-projects\com.lveditor.draft\PROJECT NAME\Resources\combination\ID_video.mp4'
$OutputFile = 'D:\actual\exports\Project-compound.mp4'
$CopyDirectory = 'D:\actual\requested-destination'
py -3 $SkillScript recover --input $CacheFile --output $OutputFile --copy-to $CopyDirectory
```

Replace all placeholders with discovered/existing locations. Omit `--copy-to` when only the output is requested. Use `--overwrite` only for a user-authorized replacement. The helper restores supported cache masking, remuxes a normal MP4 with video/audio stream copy, decodes the whole output, checks its media properties, and verifies an additional copy by SHA-256. Run it on the Windows machine, not just against a copied Windows path from macOS.

After recovery, inspect representative frames and confirm the exported MP4 plays with audio using an available local player or media inspection tools. Verify duration, dimensions, frame count, and the requested destination. A located cache, readable header, or successful copy alone does not establish a correct Windows export.

If the cache is absent, unfinished, or unsupported, use CapCut's native preprocess/export workflow when available and authorized. Verify the actual exported file with FFprobe, a full FFmpeg decode, and a hash check after copying. If native app control or Windows validation is unavailable, state the specific limitation rather than claiming a successful Windows render.
