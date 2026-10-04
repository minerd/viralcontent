---
title: "Frigate Coral TPU Not Detected After an Update? Check Protection Mode First"
slug: frigate-coral-not-detected-after-update
meta_description: "'No EdgeTPU was detected' after upgrading Frigate is often the Home Assistant add-on's Protection mode switching back on. Then device passthrough, USB power and version pinning."
updated: October 2026
cluster: round 9 (tech) — GitHub discussions only
competition: LOW
---

# Frigate Coral TPU Not Detected After an Update? Check Protection Mode First

You upgrade Frigate, and detection stops: **"No EdgeTPU was detected"**, the detector fails to start, or Frigate crash-loops. The GitHub discussions are full of this after nearly every release.

Work through it in this order.

## 1. Home Assistant add-on: Protection mode

If you run Frigate as a **Home Assistant add-on**, this is the first thing to check and the most common cause after an upgrade.

The Coral needs direct hardware access, which means the **Full Access** variant of the add-on with **Protection mode OFF**. Upgrades have re-enabled Protection mode, and the Coral disappears.

- Home Assistant → **Settings → Add-ons → Frigate (Full Access)**
- Turn **Protection mode off**
- **Restart** the add-on

Several people report that alone fixing it.

## 2. Is the TPU visible to the host at all?

Check below Frigate before changing Frigate's config:

**USB Coral**
```
lsusb
```
Look for Global Unichip Corp. (before first use) or Google Inc. (after it's been initialised). The ID changing between those two is normal and confuses people — it's the device switching to its runtime mode.

**PCIe / M.2 Coral**
```
ls /dev/apex_0
dmesg | grep -i apex
```
No `/dev/apex_0` means the `gasket`/`apex` driver isn't loaded or didn't rebuild after a **kernel update** — which is its own very common cause. Rebuild/reinstall the gasket DKMS modules for the running kernel.

If the host can't see it, no amount of Frigate configuration will help.

## 3. Device passthrough in Docker/Compose

Updates and config regeneration lose these more often than you'd expect:

```yaml
# USB Coral
devices:
  - /dev/bus/usb:/dev/bus/usb
# PCIe/M.2 Coral
devices:
  - /dev/apex_0:/dev/apex_0
```

Also check:
- The container has the **permissions/group** it needs for the device
- You didn't switch to a different image variant in the upgrade
- On USB, the device node moves when it re-enumerates — passing the whole `/dev/bus/usb` tree is more robust than a single path

## 4. USB power and cabling

A USB Coral can draw up to about **900 mA**, more than some ports and most hubs supply. Symptoms are intermittent: works, then drops out under load, often after a reboot.

- Use a **USB 3 port directly** on the host
- Use a **short, good-quality** cable (the supplied one, ideally)
- Use a **powered** hub if you must use one
- On a Pi, consider the power budget for everything else attached

## 5. The version you upgraded to

Several Frigate releases have had Coral detection regressions, reported across multiple version jumps. If the host sees the TPU, passthrough is right, and Protection mode is off:

- Check the **GitHub discussions and release notes for your exact version**
- **Pin the previous working image tag** and confirm the behaviour reverses
- Report it with your logs if it's new

Pin a specific tag rather than `latest`, so that an unattended image pull can't take your NVR's detection down.

## 6. Read the detector startup log

```
docker logs frigate 2>&1 | head -100
```
The startup lines name the detector type and the error. "No EdgeTPU was detected" is a device/permission problem. A detector that starts and then **times out** points at power, overheating, or a config mismatch (wrong `type:`, wrong device string, model/edgetpu mismatch).

## Quick table

| Symptom | Most likely |
|---|---|
| Worked before upgrade, HA add-on | Protection mode re-enabled |
| `/dev/apex_0` missing after host update | gasket driver didn't rebuild for the new kernel |
| `lsusb` shows nothing | Cable, port, power |
| Host sees it, container doesn't | Device passthrough / permissions |
| Starts then drops under load | USB power or overheating |
| Everything correct, still nothing | Version regression — pin the previous tag |

## FAQ

**Why does the Coral's USB ID change?**
It presents as Global Unichip before initialisation and Google Inc. afterwards. Both are normal.

**Do I need Protection mode off permanently?**
For the Coral with the Home Assistant add-on, yes — that's what gives the container hardware access.

**Can I run Frigate without a Coral?**
Yes, with CPU detection (slow, not recommended for several cameras) or another accelerator such as OpenVINO on supported Intel hardware.

**Should I use `latest` for the Frigate image?**
No. Pin a version you've tested, so an unexpected pull can't break detection while you're away.
