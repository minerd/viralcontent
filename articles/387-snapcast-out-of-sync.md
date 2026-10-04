---
title: "Snapcast Clients Drifting Out of Sync"
slug: snapcast-out-of-sync
meta_description: "Clients start aligned and drift apart, or lose their latency setting after a volume change. Buffer, per-client latency and the muted-client trap."
updated: October 2026
cluster: round 14 (tech) — snapcast/snapcast GitHub issues
competition: LOW
---

# Snapcast Clients Drifting Out of Sync

Snapcast synchronises by timestamping the stream and having every client play each sample at the same wall-clock moment. Drift means a client's clock estimate or its output latency is wrong — and there are a few specific, fixable causes.

## 1. Per-client latency is the main knob

Every client has a latency offset, set from a controller (Snapweb, Snapdroid, Home Assistant, or the JSON-RPC API) — **not** in the client's own config file.

```bash
# via the control API
curl -s -X POST http://192.168.1.10:1780/jsonrpc -H 'Content-Type: application/json' -d '{
  "id": 1, "jsonrpc": "2.0", "method": "Client.SetLatency",
  "params": {"id": "aa:bb:cc:dd:ee:ff", "latency": 50}
}'
```

Snapcast aligns all clients to **whichever has the highest latency**, so a single badly-configured client delays everything. Set the slowest device's latency to 0 and add offsets to the faster ones, rather than the reverse.

Bluetooth speakers and HDMI/eARC paths add 100–300 ms that Snapcast cannot measure. Those need manual offsets, found by ear with a clap or a click track.

## 2. Latency forgotten after a volume change

A documented bug worth knowing: **adjusting a client's volume through some interfaces (including Home Assistant) clears its latency setting**, and the client drifts until restarted.

Symptoms match exactly: everything was fine, someone changed the volume, now one room lags.

Workarounds:

- Re-apply the latency after volume changes, or script it.
- Restart that client (`systemctl restart snapclient`) to re-read its configured value.
- Set volume at the source or on the device rather than through Snapcast's API where you can.

## 3. Buffer size

```ini
# /etc/snapserver.conf
[stream]
buffer = 1000
chunk_ms = 20
codec = flac
sampleformat = 48000:16:2
```

`buffer` is the total latency from reading on the server to playing on the client, 200–6000 ms, default 1000. What it buys:

- **Higher buffer** — more tolerance of Wi-Fi jitter, more stable sync, more delay. For whole-home audio with no video, 1000–1500 ms is comfortable.
- **Lower buffer** — less delay, more dropouts and drift on marginal links. Below about 500 ms over Wi-Fi, expect trouble.

If you're syncing audio to video (Kodi, a TV), Snapcast's inherent latency is the problem rather than the drift — budget for it in the player's audio offset, and keep the buffer as low as your network allows.

`codec = flac` is the default and the right choice; `pcm` uses far more bandwidth and `opus` adds its own latency.

## 4. Drift that returns after a while

Radio streams drifting apart after an initially correct offset is reported and usually means **clock drift on the client device**, not a Snapcast setting. Cheap Pi Zeros and some SBCs have poor oscillators.

Mitigations:

- **NTP on every client**, actually working:

```bash
timedatectl status
chronyc tracking     # or: ntpq -p
```

Snapcast does its own clock estimation, but a client whose system clock is being stepped by NTP mid-stream produces audible glitches. Prefer `chrony` with slewing rather than large steps.

- **Wired Ethernet** where possible. Wi-Fi power saving on the client is a frequent cause of periodic resync:

```bash
sudo iw dev wlan0 set power_save off
```

- **CPU contention.** A client also running a browser or a transcode will miss its deadlines.

## 5. Muted clients and rebuffering

A real behaviour with a real fix: **muted clients can go out of sync** or stop their stream entirely, then need to rebuffer when unmuted — producing a delay of a second or more.

```ini
[stream]
send_to_muted = true
```

With that on, Snapcast keeps feeding muted clients so they stay in sync and unmute instantly. It costs bandwidth to rooms nobody is listening to, which on a wired network is irrelevant.

## 6. Client disconnecting every few minutes

```bash
journalctl -u snapclient -n 50
```

Reported at 4–5 minute intervals, which is the shape of a NAT or firewall state timeout, or Wi-Fi power saving. Check:

- Power saving off (above)
- The server reachable on **1704** (stream) and **1705** (control)
- No VPN or IDS in the path resetting idle TCP connections

## What not to do

- **Don't lower the buffer to reduce delay** before fixing jitter. You'll trade one problem for a worse one.
- **Don't set latency on the client's command line** and expect it to stick — it's a server-held, per-client property in current versions.
- **Don't mute clients and expect instant unmute** without `send_to_muted`.
- **Don't mix a Bluetooth speaker into a sync group** without measuring its offset. It will never align by itself.

## Prevention

| Habit | Why |
|---|---|
| Wired clients where you can, power saving off where you can't | Most drift is network jitter |
| `send_to_muted = true` | Removes the mute/unmute desync class |
| Per-client latency recorded in your notes | You'll need to re-apply it after the volume bug |
| NTP with slewing on every client | Prevents clock steps mid-stream |

## FAQ

**What latency should I expect?**
Around the buffer value — 1 second by default. It's whole-home audio, not a monitoring path.

**Can I use it with Music Assistant?**
Yes, it's a supported player type and handles the group plumbing for you.

**Does it sync video?**
No. The latency is too high for lip sync unless you offset the video player.

**Different sample rates per client?**
The server resamples to one format for all clients. Set `sampleformat` to match your most constrained device.
