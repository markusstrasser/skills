---
name: youtube-transcript
description: "Use when: YouTube/podcast transcript via yt-dlp for cite or corpus. Transcript-only — NOT video analysis."
user-invocable: true
argument-hint: "<youtube-url-or-id> [topic-prefix]"
allowed-tools: [Bash, Write, Read]
effort: low
---

# YouTube Transcript

Lightweight wrapper around `yt-dlp` for transcript-only fetching.

## Install check

```bash
command -v yt-dlp || uvx yt-dlp --version  # uvx works without install
```

## Fetch transcript (no video)

```bash
# Replace VID with the 11-char YouTube ID or full URL
VID="Pxyl2O_AxPk"
OUT_DIR="sources/<topic>/transcripts"
mkdir -p "$OUT_DIR"

uvx yt-dlp \
  --skip-download \
  --write-auto-sub --write-sub \
  --sub-lang "en.*" \
  --sub-format "vtt/srv1/best" \
  --convert-subs vtt \
  -o "${OUT_DIR}/%(id)s-%(title)s.%(ext)s" \
  "https://www.youtube.com/watch?v=${VID}"
```

## VTT → plain text

VTT has timestamps and cue tags that make grep noisy. Strip them:

```bash
# Simple: drop all lines that look like timestamps, cues, or metadata
awk '
  /^WEBVTT/ { next }
  /^NOTE/ { next }
  /^[0-9]+$/ { next }
  /-->/ { next }
  /^$/ { next }
  { gsub(/<[^>]*>/, ""); print }
' "${OUT_DIR}/${VID}"-*.en.vtt | awk '!seen[$0]++' > "${OUT_DIR}/${VID}.txt"
```

The `!seen[$0]++` dedupes the rolling-captions pattern (same line repeated with growing cue).

## Citation convention

After staging, cite as:
```
[SOURCE: youtube.com/watch?v=<VID>, transcript at sources/<topic>/transcripts/<VID>.txt]
```

Include approximate timestamp in-quote if the claim is time-specific:
```
At ~01:23:45, [speaker] claims X [SOURCE: <VID> transcript, line N]
```

## Known failures

- **Auto-captions unavailable** — some channels disable them. yt-dlp errors out; download the audio and run `transcribe <file>`.
- **Age-restricted / members-only** — requires `--cookies-from-browser chrome`.
- **"Sign in to confirm you're not a bot"** — YouTube answered this without cookies from this machine on 2026-11-05. Do not add cookies: they run as Markus's Chrome login, the yt-dlp wiki warns that account use risks a temporary or permanent ban, and he declined an agent YouTube account that day. Get the 360p file with the `mweb` client and transcribe it on-device, one video at a time:

  ```bash
  yt-dlp --extractor-args 'youtube:player_client=mweb' -f 18 -o "${OUT_DIR}/${VID}.%(ext)s" "https://www.youtube.com/watch?v=${VID}"
  transcribe "${OUT_DIR}/${VID}.mp4"   # writes ${VID}.json beside the input
  ```

  A 5-minute video took 52 s in total. This is speech recognition, not captions, so names and technical terms can come out wrong; check any quote against the audio before citing it. Delete the video file afterwards.
- **Live streams** — transcript not finalized until stream ends.
- **Very long videos (>6h)** — .vtt can be 2-5MB. Strip before committing to git.

## Evidence

- `sources/jre-2460-rachel-wilson-transcript.txt` + `.en.vtt` — one-off, no reusable pattern.
- Future: any podcast/video citation in research memos.
