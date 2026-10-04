---
title: "crowsnest: Webcam Not Working in Mainsail/Fluidd"
slug: crowsnest-webcam-not-working
meta_description: "Black stream, 'no device found', or a camera that works in one browser only. How to read crowsnest.log and pick the right mode for your camera."
updated: October 2026
cluster: round 13 (tech) — crowsnest GitHub issues
competition: LOW
---

# crowsnest: Webcam Not Working in Mainsail/Fluidd

crowsnest finds your camera, picks a streaming mode, and serves it. When the stream is black or missing, the answer is nearly always in its own log — which names the device it found and why it rejected it.

```bash
tail -n 60 ~/printer_data/logs/crowsnest.log
```

## 1. Find the camera's stable path

USB camera device numbers change across reboots, and a hardcoded `/dev/video0` will eventually point at the wrong thing — or at a metadata node rather than the video node. Use the by-id path:

```bash
ls -l /dev/v4l/by-id/
```

```
usb-046d_HD_Pro_Webcam_C920_ABC123-video-index0 -> ../../video0
```

Put that full path in the config:

```ini
[cam 1]
mode: camera-streamer
enable_rtsp: false
rtsp_port: 8554
port: 8080
device: /dev/v4l/by-id/usb-046d_HD_Pro_Webcam_C920_ABC123-video-index0
resolution: 1280x720
max_fps: 15
```

Note `-video-index0`. A single USB camera commonly exposes several `/dev/video*` nodes, and only the first is the capture node. Selecting `video1` on a camera whose capture node is `video0` gives exactly the "device found, no stream" symptom.

Confirm what the device can actually do:

```bash
v4l2-ctl --device=/dev/video0 --list-formats-ext
```

If the resolution and framerate in your config aren't in that list, the stream fails. This is the second most common cause: people set 1920x1080 at 30 fps on a camera that only offers it in MJPEG, while the config asks for YUYV.

## 2. Pick the right mode

crowsnest has three modes and they aren't interchangeable:

| Mode | Use for | Notes |
|---|---|---|
| `camera-streamer` | Pi Camera modules, and USB cameras on a Pi | Hardware-accelerated; supports WebRTC |
| `ustreamer` | Any USB camera, any host | MJPEG only; the safe fallback |
| `mjpg-streamer` | Legacy | Deprecated; avoid |

Rules that save time:

- **`camera-streamer` requires a Raspberry Pi** (it uses the Pi's hardware encoder). On an x86 host, an Orange Pi, or inside a container without the right devices, it fails at startup. The log says so plainly. Use `ustreamer`.
- **`libcamera`-based Pi Camera modules** need `camera-streamer` with the libcamera path, not a `/dev/video*` device. A Pi Camera on Bookworm configured as a V4L2 device is a frequent dead end.
- **WebRTC works in some browsers only** in certain versions. If the stream works in Chrome and is black in Safari or Firefox, switch the Mainsail camera service to MJPEG-stream to confirm — that isolates it to WebRTC rather than crowsnest.

## 3. Match Mainsail's camera settings

crowsnest serving correctly and Mainsail showing nothing is a URL problem, not a camera problem.

In Mainsail: **Settings → Webcams**. For `ustreamer`:

- Service: **MJPEG-Stream**
- URL Stream: `/webcam/?action=stream`
- URL Snapshot: `/webcam/?action=snapshot`

For `camera-streamer` with WebRTC:

- Service: **WebRTC (camera-streamer)**
- URL Stream: `/webcam/webrtc`
- URL Snapshot: `/webcam/snapshot`

The leading `/webcam/` relies on your nginx config proxying that path to crowsnest's port. If you changed `port:` in crowsnest.conf, the nginx site must change too — otherwise you've moved the stream and nothing is told.

Test crowsnest directly, bypassing nginx and Mainsail:

```bash
curl -sI http://localhost:8080/?action=stream | head -3
```

A 200 with `multipart/x-mixed-replace` means crowsnest is fine and the problem is downstream.

## 4. Resource problems

- **USB bandwidth.** Two 1080p MJPEG cameras on one Pi's USB bus will not both run. Drop resolution or framerate, or move one to a different physical controller.
- **Power.** An underpowered Pi with a bus-powered camera resets the camera under load. `dmesg | grep -i usb` shows the disconnects.
- **CPU.** `ustreamer` transcoding on a Pi 3 at 1080p30 starves Klipper and causes `Timer too close`. 720p15 is a sensible ceiling for a print camera; you don't need more.

## What not to do

- **Don't use `/dev/video0` in config.** It will break on a reboot or a replugged camera.
- **Don't run two streamers on the same device.** crowsnest plus a stray `ustreamer` from an old guide means whichever starts first wins and the other logs a busy device.
- **Don't push 1080p30 for timelapse.** Timelapse takes snapshots; stream resolution barely matters, and high framerates cost you print quality via CPU contention.
- **Don't debug in Mainsail first.** Curl the stream directly; it halves the search space.

## Prevention

| Habit | Why |
|---|---|
| Always use `/dev/v4l/by-id/...` | Immune to enumeration order |
| Record `--list-formats-ext` output in a comment | Stops invalid resolution/format combinations |
| Keep the stream at 720p15 | Leaves CPU for Klipper, which matters more |
| Change crowsnest's port and nginx's together | They're one setting split across two files |

## FAQ

**Can I use an IP camera instead?**
Yes — crowsnest isn't involved. Point Mainsail's webcam URL straight at the camera's MJPEG or HLS endpoint.

**Stream works locally but not remotely.**
Reverse proxy buffering. For MJPEG you need `proxy_buffering off;` on that location.

**Timelapse frames are missing.**
That's moonraker-timelapse, using the snapshot URL. Verify the snapshot URL separately from the stream URL; they fail independently.

**Pi Camera v3 shows a black frame.**
Autofocus and the libcamera path. Confirm with `rpicam-hello` first; if that's black, crowsnest isn't the problem.
