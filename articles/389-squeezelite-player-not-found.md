---
title: "Lyrion Music Server: \"Player Not Found\" / Squeezelite Not Detected"
slug: squeezelite-player-not-found
meta_description: "LMS doesn't see squeezelite, or a player disappears after an update. The audio-device exit, port 3483/udp, and the discovery path."
updated: October 2026
cluster: round 14 (tech) — Lyrion community forums
competition: LOW
---

# Lyrion Music Server: "Player Not Found" / Squeezelite Not Detected

Two things cause nearly all of these: **squeezelite exited** (so there is nothing to find), or **discovery traffic is blocked** (so it can't be found).

Check the first in one command:

```bash
systemctl status squeezelite
journalctl -u squeezelite -n 30 --no-pager
```

## 1. squeezelite exits when its audio device isn't there

By default, squeezelite **exits immediately** if the output device it was told to use doesn't exist. After a reboot, a USB DAC that enumerated as `hw:1` yesterday may be `hw:2` today, and squeezelite quits silently as far as LMS is concerned.

List what's actually available:

```bash
squeezelite -l
```

```
default
sysdefault:CARD=DAC
hw:CARD=DAC,DEV=0
plughw:CARD=DAC,DEV=0
```

Then use the **card name**, not the number:

```bash
# /etc/default/squeezelite
SB_EXTRA_ARGS="-o plughw:CARD=DAC,DEV=0 -n Kitchen -s 192.168.1.10"
```

`CARD=DAC` is stable across reboots; `hw:1` is not. This single change fixes the "worked yesterday" class.

For a Pi with HDMI and headphone jack plus a HAT, the HAT's card name is in `/proc/asound/cards`.

## 2. Port 3483 — both protocols

Discovery is **UDP/3483**; the player protocol is **TCP/3483**; the web UI and streaming are **TCP/9000** (and 9090 for the CLI).

The one people miss is **UDP/3483**, and without it hardware players (Boom, Radio, Duet) and squeezelite instances can't find the server automatically:

```bash
sudo ufw allow 3483/udp
sudo ufw allow 3483/tcp
sudo ufw allow 9000/tcp
sudo ufw allow 9090/tcp
```

In Docker, publish both:

```yaml
services:
  lms:
    image: lmscommunity/lyrionmusicserver
    network_mode: host      # simplest, and discovery needs broadcast
    volumes:
      - ./config:/config
      - ./music:/music:ro
```

Bridge networking breaks UDP discovery because broadcasts don't cross it. `network_mode: host` is the practical choice for LMS; if you must use bridge, point every player at the server explicitly with `-s <ip>` and accept that hardware players won't auto-discover.

## 3. Point the player at the server explicitly

Discovery is convenience, not a requirement:

```bash
squeezelite -s 192.168.1.10 -o plughw:CARD=DAC,DEV=0 -n Kitchen
```

`-s` skips discovery entirely. If a player works with `-s` and not without, you have confirmed a UDP/broadcast problem rather than anything else — a useful, fast bisect.

## 4. Players disappearing after an LMS update

Reported on specific stable releases: squeezelite players vanishing from the player list. Things to check in order:

- **LMS version and the player's firmware/protocol.** Very old squeezelite builds and very new LMS versions occasionally disagree; update squeezelite:

```bash
squeezelite -?  | head -2      # shows version
```

- **The player's MAC-derived ID collided.** squeezelite derives its ID from a network interface's MAC. Two instances in containers sharing a MAC, or a Pi whose MAC changed, appear as one player that flaps. Set it explicitly:

```bash
squeezelite -m 01:02:03:04:05:06 -n Kitchen
```

- **LMS's player database.** Settings → Players shows configured players including ones not currently connected. A player that appears there but never connects is a network problem; one that isn't there at all has never announced.

## 5. The simpler alternatives

Two options worth knowing before you spend an evening:

- **Install squeezelite on the same machine as LMS.** No discovery, no firewall, no MAC questions.
- **The Local Player plugin** for LMS, which runs squeezelite internally and is generally the least-effort route for audio out of the server itself.

For remote rooms, a Pi with squeezelite and `-s` pointing at the server is reliable once sections 1–2 are right.

## 6. Player appears, no sound

Separate issue:

```bash
aplay -D plughw:CARD=DAC,DEV=0 /usr/share/sounds/alsa/Front_Center.wav
alsamixer -c 1
```

- Another process holds the device (one consumer per ALSA device).
- The mixer is muted or at zero — common on fresh Pi images.
- Sample-rate mismatch: `-r 44100-192000` lets squeezelite negotiate; a fixed rate the DAC doesn't support fails silently.

## What not to do

- **Don't use `hw:1` in a service file.** Device numbers move.
- **Don't run LMS in bridge networking** and expect hardware players to find it.
- **Don't run two squeezelite instances against one ALSA device.** The second fails to open it and exits.
- **Don't delete players from LMS settings to "refresh" them.** You lose their settings and sync groups.

## Prevention

| Habit | Why |
|---|---|
| `CARD=NAME` output device, never a number | Survives reboots and replugs |
| UDP 3483 open, and host networking for LMS | Discovery works for hardware players too |
| Explicit `-n` name and `-m` MAC per instance | No collisions, stable identities |
| `-s <server-ip>` on software players | Removes discovery from the equation |

## FAQ

**Is Lyrion the same as Logitech Media Server?**
Yes — renamed, community-maintained continuation. Old LMS guides mostly still apply.

**Can squeezelite play to Bluetooth?**
Through an ALSA/PulseAudio sink, yes, with added latency that breaks sync groups.

**Sync between rooms drifts.**
LMS handles sync server-side; adjust each player's sync offset in its settings. Wired beats Wi-Fi.

**Can I use piCorePlayer instead?**
Yes — it's squeezelite plus a minimal OS, and it removes most of section 1 by handling the audio device selection in its UI.
