---
title: "MiSTer FPGA: Cores Not Loading"
slug: mister-core-not-loading
meta_description: "A blank screen on core load, cores that stopped working, or the SD card not recognised. Card integrity, the Linux folder, and power supply sag."
updated: October 2026
cluster: round 14 (tech) — MiSTer FPGA forum and MiSTer documentation
competition: LOW
---

# MiSTer FPGA: Cores Not Loading

Four causes, and the first two account for most of it. The MiSTer is unusually sensitive to card and power quality, which is why "it worked yesterday" is so common.

## 1. The SD card

MicroSD cards degrade, and the MiSTer writes to its card constantly. A card that boots the menu and fails on cores is a classic partial failure.

```bash
# over SSH to the MiSTer
dmesg | tail -30
df -h
mount | grep media
```

Look for I/O errors or a filesystem remounted read-only. Then:

- **Reseat the card.** The MiSTer fails to boot at all if it can't read the card, but a marginal contact gives intermittent core loads.
- **Try a different card.** Reported repeatedly as the resolution. Use a good-quality A1/A2 card; the cheapest cards fail fastest under this write pattern.
- **Don't copy a card file-by-file.** A documented point: manually copying files from one card to another **won't work** — you need an image-writing process that produces a bootable card with the correct filesystem and boot sector. Write the official SD installer image, then restore your games and saves on top.

## 2. The Linux folder

MicroSD corruption often lands in the `linux/` folder, which holds the kernel, device tree and the MiSTer binary. Cores then fail to load while the menu still works.

The documented repair: **copy and overwrite the `linux` folder from the latest SD-installer release.**

```bash
# from a PC, with the card mounted
rsync -av --delete /path/to/release/linux/ /media/MISTER/linux/
sync
```

Keep `linux/u-boot.img`, `linux/MiSTer`, `linux/zImage_dtb` and the `.dtb` files consistent — mixing versions is a reliable way to produce odd failures. Taking the whole folder from one release avoids that.

After overwriting, run the updater so cores and the menu match:

```bash
# on the MiSTer, via the menu or SSH
/media/fat/Scripts/update_all.sh
```

## 3. Power supply

This one is specific and widely confirmed: **an inline barrel switch drops voltage enough to prevent some cores loading.** Removing the switch resolves it.

More generally:

- Use a supply rated well above the nominal draw — the DE10-Nano plus USB peripherals plus an expansion board is more than a phone charger delivers cleanly.
- **Avoid inline switches, thin barrel cables and long extensions.** Voltage sag under the FPGA's reconfiguration current is exactly when a core fails to load.
- A core that loads with nothing plugged into USB and fails with a hub attached is a power problem, not a core problem.

The symptom profile: **different cores failing at different times**, with heavier cores (SNES, Neo Geo, PSX) failing more often than light ones. That's a supply that can't hold voltage during configuration.

## 4. Blank screen when the core loads

Distinct from the core not loading at all — the core *did* load and you can't see it.

```
Menu → System Settings → Video
```

- **Video mode mismatch.** Many cores output 15 kHz-era timings; a modern display may not sync. Set a scaler mode in `MiSTer.ini`:

```ini
[MiSTer]
video_mode=8
vsync_adjust=1
vscale_mode=0
```

`video_mode=8` is 1280x720@60, which almost any display accepts. Get a picture first, then experiment.

- **HDMI versus analogue (VGA/direct video).** With `direct_video=1` set and no analogue adapter, HDMI output is unusable:

```ini
direct_video=0
```

- **Per-core overrides.** `MiSTer.ini` supports core-specific sections; a stale override for one core gives a blank screen only there:

```ini
[NES]
video_mode=6
```

Remove it to test.

## 5. Cores stopped loading after an update

```bash
cat /media/fat/Scripts/.mister_updater/*.log | tail -40
```

- **A partial update.** `update_all.sh` interrupted mid-run leaves mismatched core and menu versions. Re-run it to completion on a stable network.
- **A core requiring a newer `linux/` than you have.** Cores track the main binary; an old `MiSTer` binary refuses new cores.
- **Out of space.** The card fills with ROMs and save states, and the updater can't write:

```bash
df -h /media/fat
```

## 6. SD card not recognised at all

```
# no boot at all, no menu
```

- The card isn't written with the official image (section 1).
- Exotic card formats: the MiSTer wants the standard partition layout the installer produces. Cards formatted exFAT in one partition won't boot.
- Very large cards (above 256 GB) have occasionally been troublesome; a 64–128 GB card is the well-trodden size.

## What not to do

- **Don't copy a card file-by-file.** Write the image.
- **Don't use an inline switch on the power supply.** It's a documented cause.
- **Don't mix `linux/` files from different releases.** Take the folder whole.
- **Don't fill the card.** Leave several gigabytes free for the updater and save states.

## Prevention

| Habit | Why |
|---|---|
| Quality A2 card, 64–128 GB, replaced when it misbehaves | Cards are consumable here |
| A generously-rated supply with a solid barrel connector | Removes the configuration-time sag class |
| `update_all.sh` run to completion, on a reliable network | Partial updates cause version mismatches |
| Back up `saves/`, `config/` and `MiSTer.ini` off the card | The only irreplaceable files |

## FAQ

**Does it need internet?**
Only for updates and online features. Cores run offline.

**Can I use a USB SSD instead of the SD card?**
Boot is from SD; games can live on USB storage, which reduces card wear considerably.

**Core loads, no sound.**
Audio output setting in `MiSTer.ini` (HDMI versus analogue) and the core's own audio options.

**How do I know the card is failing?**
`dmesg` I/O errors, a read-only remount, or saves that don't persist. Replace it rather than investigating further — it's cheap.
