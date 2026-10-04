---
title: "PeerTube: \"Transcoding Failed\" After Upload or Import"
slug: peertube-transcoding-failed
meta_description: "Videos import and transcoding fails, with no automatic retry. Memory kills, duration mismatches, and how to re-trigger jobs from the admin panel."
updated: October 2026
cluster: round 14 (tech) — Chocobozzz/PeerTube GitHub issues
competition: LOW
---

# PeerTube: "Transcoding Failed" After Upload or Import

The first thing to know, because it changes how you work: **PeerTube does not automatically retry failed transcoding jobs.** A failure is permanent until you re-trigger it, which is why a handful of failures becomes a backlog.

```
Administration → System → Jobs → filter: failed
```

That list, filtered to `video-transcoding` and `video-import`, is your worklist.

## 1. Read the job's error

Each failed job has an error field. The useful ones:

**`Killed`** — out of memory. The ffmpeg process was OOM-killed.

```bash
dmesg -T | grep -iE 'oom|killed process' | tail
docker stats --no-stream
```

Transcoding 1080p needs 2–4 GB; 4K wants considerably more, and PeerTube may run several jobs concurrently. Reduce concurrency before adding RAM:

```yaml
# config/production.yaml
transcoding:
  enabled: true
  threads: 2
  concurrency: 1
  resolutions:
    '144p': false
    '480p': true
    '720p': true
    '1080p': true
    '1440p': false
    '2160p': false
```

`concurrency: 1` and `threads: 2` on a modest server is the difference between a working instance and a permanent queue of failures.

**`Output file #0 does not contain any stream`** — ffmpeg couldn't read the input. A corrupt upload, an unusual container, or a video with no video track (an audio file uploaded as a video).

**`Conversion failed`** on specific YouTube imports — the imported file is often a format or codec combination ffmpeg in your PeerTube version handles poorly. Re-import with different yt-dlp format selection, or download and upload manually.

## 2. The duration mismatch

A documented failure: `some version has not the right duration` — a 32-minute original producing a 6-minute 480p rendition. The transcode "succeeds" and produces a broken file, then the consistency check rejects it.

Causes seen in practice:

- **Variable frame rate** input (screen recordings, phone footage). Normalise before uploading:

```bash
ffmpeg -i input.mp4 -vsync cfr -r 30 -c:v libx264 -preset medium -crf 20 \
       -c:a aac -b:a 128k normalised.mp4
```

- **A broken or truncated source.** `ffprobe` will usually say:

```bash
ffprobe -v error -show_format -show_streams input.mp4 | grep -E 'duration|nb_frames'
```

- **Concatenated files** with inconsistent timestamps.

Pre-normalising problem uploads is far more reliable than fighting the server side.

## 3. Privacy changes during transcoding

A real and specific cause: a video uploaded as **private**, then changed to unlisted or public **while transcoding jobs are queued**, can fail processing — the job references a state that changed underneath it.

Rule: upload, let transcoding finish, then change privacy. For scheduled publishing use PeerTube's own "publish at" feature rather than flipping privacy manually.

## 4. File location mismatch

Reported as "video processing fails due to file location mismatch". PeerTube moves files between directories as a video progresses (`tmp` → `videos` → `streaming-playlists`). If any of those are on different filesystems with a permission or space problem, the move fails mid-job.

```yaml
storage:
  tmp: '../data/tmp/'
  bin: '../data/bin/'
  avatars: '../data/avatars/'
  videos: '../data/videos/'
  streaming_playlists: '../data/streaming-playlists/'
  redundancy: '../data/redundancy/'
```

```bash
docker exec peertube sh -c 'df -h /data; ls -ld /data/tmp /data/videos /data/streaming-playlists'
```

All of these must be writable by the PeerTube user and ideally on the same filesystem — a cross-device move is a copy, and a full `tmp` partition fails jobs that would otherwise work. Keep `tmp` with several times your largest upload free.

## 5. Re-triggering failed jobs

This is where the lack of auto-retry bites. Options:

**Per video, from the admin panel:** the video's menu offers transcoding actions — run transcoding again for a given resolution or type.

**From the CLI, which is the practical route for a backlog:**

```bash
docker exec -u peertube peertube node dist/scripts/create-transcoding-job.js -v <video-uuid>
# all videos missing HLS:
docker exec -u peertube peertube node dist/scripts/create-transcoding-job.js --generate-hls
```

For a long list, script it over the UUIDs from the failed-jobs view. There is no "retry all" button, which is the main ergonomic complaint and worth knowing before you accumulate hundreds.

## 6. Transcription failures are separate

A video can import and transcode fine while **transcription** (subtitles) fails. That's a different job type with its own dependencies (a whisper model and its runtime). A failed transcription job does not affect playback — don't let it send you down the transcoding path.

```
Administration → System → Jobs → video-transcription
```

## What not to do

- **Don't leave `concurrency` at a value your RAM can't support.** You'll fail jobs in batches.
- **Don't change a video's privacy while it's transcoding.**
- **Don't enable every resolution** on a small instance. Each is a separate transcode of the whole video.
- **Don't delete failed videos to tidy up** without checking whether the original file is still there — you may be able to re-trigger instead.

## Prevention

| Habit | Why |
|---|---|
| `concurrency: 1`, `threads: 2` on modest hardware | Most failures are resource exhaustion |
| Normalise odd sources with ffmpeg before upload | Removes the duration-mismatch class |
| Keep `tmp` on the same filesystem with ample free space | Mid-job moves stop failing |
| Check the failed-jobs view weekly | Without auto-retry, backlogs are silent |

## FAQ

**Can I disable transcoding entirely?**
Yes, and then only the original file is served — viewers need to handle that format and bitrate. Acceptable for a small, technical audience.

**Does hardware encoding help?**
PeerTube supports custom ffmpeg encoder profiles. It cuts CPU substantially; quality per bitrate is slightly worse.

**Remote runners?**
Recent PeerTube supports offloading transcoding to separate runner processes — the right answer if your web server is small.

**Import works, the video is blank.**
Transcoding produced empty renditions. Check the duration-mismatch section and re-trigger.
