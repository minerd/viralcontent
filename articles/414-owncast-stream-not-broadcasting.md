---
title: "Owncast: Receiving the Stream But Viewers See Offline"
slug: owncast-stream-not-broadcasting
meta_description: "Owncast says it's receiving RTMP and viewers get the offline clip. The TLS-proxy problem, video passthrough and the transcoder log."
updated: October 2026
cluster: round 14 (tech) — owncast/owncast GitHub issues and docs
competition: LOW
---

# Owncast: Receiving the Stream But Viewers See Offline

The distinctive case: Owncast's admin panel shows an inbound stream, and visitors get the offline placeholder. That means **ingest works and output doesn't** — which narrows it to the transcoder or the way the stream reaches Owncast.

```bash
docker logs owncast --tail 100
docker exec owncast tail -n 60 /app/data/logs/transcoder.log
```

`transcoder.log` is the file that matters and the one people don't read.

## 1. Don't proxy RTMP through stunnel or nginx

A documented cause with a clear answer: attempts to secure the RTMP ingest with TLS (making RTMPS) via **stunnel or an nginx stream proxy** result in Owncast acknowledging that it is receiving the stream from the proxy while **not broadcasting it to viewers**. Reverting to plain RTMP makes it work every time.

So:

```yaml
services:
  owncast:
    image: owncast/owncast:latest
    ports:
      - "8080:8080"      # web, behind your HTTPS proxy
      - "1935:1935"      # RTMP ingest, NOT proxied
    volumes:
      - ./data:/app/data
```

- **Proxy the web port (8080) over HTTPS.** That's normal and supported.
- **Expose 1935 directly** for RTMP. Restrict it by source IP at the firewall if you're worried, and rely on the stream key for authentication.

If you must not expose 1935, send the stream over a VPN to the server rather than wrapping RTMP in TLS at a proxy.

## 2. Turn video passthrough off

Owncast's documentation is explicit: **if you're having issues, disable video passthrough.**

```
Admin → Video configuration → Stream output → Video passthrough: off
```

Passthrough forwards your encoder's output without re-encoding. It saves CPU and it requires your encoder's settings to be exactly compatible with HLS packaging — keyframe interval, profile, level. OBS defaults are often not, and the result is a stream that ingests and produces unplayable segments.

With passthrough off, Owncast transcodes and controls those parameters itself. Turn it back on later, deliberately, once everything works.

While you're in there, set a keyframe interval in OBS of **2 seconds**:

```
OBS → Settings → Output → Advanced → Keyframe Interval: 2
```

A keyframe interval of 0 (auto) or a long one produces segments Owncast can't cut cleanly.

## 3. Check the transcoder is actually producing segments

```bash
docker exec owncast ls -la /app/data/hls/0/
```

You should see `.ts` segment files appearing and a rolling `stream.m3u8`. If the directory is empty while RTMP is connected, the transcoder is failing — and `transcoder.log` will say why:

- **`Output file #0 does not contain any stream`** — the input isn't what ffmpeg expected; usually passthrough with an incompatible encoder.
- **Hardware encoder unavailable** — if you enabled NVENC/VAAPI/QSV and the container lacks the device, ffmpeg exits. Pass the device through or revert to software:

```yaml
    devices:
      - /dev/dri:/dev/dri
```

- **Permission denied writing HLS** — the data volume isn't writable.
- **`Killed`** — out of memory. Transcoding 1080p needs real CPU and RAM; a 512 MB container won't do it.

## 4. Bitrate and the viewer's experience

Owncast's own guidance: if your computer or network connection struggles to get video to the internet, viewers buffer. Reduce bitrate, resolution or framerate.

Practical starting points:

- **Upload bandwidth** must comfortably exceed your highest output variant. Owncast's output bitrate is what viewers consume, and your ingest bitrate is what you upload. Both matter.
- **One output variant** while debugging. Multiple variants multiply CPU cost.
- 720p30 at 2500 kbps is a robust default that almost any host can transcode.

## 5. Viewers see offline immediately after you stop and restart

Owncast keeps a short offline state and serves the offline clip. Restarting the stream too quickly, or an encoder that reconnects repeatedly, leaves viewers on the placeholder. Give it a few seconds, and check for a reconnect loop in OBS.

## 6. Embedded player works, the site doesn't (or vice versa)

That's the web layer:

```nginx
location / {
    proxy_pass http://127.0.0.1:8080;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_buffering off;
}
```

- **Websocket upgrade** is needed for chat and for the live status indicator. Without it, the page can show offline while the stream plays.
- **`proxy_buffering off`** — HLS segments are small and frequent; buffering adds latency and has caused stalls.

## What not to do

- **Don't wrap RTMP in TLS at a proxy.** It's the documented cause of exactly this symptom.
- **Don't leave passthrough on while troubleshooting.** It's the second cause.
- **Don't enable hardware encoding without passing the device through.** ffmpeg exits and viewers see offline.
- **Don't debug from the viewer side.** `transcoder.log` and the HLS directory tell you everything.

## Prevention

| Habit | Why |
|---|---|
| Plain RTMP on 1935, HTTPS only for the web port | Removes the proxy-ingest failure |
| Passthrough off, keyframe interval 2 s in OBS | Segments Owncast can package |
| Watch `transcoder.log` after any config change | The only place ffmpeg's errors appear |
| One output variant at 720p30 as your baseline | Works on modest hardware, then scale up |

## FAQ

**Can I restream to Twitch/YouTube at the same time?**
Not from Owncast; restream at your encoder or via a relay service.

**How many viewers can one server handle?**
Bounded by bandwidth, not CPU, once transcoding is done. Put a CDN in front for real scale.

**Latency is 15–30 seconds.**
Normal for HLS. Shorter segments reduce it at the cost of robustness.

**Chat doesn't work.**
Websocket upgrade at the proxy — section 6.
