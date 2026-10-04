---
title: "WeeWX: \"Read Data From USB Failed\""
slug: weewx-usb-read-failed
meta_description: "The console works and WeeWX can't read it. Fine Offset lockups, AcuRite USB modes, cable quality and the kernel driver detach error."
updated: October 2026
cluster: round 14 (tech) — weewx-user group and weewx wiki
competition: LOW
---

# WeeWX: "Read Data From USB Failed"

The console keeps working while WeeWX can't talk to it. That pattern is characteristic and it points at a small set of causes — mostly the station's USB implementation rather than WeeWX.

```bash
sudo journalctl -u weewx -n 60 --no-pager
lsusb
dmesg | grep -i usb | tail -20
```

## 1. Fine Offset lockups

Fine Offset stations (and the many rebadges: Ambient Weather WH1080/WH1081, Watson, Maplin, Elecsa) **periodically stop responding on USB** while the console display continues normally. The characteristic log line:

```
could not detach kernel driver from interface 0: No data available
```

The documented explanation is a timing collision: the station writes to its own console memory and reads sensors every 48–60 seconds, and a USB read landing in that window can wedge the interface.

Recovery is physical and total:

1. Unplug USB
2. Remove the batteries
3. Wait 30 seconds
4. Reinsert batteries
5. Reconnect USB
6. Restart WeeWX

A software restart alone usually doesn't clear it. If it recurs weekly, the practical answers are a scheduled check that restarts WeeWX on repeated failures, or replacing the station with one that uses a serial or network interface. This is a known hardware limitation, not something to configure away.

## 2. AcuRite USB mode

AcuRite consoles have a mode selector, and **modes 1 and 2 disable USB data**. The WeeWX driver needs **mode 3 or 4**:

- Mode 1/2 — display only, USB data off
- Mode 3 — USB data, no logging
- Mode 4 — USB data plus logging

If `lsusb` shows the console but every read fails, check the mode before anything else. It is a button press on the console.

## 3. Cable, hub and bus quality

Many bad USB reads in a short window is a physical-layer symptom:

```
weewx[1234] ERROR weewx.drivers.fousb: bad USB read
```

In order of likelihood:

- **The cable.** Weather station cables are often thin and long. Replace it with a short, known-good one.
- **A hub.** Remove it; connect directly.
- **Other devices on the same bus.** A USB 3 device adjacent to the station's port injects noise; move it.
- **Power.** On a Raspberry Pi with an underpowered supply, the bus browns out under load.

A handful of bad reads per day is normal for several station types and WeeWX retries. Dozens per hour is a fault.

## 4. Permissions and udev

WeeWX runs as a non-root user and needs access to the device:

```bash
# find the vendor:product
lsusb | grep -i 'weather\|1941\|24c0'
```

```
# /etc/udev/rules.d/60-weewx.rules
SUBSYSTEM=="usb", ATTR{idVendor}=="1941", ATTR{idProduct}=="8021", MODE="0664", GROUP="weewx"
```

```bash
sudo udevadm control --reload-rules && sudo udevadm trigger
```

A permission failure gives a clean, immediate error on startup rather than intermittent read failures — if WeeWX never reads successfully even once, start here.

## 5. pyusb version

An older but still-encountered issue: **python-usb 1.x incompatibility** with some drivers, where downgrading to 0.4 restored operation. If you're on a recent WeeWX with a recent pyusb this shouldn't apply, but if you've just migrated a long-running install to a new OS and reads fail immediately:

```bash
python3 -c "import usb; print(usb.__version__)"
```

Check the driver's own requirements rather than guessing — mismatches here are version-specific and the WeeWX wiki tracks them.

## 6. Confirm it isn't the driver choice

A wrong driver talks to the right device and gets nothing useful:

```bash
sudo weectl device --info
```

```ini
# weewx.conf
[Station]
    station_type = FineOffsetUSB

[FineOffsetUSB]
    driver = weewx.drivers.fousb
    polling_mode = PERIODIC
    polling_interval = 60
```

`polling_mode = ADAPTIVE` reads as soon as the station has new data and is more efficient; `PERIODIC` is more robust against the lockup in section 1 because it avoids the station's own busy window. If you're fighting lockups, `PERIODIC` with a 60-second interval is the safer setting.

## What not to do

- **Don't run WeeWX as root to fix permissions.** Write a udev rule.
- **Don't poll faster to get more data.** More reads means more collisions with the station's internal cycle.
- **Don't ignore repeated bad reads.** They precede a lockup.
- **Don't replace the station before trying a different cable.** It's the cheapest fix and often the right one.

## Prevention

| Habit | Why |
|---|---|
| Short, good-quality USB cable, no hub | Eliminates most bad reads |
| `PERIODIC` polling at 60 s on Fine Offset hardware | Avoids the station's busy window |
| A watchdog that restarts WeeWX after N failures | Turns a lockout into a gap, not an outage |
| Prefer network or serial stations for new builds | USB HID weather stations are the fragile option |

## FAQ

**Does this affect Davis Vantage stations?**
Different driver and a serial/USB-serial interface; its failures look different (`Unable to wake up console`) and usually mean baud rate or a dead datalogger battery.

**Will I lose data during a lockout?**
Stations with internal logging catch up when WeeWX reconnects. Those without lose the gap.

**Can I run WeeWX in Docker?**
Yes, with the USB device passed through. The lockup behaviour is unchanged.

**How do I tell a station fault from a WeeWX fault?**
If the console display is updating and WeeWX can't read, it's the USB interface. If the console itself is stale, it's the sensors or their radio link.
