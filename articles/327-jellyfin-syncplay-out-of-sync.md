---
title: "Jellyfin SyncPlay Drifting or Won't Start"
slug: jellyfin-syncplay-out-of-sync
meta_description: "SyncPlay keeps drifting, pauses for one user only, or the group won't form. Transcoding, client support and the time-sync settings that actually matter."
updated: October 2026
cluster: round 13 (tech) — Jellyfin GitHub issues and forum
competition: LOW
---

# Jellyfin SyncPlay Drifting or Won't Start

SyncPlay coordinates playback position across clients. It does **not** coordinate the decoding pipeline — so anything that makes one client's playback behave differently (transcoding, buffering, a different player) shows up as drift. Most SyncPlay complaints are really transcoding complaints.

## 1. Make every client play the same way

The single biggest improvement: get all clients **direct playing** the same file, or all transcoding identically.

Check per session in **Dashboard → Activity**: it says "Direct Playing", "Direct Streaming" or "Transcoding" for each. If one client direct plays and another transcodes, their latency differs by seconds and SyncPlay will spend the whole film correcting.

Causes of mixed playback:

- One client doesn't support the container or codec (HEVC, or an unsupported subtitle format forcing a burn-in transcode)
- A user's quality setting capped at a lower bitrate
- **Subtitle format.** Image-based (PGS/VOBSUB) and some ASS subtitles force a video transcode on clients that can't overlay them. Toggling subtitles mid-playback changes the mode for that client only, which produces sudden drift. Use SRT where you can.

The practical fix is to pick content and settings everyone direct plays, and set every participant's quality to the same value.

## 2. Group won't form or users can't join

- **Permissions.** Each user needs the **SyncPlay** permission enabled in their profile. In Dashboard → Users → (user) → there's an explicit SyncPlay access setting; new users don't always have it.
- **Client support.** Not every client implements SyncPlay. Web, Android, Android TV and some desktop clients do; several third-party and older clients do not, and they'll show no SyncPlay button at all. A client without the button is not misconfigured.
- **Version skew.** Clients much older than the server may not negotiate the group. Update both ends.
- **Reverse proxy and websockets.** SyncPlay signalling uses the websocket connection. If your proxy doesn't upgrade it, playback works and SyncPlay silently doesn't:

```nginx
location / {
    proxy_pass http://127.0.0.1:8096;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

This is worth checking early: a missing websocket upgrade also breaks the dashboard's live session view, which is a quick way to confirm it.

## 3. Drift settings

In each client's playback settings there are SyncPlay tolerances. The useful ones:

- **Sync method**: "Playback rate" (speeds up or slows down slightly to catch up) versus "Skip" (jumps). Playback-rate is far less disruptive for small offsets; skip is better for large ones. If your clients support it, playback-rate with a small threshold gives the smoothest result.
- **Maximum offset before correcting** — too small and it corrects constantly, which is more annoying than the drift. A few hundred milliseconds is reasonable.
- **Time sync** — SyncPlay measures round-trip time to the server. A client on a congested or high-jitter connection (mobile data, distant VPN) will have unstable measurements and will drift regardless of settings. This is the limit of what the feature can do.

## 4. Remote participants

SyncPlay across the internet works, with caveats that are physical rather than configurable:

- Latency differences of tens of milliseconds are fine. Hundreds, with jitter, are not.
- A remote client transcoding while a local one direct plays guarantees drift (section 1).
- Buffering on one end pauses that client; SyncPlay will pause everyone if configured to, which is correct but feels like a fault.

Where people have one far-away participant, the pragmatic approach is to let them have a slightly lower quality that direct plays rather than a higher one that transcodes.

## What not to do

- **Don't troubleshoot SyncPlay before checking the playback mode of every session.** Mixed direct-play and transcoding cannot be fixed by SyncPlay settings.
- **Don't set the correction threshold very low.** Constant micro-corrections are worse than a stable 300 ms offset.
- **Don't blame the server CPU first.** A CPU-starved transcode causes buffering, which SyncPlay then reports as drift — but the fix is the transcode, not SyncPlay.
- **Don't expect it to work on clients that don't implement it.** Check the client, not the server.

## Prevention

| Habit | Why |
|---|---|
| Keep a direct-play-friendly copy of shared content (H.264, SRT subs) | Eliminates the main cause of drift |
| Same quality setting for all participants | Keeps the pipelines identical |
| Websocket upgrade configured and verified | SyncPlay and the live dashboard both depend on it |
| Enable the SyncPlay permission when creating users | Avoids the "no button" confusion |

## FAQ

**Does SyncPlay need everyone on the same network?**
No, but latency and transcoding differences matter more across the internet.

**Can I sync with Plex or Emby clients?**
No. It's a Jellyfin protocol feature.

**One user's playback pauses for everyone.**
That's the group pause behaviour, which is configurable per group. If it's unwanted, the setting is in the SyncPlay group options.

**Audio is in sync but video isn't.**
That's not SyncPlay — it's an A/V sync problem on one client, usually hardware decoding. Test that file solo on that client.
