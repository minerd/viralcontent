---
title: "Threadfin: Channels Not Loading in Plex or Jellyfin"
slug: threadfin-channels-not-loading
meta_description: "Threadfin shows channels but your media server finds none, or tuners go offline. The HDHomeRun emulation, the buffer setting, and the stream limit."
updated: October 2026
cluster: round 13 (tech) — Threadfin GitHub issues
competition: LOW
---

# Threadfin: Channels Not Loading in Plex or Jellyfin

Threadfin presents your M3U playlist as an HDHomeRun-style tuner. Three layers can fail, and the symptom in Plex or Jellyfin is the same unhelpful "no channels found".

Work outwards: playlist → Threadfin → media server.

## 1. Does Threadfin itself have channels?

In the Threadfin UI, **Playlist** should list channels, and **Mapping** should show them with `active` toggled on.

Points that catch people:

- **Channels must be explicitly activated.** A fresh playlist import leaves everything inactive. The XML/M3U output Threadfin serves contains only *active* channels — so an import that looks fine produces an empty tuner. This is the most common cause of "Threadfin works, Plex sees nothing".
- **The `tuner` count** (Settings → General) limits how many simultaneous streams Threadfin advertises. Plex reads this at tuner setup. Setting it to 1 and then wondering why a second stream fails is expected behaviour.
- **Filters.** A filter with a typo matches nothing and leaves you with zero active channels after a refresh.

Verify what Threadfin is actually serving:

```bash
curl -s http://192.168.1.10:34400/discover.json
curl -s http://192.168.1.10:34400/lineup.json | head -40
```

`lineup.json` returning `[]` means the problem is in Threadfin's configuration, not in the media server. That's a decisive two-command test.

## 2. The URLs the media server needs

| Setting | Value |
|---|---|
| Tuner / DVR device | `192.168.1.10:34400` |
| XMLTV / EPG | `http://192.168.1.10:34400/xmltv/threadfin.xml` |
| M3U (for clients that want it) | `http://192.168.1.10:34400/m3u/threadfin.m3u` |

In **Plex**: Live TV & DVR → Set up Plex DVR → it should autodiscover, but "Enter manually" with `192.168.1.10:34400` is more reliable. Plex is fussy: it must reach the host directly, so Threadfin behind a reverse proxy with a path prefix generally won't be discovered.

In **Jellyfin**: Live TV → Tuner Devices → Add → **HDHomeRun** → the same host:port. Then TV Guide Data Providers → XMLTV → the xmltv URL.

Two traps:

- **Plex and Jellyfin need Threadfin on the same network reachability.** In Docker, `network_mode: host` or an explicit port publish — a container on a separate bridge network that Plex can't reach by IP fails at discovery.
- **The `Threadfin` host URL setting.** In Settings there's a field for the URL Threadfin advertises about itself. If it says `localhost` or a stale IP, Plex records that address and then can't connect, even though discovery worked. Set it to the LAN IP.

## 3. Streams start then fail

- **Buffer setting.** Threadfin can proxy through ffmpeg/VLC or pass the URL through. Settings → Streaming → Buffer:
  - **None** — the client connects to the provider directly. Fewest moving parts, but the provider sees your client's requests, and some don't tolerate Plex's probing.
  - **ffmpeg** — Threadfin pulls and re-serves. More robust with awkward providers, costs CPU. This is usually the fix when streams work in VLC and fail in Plex.
  
  Confirm the binary exists if you select it:

```bash
docker exec threadfin which ffmpeg
```

- **Provider connection limit.** Most IPTV providers allow a small number of concurrent connections. Plex opens a connection to probe the channel *and* one to play it; with a 1-connection provider that fails immediately. Setting Threadfin's tuner count above the provider's limit guarantees this.
- **User-agent.** Some providers reject unknown clients. Threadfin lets you set the user-agent; a provider-recommended string fixes an otherwise inexplicable 403.

## 4. EPG empty or mismatched

- The XMLTV file must be fetched and its channel IDs **mapped** to your channels in Threadfin's Mapping tab. Unmapped channels show in the lineup with no guide data.
- Plex caches guide data aggressively. After fixing the mapping, remove and re-add the guide source rather than waiting.
- A huge XMLTV file (many days, hundreds of channels) can time out. Reduce the channel set — you only need guide data for channels you activated.

## What not to do

- **Don't put Threadfin behind a reverse proxy at a subpath** for Plex. HDHomeRun emulation expects specific root paths.
- **Don't set the tuner count higher than your provider's connection limit.** It converts a clean limit into random failures.
- **Don't activate all 10,000 channels from a big playlist.** Plex and Jellyfin both struggle, guide data becomes enormous, and you'll never scroll it. Activate what you watch.
- **Don't debug in Plex first.** `curl lineup.json` answers the question immediately.

## Prevention

| Habit | Why |
|---|---|
| Activate a small, deliberate channel set | Everything downstream gets faster and more reliable |
| Set the advertised host URL to a static LAN IP | Prevents stale-address failures after a container move |
| Keep tuner count ≤ provider connection limit | Removes random stream failures |
| Back up the Threadfin config directory | Mappings and filters are tedious to rebuild |

## FAQ

**Threadfin or xTeVe?**
Threadfin is the actively maintained fork. xTeVe configurations import, and xTeVe-era guides mostly still apply.

**Does it work with Emby?**
Yes, same HDHomeRun path as Jellyfin.

**Channels work in VLC but not Plex.**
Classic buffer case: switch to the ffmpeg buffer. Plex's probing behaviour is stricter than VLC's.

**Can two media servers share one Threadfin?**
Yes, but each one's probes count against your provider's connection limit.
