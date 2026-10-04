---
title: "Jellyfin HDR Tone Mapping Stopped Working After an Update? How to Diagnose It"
slug: jellyfin-hdr-tone-mapping-broken
meta_description: "Washed-out or grey HDR after a Jellyfin or GPU driver update. How to tell a client regression from a driver break, what needs hardware acceleration, and how to roll back safely."
updated: October 2026
cluster: round 9 (tech) — GitHub issues and the Jellyfin forum only
competition: LOW
---

# Jellyfin HDR Tone Mapping Stopped Working After an Update? How to Diagnose It

HDR films that looked right last week now play **washed out, grey and flat** on an SDR screen. Nothing in your config changed. Something updated.

Three different things break HDR tone mapping, and they need different fixes.

## First: understand what has to be true for tone mapping to work at all

- Tone mapping only runs when the server is **transcoding** HDR → SDR. Direct play doesn't tone map, because nothing is being converted
- **Jellyfin has no software tone mapping.** It requires **hardware acceleration** (VA-API/QSV on Intel, NVENC on NVIDIA, AMF on AMD, VideoToolbox on macOS). If hardware acceleration isn't working, tone mapping isn't happening — that's the first thing to check, not the last
- **Dolby Vision** and **HDR10** behave differently; a profile-5 DV file with no HDR10 fallback is its own problem

So: open the **playback info** overlay during playback and confirm the stream is actually being **transcoded** and the hardware decoder/encoder is in use. Then read the **FFmpeg log** for that session — it names the filter chain and will say if tone mapping was skipped.

## Cause 1: a client-side regression

Reported pattern: **Jellyfin Media Player** broke HDR tone mapping in a specific release, and **downgrading to the previous version** restored it on the same server and the same files.

How to tell: the server is unchanged, other clients (web, TV app) look right, and it started exactly when that client updated.

What to do:
- **Install the previous client version** and confirm
- Check the project's GitHub issues for your exact version before spending hours on config
- Look at the client's own HDR/SDR settings (there are sliders and toggles that have caused flat-looking output on their own)

## Cause 2: a GPU driver break

Also reported: specific **Intel Windows driver** releases broke tone mapping; rolling the driver back fixed it. The same class of problem happens with Linux kernel/mesa/`intel-media-driver` updates and with NVIDIA driver jumps in containers.

How to tell: it started with a host update, not a Jellyfin update, and the FFmpeg log shows hardware filter errors.

What to do:
- **Roll the GPU driver back** to a known-good version and pin it
- On Linux, check `vainfo` still reports the expected profiles after the update
- In Docker, confirm the device is still passed through (`/dev/dri` present, correct group) — updates sometimes reset permissions and group IDs
- For NVIDIA in containers, re-check the container toolkit after host driver changes

## Cause 3: the server skips VPP/VA-API tone mapping for plain HDR10

There's a separate reported server bug where Jellyfin **doesn't use VPP/VA-API tone mapping for plain, non-Dolby-Vision HDR10** content, so those files come out untone-mapped while others are fine.

How to tell: it's **content-dependent** — some HDR files tone map correctly, plain HDR10 ones don't, on the same client and server.

What to do:
- Try the **OpenCL** tone-mapping path instead of VPP if your hardware supports it (Intel: install the compute runtime; the Jellyfin docs list the packages)
- Compare the FFmpeg command between a working file and a broken one — the filter chain difference is the evidence
- Track the server issue rather than rebuilding your setup around it

## A sane order of operations

1. Note **what updated** (client, server, GPU driver, kernel, container image) and when
2. Confirm the session is **transcoding** and hardware acceleration is active
3. Read the **FFmpeg log** for the failing session
4. Test the **same file on a different client**
5. Test a **different HDR file** on the same client
6. **Roll back** the one thing that changed, and pin it
7. Search GitHub issues with your exact versions

## What not to do

- Don't disable hardware acceleration "to simplify" — that removes tone mapping entirely
- Don't re-encode your library because of a two-week regression
- Don't change ten settings at once; you'll lose the thread
- Don't assume your TV is at fault before you've looked at the playback info

## FAQ

**Does Jellyfin tone map without hardware acceleration?**
No. Hardware acceleration is required for HDR→SDR tone mapping.

**Why do only some HDR files look wrong?**
Different HDR formats take different paths. Plain HDR10 has a reported bug where the VPP/VA-API tone-mapping path isn't used.

**Is it safe to downgrade the client?**
Generally yes for a media client; keep the server version and your config untouched so you're changing one variable.

**Should I switch to VPP or OpenCL tone mapping?**
Whichever your hardware supports properly. If one path is broken by a driver, trying the other is a legitimate diagnostic step.
