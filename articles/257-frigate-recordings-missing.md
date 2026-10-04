---
title: "Frigate Not Saving Recordings After an Update? Audio Codecs and Record Presets"
slug: frigate-recordings-missing
meta_description: "'No new recording segments were created' or empty history after a Frigate upgrade. The undecodable audio stream problem, H.265, storage permissions and retention settings."
updated: October 2026
cluster: round 12 (tech) — Frigate GitHub discussions only
competition: LOW
---

# Frigate Not Saving Recordings After an Update? Audio Codecs and Record Presets

Live view works, detection works, and the recordings timeline is empty — or the log repeats **"No new recording segments were created"**.

## 1. The audio stream Frigate can't copy (most common)

Frigate's record path **copies** the camera's streams rather than re-encoding. If the camera sends audio in a codec ffmpeg can't put in the output container, the whole recording fails — video included.

Fix it by telling ffmpeg to drop audio for the record role:

```yaml
cameras:
  front:
    ffmpeg:
      output_args:
        record: preset-record-generic
```

Or keep audio but force a usable codec:

```yaml
      output_args:
        record: preset-record-generic-audio-aac
```

Cameras that send **PCM/G.711/ulaw** audio are the classic case. This single change fixes a large share of post-upgrade recording failures, because presets and defaults have changed between Frigate versions.

## 2. H.265 and what the browser can play

Two different things get confused:

- Recordings **not created** → codec/container problem on the server (above)
- Recordings created but **won't play in the browser** → your browser can't decode H.265

If the files exist on disk and the UI won't play them, switch the camera's record stream to **H.264**, or accept that playback needs a capable browser/device.

Check whether files exist at all:

```bash
docker exec frigate ls -la /media/frigate/recordings/ | tail
du -sh /media/frigate/recordings
```

No files = server side. Files present = playback side.

## 3. The record role and retention config

Frigate's recording configuration changed shape across 0.13 → 0.14 → 0.15 → 0.16. An old config can be valid YAML and still record nothing:

- The camera must have a stream with the **`record` role** assigned
- **Retention mode**: `all` keeps continuous footage; `motion`/`active_objects` keeps far less, and people read that as "nothing is being saved"
- `retain.days: 0` anywhere means nothing is kept
- Check the **config editor** in the UI — it validates and flags deprecated keys for your version

Read your version's release notes for the recording section specifically; this is the one area that keeps moving.

## 4. Storage and permissions

```bash
df -h /media/frigate
docker exec frigate touch /media/frigate/recordings/.writetest && echo writable
```

- **Disk full** — Frigate will also prune aggressively and look like it keeps nothing
- Wrong **ownership/UID** on a bind mount after a host change
- Recording to a **network share** (NFS/SMB): latency and locking break segment writes. Record locally and sync elsewhere
- A **read-only** mount after a host reboot where the array didn't come up

## 5. Hardware acceleration side-effects

A broken or changed `hwaccel_args` after a host/driver update affects the whole ffmpeg chain, and recordings can be the first casualty. Temporarily remove hardware acceleration to see if recordings resume — if they do, fix the GPU setup rather than the record config.

## 6. One camera out of several

Almost always that camera's own stream: its audio codec, a different firmware, H.265 vs H.264, or a substream without the record role. Compare its block with a working camera's, line by line.

## Diagnose in order

1. **Frigate log** (`docker compose logs -f frigate`) while it should be recording — ffmpeg's error is printed in full
2. **Files on disk?** — separates server from playback
3. **Drop audio** with `preset-record-generic` as a test
4. **Disk space and writability**
5. **Retention settings** for your version
6. Compare a **working camera's** config

## Prevention

- **Pin the Frigate image tag**; recording config changes between minor versions
- Record to **local storage**
- Monitor **free space** with an alert
- After any upgrade, check the timeline for **one camera** before assuming it's fine
- Keep the config in **version control** so you can diff it against the release notes

## FAQ

**Why would audio break video recording?**
Because the stream is copied into one container. If the audio can't be written, the whole output fails.

**Does Frigate need motion to record?**
It depends on retention mode. `all` records continuously; motion-based modes only keep segments with activity.

**Can I record to a NAS?**
It works for some people and breaks for many. Record locally; move files afterwards.

**Files exist but won't play.**
Browser codec support — usually H.265. Check with VLC on the file directly.
