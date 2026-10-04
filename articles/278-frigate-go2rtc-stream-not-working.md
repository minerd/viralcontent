---
title: "Frigate go2rtc Stream Not Working? Test It at Port 1984 First"
slug: frigate-go2rtc-stream-not-working
meta_description: "'Failed to fetch streams from go2rtc', black live view, or playback that dies after 35 seconds. The port 1984 check, H.265 in browsers, keyframe intervals and roles."
updated: October 2026
cluster: round 12 (tech) — Frigate GitHub discussions and docs
competition: LOW
---

# Frigate go2rtc Stream Not Working? Test It at Port 1984 First

Before changing any config, find out whether **go2rtc** is getting the stream at all. That single check splits the problem in half.

## Step 1: the go2rtc web UI

Open **`http://frigate-host:1984`**. Click your camera's stream.

- **Stream plays here** → go2rtc has the camera. Your problem is browser playback or Frigate's config (steps 3–5)
- **Stream fails here** → the source URL, credentials, codec or transport is wrong (step 2)
- **Page doesn't load** → go2rtc isn't running; check the Frigate log and your `go2rtc:` config block for a YAML error

Also check Frigate's log for **"Failed to fetch streams from go2rtc"**, which means Frigate itself can't reach the embedded go2rtc — usually a config parse failure earlier in the file.

## Step 2: prove the camera stream outside Frigate

```bash
ffprobe -v error -show_streams "rtsp://user:pass@192.168.1.60:554/stream1" | head -30
# or just open the URL in VLC
```

Note the **video codec** and whether there's an audio track you didn't expect. Then:

- Credentials with special characters need **URL-encoding** (`@` → `%40`)
- Try the camera's **substream** — many cheap cameras can't serve two main-stream clients
- Force **TCP** transport, which fixes a lot of flaky RTSP:
  ```yaml
  go2rtc:
    streams:
      front: 
        - "ffmpeg:rtsp://user:pass@cam/stream1#input=rtsp/udp"   # or
      front_tcp:
        - "rtsp://user:pass@cam/stream1"      # go2rtc prefers TCP by default
  ```
- Camera **connection limits**: Frigate + go2rtc + a phone app + an NVR is often one too many

## Step 3: browser codec support (the "debug works, live doesn't" case)

If Frigate's debug view shows video and the **Live** view is black, your browser usually can't decode what the camera sends — most often **H.265**, or an audio track it won't play.

Options:
- Set the camera's stream to **H.264** (the reliable answer)
- Keep H.265 and accept that only some browsers/devices will play it
- Use go2rtc to **transcode** for the live view (costs CPU):
  ```yaml
  go2rtc:
    streams:
      front: "rtsp://user:pass@cam/stream1"
      front_transcoded: "ffmpeg:front#video=h264#audio=aac"
  ```

## Step 4: keyframe interval

A long GOP/i-frame interval delays the first frame, so live view takes many seconds to appear or looks stuck. Set the camera's **keyframe interval to match its frame rate** (roughly one keyframe per second) in the camera's own web UI. This is a camera setting, not a Frigate one, and it improves everything downstream.

## Step 5: roles and the restream wiring

A common misconfiguration: pointing Frigate's **detect** role at the go2rtc restream in a way that loops, or restreaming and then asking Frigate to re-read it inefficiently.

The documented pattern is:

```yaml
go2rtc:
  streams:
    front:
      - rtsp://user:pass@cam/main
      - "ffmpeg:front#audio=aac"

cameras:
  front:
    ffmpeg:
      inputs:
        - path: rtsp://127.0.0.1:8554/front
          input_args: preset-rtsp-restream
          roles: [record, detect]
```

- Use **`127.0.0.1:8554`**, not the camera, once you restream
- Use the **restream preset** for input args
- Read the Live view documentation for your Frigate version — this block has changed shape between releases

## Step 6: WebRTC dying after ~35 seconds

Reported: WebRTC live feed stops after about 35 seconds. That's a WebRTC connectivity problem rather than a stream problem:

- Expose the **WebRTC port (8555 TCP/UDP)** and set `webrtc` candidates in the go2rtc config for your host IP
- Without usable candidates it falls back and then times out
- MSE/HLS playback modes work without that plumbing — switch the live view mode as a test

## Prevention

1. **H.264** for anything you want to watch in a browser
2. **Keyframe interval ≈ 1 second** on every camera
3. **Substream for detect**, main stream for record
4. Keep camera **firmware** current but note what changed
5. **Pin the Frigate tag** — the live/restream config keeps evolving

## FAQ

**What is port 1984?**
go2rtc's own web UI, embedded in Frigate. It's the fastest way to see whether the stream is reaching go2rtc.

**Why does debug view work but live not?**
Debug is a server-rendered image; live is a real stream your browser has to decode. Usually H.265.

**Should I restream everything through go2rtc?**
It reduces camera connections and is the recommended pattern — just wire the roles to the restream, not the camera.

**Audio breaks my stream.**
Transcode it to AAC in go2rtc, or drop it.
