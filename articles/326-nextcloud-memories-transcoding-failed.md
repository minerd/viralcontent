---
title: "Nextcloud Memories: Video Transcoding Failed"
slug: nextcloud-memories-transcoding-failed
meta_description: "Videos won't play, or only play at original quality. go-vod, the ffmpeg paths, temp space and the hardware-acceleration device permissions."
updated: October 2026
cluster: round 13 (tech) — Memories GitHub issues
competition: LOW
---

# Nextcloud Memories: Video Transcoding Failed

Memories transcodes through a helper binary called **go-vod**, which shells out to ffmpeg. The error in the UI is generic; the cause is always in one of four places. Start with the app's own diagnostic page — it checks most of this for you.

**Admin settings → Memories**, or:

```bash
docker exec -u www-data nextcloud php occ memories:video-setup
```

That command tests ffmpeg, ffprobe, go-vod and hardware acceleration, and prints what's missing. Run it before changing anything.

## 1. ffmpeg and ffprobe must exist, with paths Nextcloud knows

```bash
docker exec nextcloud which ffmpeg ffprobe
```

The official Nextcloud images do **not** include ffmpeg. If it's absent, nothing transcodes. Either use an image that includes it, or install it in a custom Dockerfile:

```dockerfile
FROM nextcloud:apache
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*
```

Then tell Memories where they are:

```bash
docker exec -u www-data nextcloud php occ config:system:set memories.ffmpeg_path --value="/usr/bin/ffmpeg"
docker exec -u www-data nextcloud php occ config:system:set memories.ffprobe_path --value="/usr/bin/ffprobe"
```

Installing ffmpeg inside a running container with `apt-get` works until the container is recreated, at which point transcoding breaks again "for no reason". Build it into the image.

## 2. go-vod must be able to run and to write

go-vod runs as a separate process (or container). Two requirements:

**It needs temp space.** Transcoding writes segments to a temp directory. The default is inside the container, which may be small or read-only:

```bash
docker exec -u www-data nextcloud php occ config:system:set memories.vod.path --value="/var/www/html/custom_apps/memories/exhaust"
```

A full temp directory produces exactly the "transcoding failed" message. Check:

```bash
docker exec nextcloud df -h /tmp
```

**It must be executable.** If `/tmp` or the app directory is mounted `noexec`, go-vod cannot start. This is common on hardened hosts and on some NAS platforms, and the symptom is a transcoding failure with go-vod not appearing in the process list:

```bash
docker exec nextcloud mount | grep -E 'noexec'
docker exec nextcloud ps aux | grep go-vod
```

**External go-vod container** is the cleaner layout for Docker setups:

```yaml
  go-vod:
    image: radialapps/go-vod
    restart: always
    environment:
      - NEXTCLOUD_HOST=https://cloud.example.com
    volumes:
      - ncdata:/var/www/html:ro
```

Then enable external mode:

```bash
docker exec -u www-data nextcloud php occ config:system:set memories.vod.external --value=true --type=boolean
```

The volume must be mounted at the **same path** go-vod sees in Nextcloud's file metadata. A mismatch means go-vod is handed a path that doesn't exist on its side — the most common failure in the external setup.

## 3. Hardware acceleration: device access

VAAPI or NVENC can be enabled, and both fail in the same way if the device isn't accessible.

**VAAPI (Intel/AMD):**

```yaml
    devices:
      - /dev/dri:/dev/dri
```

```bash
docker exec -u www-data nextcloud php occ config:system:set memories.vod.vaapi --value=true --type=boolean
```

Then the web server user must be able to use it. The `www-data` user needs to be in the group owning `/dev/dri/renderD128`:

```bash
docker exec nextcloud ls -l /dev/dri/
# crw-rw---- 1 root 104 ... renderD128
docker exec nextcloud getent group 104
```

If no group matches, add `group_add: ["104"]` to the compose service with the host's actual GID. A permission failure here reports as "transcoding failed" with a VAAPI device error in go-vod's log — not as a permissions message in the UI.

**NVENC:** needs the NVIDIA container toolkit, `runtime: nvidia`, and `memories.vod.nvenc` set. Verify with `nvidia-smi` inside the container before enabling it in Memories.

If hardware acceleration fails, **disable it and confirm CPU transcoding works first**. That isolates the problem to acceleration rather than the whole pipeline.

## 4. Videos play at original quality only

Not a failure — it's the fallback. Memories streams the original when transcoding is unavailable. If large videos stutter but small ones are fine, transcoding is off and you're seeing direct play.

Check the quality selector in the player: if only "Original" is offered, go-vod isn't producing renditions. Back to section 1.

## What not to do

- **Don't install ffmpeg interactively in the container** and consider it done. It's gone on the next pull.
- **Don't enable VAAPI before confirming the device is usable.** You convert a working CPU path into a broken one.
- **Don't point `memories.vod.path` at a tmpfs with a few hundred MB.** 4K transcode segments will fill it.
- **Don't run `occ memories:index` to fix playback.** Indexing is about metadata and thumbnails; transcoding is a separate pipeline.

## Prevention

| Habit | Why |
|---|---|
| Build ffmpeg into your image | Survives container recreation |
| Run `occ memories:video-setup` after every upgrade | It checks everything in this article in one command |
| Keep the go-vod volume path identical to Nextcloud's | The external-mode failure mode is invisible otherwise |
| Test CPU transcoding before enabling HW accel | Keeps the variables separated |

## FAQ

**Is transcoding required?**
No. Without it, clients play originals — fine on a LAN, poor over a slow link or for HEVC on an unsupported browser.

**Which codecs cause the most trouble?**
HEVC/H.265 and 10-bit footage, because browser support is patchy. These are exactly the files transcoding exists for.

**Can I pre-transcode?**
Not through Memories. You'd convert the originals yourself, which changes your archive — usually not what you want.

**Thumbnails work but video doesn't.**
Thumbnails come from ffmpeg directly; playback goes through go-vod. That split means go-vod specifically, so start at section 2.
