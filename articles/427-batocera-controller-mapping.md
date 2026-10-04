---
title: "Batocera: Controller Mapping Wrong in RetroArch"
slug: batocera-controller-mapping
meta_description: "Triggers don't work, one press registers twice, or mapping is wrong for one core. The two layers of mapping and which file to edit."
updated: October 2026
cluster: round 14 (tech) — batocera.linux GitHub issues and the Batocera wiki
competition: LOW
---

# Batocera: Controller Mapping Wrong in RetroArch

Batocera has **two** mapping layers, and knowing which one is wrong saves everything:

1. **Batocera's own input mapping** — `Settings → Controllers → Configure a controller`. This translates your physical pad to a RetroPad, and feeds every libretro core.
2. **RetroArch's per-core remap** — set inside the RetroArch menu during a game. Applies to that core or that game only.

A pad that's wrong **everywhere** is layer 1. A pad that's right in most systems and wrong in one is layer 2.

## 1. Start with Batocera's configuration

```
Settings → Controller & Bluetooth Settings → Configure a Controller
```

Walk the whole sequence, including the triggers and the hotkey. Skipping a button with a long press leaves it unmapped rather than ignored.

The result lands in:

```bash
cat /userdata/system/configs/emulationstation/es_input.cfg
```

That file is the source of truth for layer 1. A pad with two entries (added twice under slightly different names) can produce inconsistent behaviour — remove the stale one.

## 2. L2 / R2 triggers not working

A documented case, worth knowing because the fix is specific: RetroArch maps **L2 to axis +9 and R2 to +8** by default for some pads, and those mappings don't work on all hardware.

Edit the pad's entry in `es_input.cfg` to use the correct ids for your device. Find them first:

```bash
# list devices
ls /dev/input/by-id/
# watch raw events while pressing the triggers
evtest /dev/input/event5
```

`evtest` prints the exact event type, code and value per press. A trigger reporting as `ABS_Z`/`ABS_RZ` is an **axis**; one reporting `BTN_TL2`/`BTN_TR2` is a **button**. Mapping an axis trigger as a button (or the reverse) is what produces a dead trigger.

```xml
<inputConfig type="joystick" deviceName="My Pad" deviceGUID="...">
  <input name="l2" type="axis" id="2" value="1" />
  <input name="r2" type="axis" id="5" value="1" />
</inputConfig>
```

Back the file up before editing; a malformed `es_input.cfg` makes EmulationStation drop all controller config.

## 3. One press registering twice

Reported in two forms, with different causes.

**L2/R2 remapping to hat directions**, so a trigger press also sends a D-pad input. This is a mapping collision: the same physical event is bound to two logical inputs. Find it with `evtest` and remove the duplicate binding.

**A causing A+B, X causing X+Y** — characteristic of a pad whose buttons are reported on both a button and an axis, or of a device presenting as **two input devices** (a common trait of cheap pads and of some arcade encoders). Batocera then maps both, and every press is doubled.

```bash
ls -l /dev/input/by-id/ | grep -i joystick
```

Two entries for one physical pad is the giveaway. The fix is a `batocera.conf` override that ignores one:

```
# /userdata/system/batocera.conf
controllers.ps3.enabled=0
```

The exact key depends on the device; the wiki's DIY arcade controls page documents the pattern, and the generic approach is to blacklist the duplicate device via a udev rule:

```
# /userdata/system/udev/rules.d/99-ignore-dup.rules
SUBSYSTEM=="input", ATTRS{name}=="Generic USB Joystick", ENV{ID_INPUT_JOYSTICK}=""
```

## 4. Wrong mapping in one core only

This is layer 2, and the place to fix it is inside RetroArch:

```
During a game: hotkey + B (or the configured menu combo)
  → Controls → Port 1 Controls
  → set the mappings
  → Manage Remap Files → Save Core Remap File   (or Game Remap File)
```

Remaps are stored per core:

```bash
ls /userdata/system/configs/retroarch/config/remaps/
```

Reported specifically for **lr-mame**: wrong control mapping in the RetroArch GUI. MAME's own input system doesn't map cleanly onto a RetroPad for arcade layouts; a core remap, or MAME's internal input menu (TAB during a game), is the right tool. For arcade systems generally, MAME's own mapping is usually less painful than fighting the RetroPad abstraction.

**N64** is the other recurring case — the N64's analogue stick and C-buttons have no clean RetroPad equivalent, and every core maps them differently. Expect to set a per-core remap, and note that mupen64plus's standalone configuration differs from the libretro core's.

## 5. Nothing is detected at all

Before mapping, confirm Linux sees the pad:

```bash
cat /proc/bus/input/devices | grep -A4 -i joystick
jstest /dev/input/js0
```

- **Bluetooth pads** must be paired in Batocera's Bluetooth menu, and some need pairing each boot unless trust is stored.
- **Xbox wireless adapters** need the right dongle; the controller alone over Bluetooth behaves differently from the proprietary adapter.
- **USB hubs** — an unpowered hub with several pads browns out.

## What not to do

- **Don't edit `es_input.cfg` without a backup.** One syntax error loses every pad.
- **Don't remap in RetroArch to fix a problem that affects all systems.** Fix layer 1.
- **Don't map the hotkey to a button you use in games.** Select is conventional; Home on pads that have it is better.
- **Don't use two mapping layers for the same correction.** They compose, confusingly.

## Prevention

| Habit | Why |
|---|---|
| Back up `es_input.cfg` and `remaps/` | The two files that hold all your work |
| `evtest` before editing anything by hand | Tells you button versus axis definitively |
| One input device per physical pad (blacklist duplicates) | Removes the double-press class |
| Per-core remaps for N64 and arcade, not global changes | Those systems genuinely need their own |

## FAQ

**Does the mapping follow to standalone (non-libretro) emulators?**
Partly. Standalone emulators (PCSX2, Dolphin in some configurations, mupen64plus) have their own input configuration and may need separate setup.

**Can I use a keyboard?**
Yes, mapped the same way; `es_input.cfg` holds keyboard entries too.

**Different pads for different players?**
Each gets its own `es_input.cfg` entry by GUID; port order is set in Batocera's controller settings.

**Mapping resets after an update.**
It shouldn't — `/userdata` persists. If it does, the pad's GUID changed (a different firmware or a different port on some adapters) and a new entry was created.
