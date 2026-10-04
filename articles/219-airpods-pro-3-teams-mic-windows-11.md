---
title: "AirPods Pro 3 Mic Not Working in Teams on Windows 11? The Hands-Free Profile Problem"
slug: airpods-pro-3-teams-mic-windows-11
meta_description: "AirPods show as connected with a mic, but Teams hears nothing on Windows 11. Why the Bluetooth profile is the cause, and the device-manager fix people report working."
updated: October 2026
cluster: round 10 (tech) — Microsoft Tech Community, Apple Community and MS Q&A threads only
competition: LOW
---

# AirPods Pro 3 Mic Not Working in Teams on Windows 11? The Hands-Free Profile Problem

The pattern, reported across Microsoft's and Apple's own forums and nowhere else: AirPods Pro 3 pair with a Windows 11 PC, show as **"Connected — voice, music"**, play audio perfectly, test fine in Sound settings — and then **Teams hears nothing**.

**This is a Bluetooth profile problem, not a broken microphone.**

## Why it happens

Windows exposes Bluetooth audio through two different profiles:

- **A2DP / Stereo** — high-quality playback, **no microphone**
- **Hands-Free (HFP/AG Audio)** — mono, lower quality, **microphone available**

Your PC creates a separate audio device for each. When Windows (or Teams) holds the AirPods on **Stereo**, the mic is simply not part of that profile — so there's nothing to capture, however connected the headset looks.

It gets worse with Teams, which manages its own device selection and can pick the playback device from one profile and expect a mic from the other.

## Fix 1: pick the Hands-Free device explicitly in Teams

**Teams → Settings → Devices.** You'll usually see two AirPods entries. Set:

- **Microphone**: the AirPods entry that corresponds to **Hands-Free AG Audio**
- **Speaker**: the same hands-free entry, if the stereo one won't give you a mic

Then **Make a test call** from the same screen. If the test call works but meetings don't, it's a Teams device-selection problem; if neither works, continue.

Also check Windows itself: **Settings → System → Sound → Input** — is the AirPods mic listed and not muted? And **Settings → Privacy & security → Microphone**, with access allowed for **Microsoft Teams** specifically. A denied app permission produces exactly this "device is fine, app hears nothing" picture.

## Fix 2: uninstall the device and let Windows rebuild it

The most-reported working fix in those forum threads:

1. **Device Manager** → **Sound, video and game controllers**
2. Find the **AirPods** entries, right-click → **Uninstall device** (do this for each AirPods entry you find; also check **Bluetooth** and **Audio inputs and outputs**)
3. Remove the AirPods from **Settings → Bluetooth & devices** as well
4. **Reboot**
5. Re-pair the AirPods from scratch

This clears a half-built device registration, which is what the symptom usually is.

## Fix 3: reinstall the Bluetooth driver

Also widely reported, especially on **Intel Wireless Bluetooth** adapters:

1. **Device Manager → Bluetooth → your adapter** → Uninstall device, and tick **"Attempt to remove the driver"** if offered
2. **Reboot** — Windows installs a clean driver on boot
3. Re-pair

If that doesn't hold, get the **vendor's** current driver (Intel, Realtek, MediaTek, or your laptop maker's support page) rather than relying on Windows Update's version. Bluetooth audio regressions are very often driver-level.

## Fix 4: the profile workarounds people resort to

- **Disable the "Handsfree Telephony" service** for the device in **Control Panel → Devices and Printers → AirPods → Properties → Services**. Counter-intuitive, but several people report Teams finally behaving after this — because it forces a single, unambiguous profile
- Or the reverse: **disable the stereo (A2DP) service** so only hands-free remains, guaranteeing a mic
- Accept a **wired or dongle headset** for meetings. Honest answer: AirPods on Windows are a second-class citizen, and no setting changes that

## Also worth checking

- **Windows 11 25H2**: one report says the problem resolved after upgrading. Install pending updates before deep troubleshooting
- **Firmware**: update the AirPods by pairing them to an iPhone/iPad for a while — there's no firmware update path from Windows
- **Teams classic vs new Teams**: device handling differs; test the other one
- **Other apps**: if Zoom/Meet get the mic and Teams doesn't, it's Teams device selection, not Bluetooth
- **Two PCs / a phone nearby** grabbing the AirPods mid-call — disconnect them from other devices

## FAQ

**Why do the AirPods say "mic" in Bluetooth settings but Teams hears nothing?**
The entry advertises mic capability; whether a mic is actually available depends on which profile is active at the time.

**Is this an AirPods Pro 3 fault?**
No. It's how Bluetooth audio profiles interact with Windows and Teams. Earlier AirPods have the same pattern.

**Will a Bluetooth dongle help?**
Often yes — a good-quality dongle with its own stack can be more reliable than a built-in adapter with a stale driver.

**Does this affect audio quality in calls?**
Yes. The hands-free profile is mono and low-bitrate by design — that's the trade for having a microphone at all.
