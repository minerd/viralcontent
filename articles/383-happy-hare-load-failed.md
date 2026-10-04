---
title: "Happy Hare: Filament Load Failed at the Gate"
slug: happy-hare-load-failed
meta_description: "Loads fail at the gate, at the extruder, or report slippage. Which sensor didn't trigger, the calibration that fixes it, and the gate-empty logic."
updated: October 2026
cluster: round 14 (tech) — moggieuk/Happy-Hare GitHub issues and wiki
competition: LOW
---

# Happy Hare: Filament Load Failed at the Gate

Happy Hare's load sequence is a chain of sensor checks. The error names the step that failed, and that tells you which sensor and which calibration to look at.

| Error | Step that failed |
|---|---|
| `Filament not detected in gate` | Gate sensor / encoder at the gate |
| `Failed to reach extruder` | Bowden move length |
| `Failed to reach toolhead sensor after moving Xmm` | Extruder-to-nozzle distance |
| `Excess slippage detected` | Encoder vs. gear movement |

```
MMU_STATUS
MMU_SENSORS
```

`MMU_SENSORS` prints the live state of every sensor Happy Hare knows about. Run it with filament in and out of the gate and watch the values change — a sensor that never changes is wired wrong or configured on the wrong pin.

## 1. Gate loading fails: the gate endstop doesn't trigger

```
Gate 3 marked as empty
```

Happy Hare marks a gate empty when the gate sensor (or the encoder) sees no filament after the selector moves and the gear tries to feed.

Checks, in order:

- **Is the sensor actually triggering?** `MMU_SENSORS` with filament pushed in by hand.
- **Selector alignment.** If the selector isn't centred on the gate, the filament pushes against the body rather than into the path. Re-run selector calibration:

```
MMU_CALIBRATE_SELECTOR
```

- **Filament tip shape.** A blob or a hook from a previous unload will not enter the gate. This is the single most common mechanical cause, and it's why tip forming matters so much on an MMU.
- **Gear grip.** Worn or poorly tensioned drive gears slip without moving filament. The encoder sees nothing and reports empty.

Important behavioural note: **a failed pickup is not automatically treated as "empty"**. Happy Hare distinguishes between a gate that is genuinely out of filament and one that failed to grip, and that logic depends on the encoder being calibrated. An uncalibrated encoder makes every failure look like an empty gate.

```
MMU_CALIBRATE_ENCODER
```

Do this before chasing anything else; a large share of load failures resolve with a correct encoder calibration.

## 2. "Failed to reach extruder"

The bowden move length is wrong. Calibrate it per gate:

```
MMU_CALIBRATE_BOWDEN
```

and for the rest:

```
MMU_CALIBRATE_GATES
```

The length must be slightly **less** than the physical distance, so the final approach is a slow homing move rather than a blind push. Too long and the filament buckles at the extruder entrance; too short and it never arrives.

**Slippage** reported during the bowden move means the gear moved more than the encoder measured:

```
Excess slippage detected in bowden: gear moved 450mm, encoder measured 390mm
```

Causes: bowden friction (too tight a bend, a kinked tube), gear tension, or an encoder with a dirty wheel. Clean the encoder wheel and check the tube routing before adjusting tolerances.

## 3. "Failed to reach toolhead sensor"

```
Failed to reach toolhead sensor after moving 40.0mm
```

The configured extruder-to-sensor distance doesn't match reality.

```ini
# mmu_parameters.cfg
toolhead_extruder_to_nozzle: 72
toolhead_sensor_to_nozzle: 62
toolhead_entry_to_extruder: 15
```

Measure these on your actual toolhead — they differ between every hotend and extruder combination, and copying someone else's numbers is the usual reason this step fails. The wiki's measurement procedure (push filament to the nozzle, mark, retract to the sensor, measure) takes ten minutes and is worth doing properly once.

With **both** an extruder entry sensor and a toolhead sensor configured, the behaviour changes: Happy Hare homes to each in turn, and an incorrect `toolhead_entry_to_extruder` makes the second homing move start from the wrong place. If you have both sensors and loads fail only at the toolhead, this value is the suspect.

## 4. Sporadic unload failures

Unload failures that happen occasionally rather than always are nearly all **tip forming**:

```ini
[gcode_macro _MMU_FORM_TIP_STANDALONE]
variable_final_eject: 0
variable_cooling_moves: 4
variable_initial_cooling_temp: 0
```

A tip with a blob won't re-enter the gate; a tip with a long thin string catches in the bowden. Tune cooling moves and the ramming sequence for your filament, and test with `MMU_FORM_TIP` plus a visual check of the tip — don't tune it blind inside a print.

An alternative that sidesteps tip forming entirely is a filament cutter at the toolhead or the gate, which Happy Hare supports and which removes this whole class of failure.

## 5. "MMU in error but the print doesn't stop"

Reported behaviour worth knowing: an MMU error state that doesn't pause the print. Make sure the pause/resume integration is configured, and check that your slicer's tool-change gcode goes through Happy Hare's macros rather than calling `T0`/`T1` directly to the firmware.

## What not to do

- **Don't widen tolerances to get past a failure.** You convert a hard stop into a mid-print jam.
- **Don't calibrate the bowden before the encoder.** Every length measurement depends on the encoder being right.
- **Don't copy `toolhead_*` distances from another machine.** Measure yours.
- **Don't tune tip forming during a real print.** Use `MMU_FORM_TIP` and inspect.

## Prevention

| Habit | Why |
|---|---|
| Encoder calibration first, re-checked after any gear change | Everything else depends on it |
| Measured toolhead distances, written in a comment | The commonest cause of toolhead-sensor failures |
| `MMU_CHECK_GATES` before a multi-colour print | Finds empty or mis-seated gates before hour three |
| Clean cut tips, or a cutter | Removes most sporadic failures |

## FAQ

**Does `MMU_CHECK_GATE` have to pause the print?**
There's an option to substitute an EndlessSpool gate instead of pausing, which is the better behaviour for long prints with spares loaded.

**Can I run without an encoder?**
Some configurations allow sensor-only operation, but you lose slippage detection and the empty-versus-failed distinction.

**Filament loads but prints show colour bleed.**
Purge volume, not loading. That's a slicer setting.

**Which sensor set is best?**
Gate sensor plus toolhead sensor is the most robust combination; it gives homing points at both ends of the bowden.
