---
title: "Home Assistant Connect ZBT-1 / SkyConnect: Firmware Update Failed"
slug: zbt1-firmware-update-failed
meta_description: "The firmware update fails or hangs because the dongle serves one consumer at a time. What to disable first, and the recovery path if it's half-flashed."
updated: October 2026
cluster: round 13 (tech) — HA community and ZBT-1 GitHub issues
competition: LOW
---

# Home Assistant Connect ZBT-1 / SkyConnect: Firmware Update Failed

The reason this fails is simple and almost always the same:

> **The dongle's serial port can serve only one consumer at a time.** If ZHA or Zigbee2MQTT (or Thread/OTBR) has it open, the firmware updater cannot.

So the fix is an order of operations, not a setting.

## 1. Stop everything that holds the port

Before starting any firmware update:

- **ZHA**: Settings → Devices & Services → ZHA → ⋮ → **Disable**. Not "reload" — disable.
- **Zigbee2MQTT**: stop the add-on or container entirely.
- **OpenThread Border Router** add-on: stop it. On multiprotocol firmware, OTBR and ZHA both hold the device.
- **Matter Server**: stop it if it was using the Thread side.
- Any `socat`/`ser2net` bridge, any terminal with the port open.

Then update: **Settings → Devices & Services → Home Assistant Connect ZBT-1 → the firmware card → Update**.

If the update still fails immediately, something is still holding it. Confirm from a terminal on the host:

```bash
ls -l /dev/serial/by-id/
sudo fuser -v /dev/ttyUSB0
sudo lsof /dev/ttyUSB0
```

Anything listed must be stopped. In HA OS you may not have `fuser`; the practical equivalent is to stop every add-on that could touch it and retry.

## 2. Pick the right firmware for what you want

The ZBT-1 runs one of three firmwares, and they're mutually exclusive in practice:

| Firmware | For |
|---|---|
| **Zigbee (EmberZNet)** | ZHA or Zigbee2MQTT. The default and the one most people want. |
| **Thread (OpenThread RCP)** | Matter over Thread, via OTBR |
| **Multiprotocol** | Both at once — and generally **not recommended** |

Multiprotocol sounds appealing and causes real problems: both radios share one 2.4 GHz front end, so Zigbee reliability drops noticeably, and it has been the source of a long tail of hard-to-diagnose dropouts. If you want Zigbee *and* Thread, two dongles (physically separated) is the configuration that works.

Switching firmware **erases the network**. A Zigbee network's keys live on the coordinator, so flashing Thread firmware and back means re-pairing every device unless you restored a backup. Take one first:

- ZHA: Settings → Devices & Services → ZHA → ⋮ → Download diagnostics includes the network backup, and HA keeps automatic coordinator backups
- Zigbee2MQTT: `coordinator_backup.json` in its data directory

## 3. USB — the physical half

The ZBT-1 is sensitive to its port, and firmware updates are where marginal connections show up:

- **Use a USB 2.0 port.** USB 3 ports generate 2.4 GHz noise that degrades range badly, and on some hosts cause enumeration problems during flashing.
- **Use the supplied extension cable.** Directly in the back of a mini PC or a Pi, next to an SSD, is the worst case for both interference and heat.
- **Avoid unpowered hubs** for the update. A voltage dip mid-flash is how you get a half-flashed dongle.
- **Check for disconnects:**

```bash
dmesg -T | grep -i 'usb\|cp210\|ttyUSB' | tail -20
```

A `USB disconnect` during the update is your answer.

## 4. Virtualised installs

In Proxmox/ESXi/Hyper-V, the dongle must be passed through to the VM, and the firmware updater needs the same exclusive access:

```
# Proxmox: pass by vendor:product so it survives reboots
qm set 100 -usb0 host=10c4:ea60
```

The update can fail in a VM even with nothing else using the port, because USB passthrough adds latency and some hypervisor configurations reset the device on bus events. If updates repeatedly fail under virtualisation, the reliable route is to flash it from a bare-metal machine:

- Attach the dongle to a desktop
- Use the web-based flashing tool from a Chromium-based browser (it uses WebSerial and needs no local install)
- Return it to the server

That path avoids the whole passthrough question and is worth going to directly rather than after five failed attempts.

## 5. If it's half-flashed

A dongle that failed mid-update may come up in bootloader mode and not appear as a working radio. It is recoverable:

- It still enumerates as a serial device (`/dev/ttyUSB0`, CP210x).
- The web flasher detects a device in bootloader mode and offers to write firmware.
- Hold the **BOOT** button while plugging it in to force bootloader mode if it doesn't present itself.

Do not conclude it's bricked because HA no longer lists a radio. Check `lsusb` and `dmesg` first — if the USB-serial chip enumerates, the device is flashable.

## What not to do

- **Don't update with ZHA running.** This is the cause, not a precaution.
- **Don't choose multiprotocol firmware** unless you've accepted the Zigbee reliability cost. Two dongles is the better answer.
- **Don't switch firmware without a coordinator backup.** Re-pairing forty devices is a weekend.
- **Don't power-cycle the host mid-update.** Let it fail cleanly; a failed update is recoverable, an interrupted one at the wrong moment is more work.

## Prevention

| Habit | Why |
|---|---|
| Coordinator backup before any firmware or coordinator change | The only thing that saves your network |
| USB 2 port on an extension cable | Range, stability and clean flashing |
| Disable ZHA/Z2M as step one of any dongle work | Removes the single-consumer conflict |
| Keep a note of which firmware is on which dongle | Prevents flashing the wrong one |

## FAQ

**Do I need to update the firmware at all?**
Only when a new ZHA/Z2M version requires it, or to fix a specific bug. A stable network on older firmware is fine.

**ZBT-1 or SkyConnect — same thing?**
Same hardware, renamed. Instructions are interchangeable.

**After updating, my devices are gone.**
If you changed firmware type, the network was erased — restore the coordinator backup. If you updated within Zigbee firmware, devices should persist; re-enable ZHA and give it a few minutes.

**Can I use it for Thread and a separate dongle for Zigbee?**
Yes, and that's the recommended layout. Keep them physically apart, each on a USB 2 extension.
