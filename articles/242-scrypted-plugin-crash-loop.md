---
title: "Scrypted Plugin in a Crash Loop? Isolate the Device, Not the Server"
slug: scrypted-plugin-crash-loop
meta_description: "A camera plugin restarting every few seconds can take the whole NVR with it. How to find the offending device from the logs, disable it safely, and stop the loop."
updated: October 2026
cluster: round 11 (tech) — Scrypted GitHub issues and discussions only
competition: LOW
---

# Scrypted Plugin in a Crash Loop? Isolate the Device, Not the Server

A plugin restarts every few seconds, the log scrolls with *"listen loop connection failed, restarting listener"*, and sometimes it drags the NVR API or the whole Scrypted process down with it.

**The fix is almost always to find the one device causing it and take it out of the loop** — not to reinstall Scrypted.

## Step 1: find which plugin, and which device

Scrypted's logs are per-plugin, which makes this quick:

1. Open the **plugin's own console** (Plugins → the plugin → Console)
2. Note the **device name or IP** that appears immediately before each restart
3. Check the device's console too (Devices → the camera → Console)

Patterns worth recognising:

| Log signature | What it usually is |
|---|---|
| `listen loop connection failed, restarting listener` every ~10s | A camera's event/AI subscription failing and being retried forever |
| `ffmpeg exited` repeatedly | Rebroadcast: a stream URL, codec or transport problem |
| `TypeError` / `undefined is not an object` then restart | A plugin bug on an unexpected device response |
| Crash shortly after startup, always same device | That device's config |
| Memory growth then kill | A leak, or too many streams for the host |

The reported Reolink case is the archetype: when the camera's AI-state call returns an error, the error path emits instead of returning, the listen loop restarts, and you get a permanent ~10-second crash cycle that also takes down the NVR API. One camera, whole system affected.

## Step 2: disable that one device

Don't uninstall the plugin — **disable the device**:

- Devices → the camera → **Disable** (or remove it from the plugin's device list)
- Restart the plugin
- If the loop stops, you've confirmed it

Now you have a working system and a single known-bad device, which is a much better position than a reinstall.

## Step 3: fix the device, not the software

For camera plugins, the usual culprits on the device side:

- **Firmware**: an old or a brand-new camera firmware changing an API response. Check the plugin's GitHub issues for your model and firmware
- **A feature the plugin polls that your model doesn't implement** — AI/object detection, two-way audio, floodlight. Turn that feature off for the device in the plugin settings
- **Credentials**: a separate, non-admin camera user that can't read the endpoint the plugin calls. Test with full credentials, then narrow
- **Too many concurrent connections** — cheap cameras allow very few; Scrypted plus a phone app plus an NVR exhausts them, and the plugin retries forever
- **Network**: a camera on a VLAN with partial reachability produces exactly this retry pattern

For Rebroadcast/FFmpeg loops:
- Try a **different stream** (substream instead of main), or **TCP instead of UDP** for RTSP
- Check the camera's **codec** (H.265 and B-frames are common troublemakers)
- Reduce **prebuffering** for that camera

## Step 4: update, or roll back, the plugin

- Update the plugin — many of these loops are fixed quickly once reported
- If the loop started with a plugin update, **install the previous version** from the plugin's page
- Check the project's **GitHub issues** with your plugin version and camera model. These are small projects; the issue is usually already there, often with a workaround in the thread

## Step 5: stop one plugin taking down everything

Structural protections worth setting up once:

- Run plugins that misbehave in their **own process** (Scrypted supports per-plugin isolation; check the plugin's settings for a separate-process option)
- Keep **NVR recording** separate in your head from camera integrations: if a camera plugin can take out the API, recordings are at risk too, so don't leave a known loop running overnight
- **Pin the Scrypted image/version** if you run it in Docker, and update deliberately
- Keep a **backup/export of your Scrypted settings** so a reinstall is cheap

## What not to do

- **Don't reinstall Scrypted** before isolating the device. You'll reproduce the loop immediately
- **Don't factory-reset the camera** as a first step
- **Don't leave it looping** — a 10-second restart cycle hammers the camera, fills logs and can mask other failures

## FAQ

**Why does one camera break the whole NVR?**
A restart loop in a shared listener can exhaust the plugin host and starve the API. That's why isolating the device matters more than restarting the server.

**Is it the plugin's fault or the camera's?**
Usually both: an unexpected device response plus an error path that retries instead of giving up. Reporting it with logs is how it gets fixed.

**Should I run plugins in separate processes?**
For the flaky ones, yes — it keeps a crash from taking neighbours down.

**My plugin crashes even with no devices.**
Then it's the plugin or its dependencies — reinstall that plugin, or roll it back, and check its issues.
