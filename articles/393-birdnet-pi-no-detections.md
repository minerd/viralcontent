---
title: "BirdNET-Pi: Analysing But No Detections"
slug: birdnet-pi-no-detections
meta_description: "The spectrogram is blank, or analysis runs with zero results. Microphone input after a reboot, PoE interference, gain and the confidence threshold."
updated: October 2026
cluster: round 14 (tech) — mcguirepr89/BirdNET-Pi discussions
competition: LOW
---

# BirdNET-Pi: Analysing But No Detections

The first thing to establish is whether it's **hearing anything at all**, because "no detections" and "no audio" look identical in the UI.

Look at the **live spectrogram**. A blank or flat-line spectrogram means no audio; a spectrogram full of broadband noise means audio with a problem; a spectrogram showing bird calls with no detections means a threshold or model issue.

## 1. No audio: the microphone after a reboot

A documented and recurring failure: **after a reboot or a crash, BirdNET-Pi comes back with no sound input**, producing blank spectrograms, while the hardware is fine.

```bash
arecord -l
arecord -D plughw:1,0 -f S16_LE -r 48000 -c 1 -d 5 /tmp/test.wav
aplay /tmp/test.wav
```

If `arecord` captures audio and BirdNET-Pi doesn't, the service grabbed the device before it enumerated, or grabbed a different one. Restart the services in order:

```bash
sudo systemctl restart birdnet_recording.service
sudo systemctl restart birdnet_analysis.service
```

If that doesn't help, unplugging and replugging the USB microphone and then restarting is the reported remedy. For a device that moves between `plughw:1,0` and `plughw:2,0` across reboots, set it by name in the BirdNET-Pi settings rather than by number — the same stability rule that applies to every USB audio device.

## 2. Broadband noise: PoE and power interference

A specific, well-documented cause: **a PoE switch feeding the Pi injects noise into the audio path**, and the recording is unusable even though levels look healthy. Switching to a plain USB-C power supply resolved it and detections resumed.

The same applies to:

- Cheap USB chargers with poor filtering
- A Pi powered from a PoE splitter
- Long unshielded USB extensions for the microphone

Listen to the recordings. BirdNET-Pi keeps them:

```bash
ls -lt ~/BirdSongs/Extracted/By_Date/ | head
```

Play one. Hum, hiss or a constant tone means the problem is electrical, not algorithmic — and no setting will fix it.

## 3. Levels and gain

```bash
alsamixer -c 1
```

Set the **capture** level (press F4 for capture controls). Both extremes cause trouble:

- Too low — quiet calls fall below the model's threshold
- Too high — clipping destroys the structure the model matches on

Aim for peaks around −12 to −6 dBFS on a loud nearby call, not at 0. BirdNET-Pi's own settings also expose a recording gain; set the hardware level first and leave software gain near neutral.

## 4. Settings that suppress detections

In BirdNET-Pi's **Settings**:

- **Confidence threshold.** The default is conservative. Lowering it to 0.6–0.7 surfaces more detections at the cost of false positives — reasonable while you're validating that the pipeline works at all, then raise it.
- **Latitude / longitude** must be set. The model uses location and week-of-year to weight species probability; wrong coordinates suppress the birds that are actually outside your window.
- **Species occurrence frequency / "include list".** An over-aggressive filter excludes common local species.
- **Overlap** — a small overlap between analysis windows catches calls that straddle a boundary.

## 5. "Constantly analysing" and never catching up

A real capacity problem: if the Pi records continuously and analysis is slower than real time, the queue grows forever and recent detections never appear.

```bash
top -b -n1 | head -15
uptime
```

On a Pi 3 or a Pi Zero 2, continuous analysis at the default settings is borderline. Options:

- A Pi 4 or 5
- Reduce the analysis load in settings (fewer overlapping windows)
- Accept gaps

If the load average sits above the core count permanently, that's the whole explanation for "analysing, no results".

## 6. Disk and database

```bash
df -h
du -sh ~/BirdSongs
```

A full SD card stops extraction and the database write. BirdNET-Pi accumulates audio clips; without a purge policy, a 32 GB card fills in weeks. There's a setting for how many days of recordings to keep — set it.

## What not to do

- **Don't reflash the SD card first.** It's the reported last resort for a reason; almost everything here is a two-minute fix.
- **Don't power the Pi from PoE** for this application.
- **Don't push the confidence threshold very low and leave it.** You'll fill the database with misidentifications and lose trust in the data.
- **Don't mount the microphone against a wall or inside a box.** Reflections and wind noise dominate.

## Prevention

| Habit | Why |
|---|---|
| Clean USB-C power supply, not PoE | Removes the interference class entirely |
| Microphone device set by name, not number | Survives reboots |
| Retention limit on recordings | SD cards fill faster than you expect |
| Listen to a recording monthly | The fastest check that the whole chain works |

## FAQ
**Which microphone works well?**
A USB lavalier or a dedicated outdoor capsule with a windscreen. The windscreen matters more than the capsule.

**Can it run on something other than a Pi?**
Yes — BirdNET-Go and the Docker variants run on x86, with far more analysis headroom.

**Detections are wrong species.**
Check latitude/longitude and raise the confidence threshold. Location weighting is doing a lot of work.

**Does it need internet?**
No for analysis. Yes for the species images, and for pushing to BirdWeather if you've enabled it.
