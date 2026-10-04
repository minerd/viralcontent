---
title: "Klipper: \"Probe triggered prior to movement\""
slug: klipper-probe-triggered-prior-to-movement
meta_description: "The error means the probe reads triggered before the move starts. Which of the five causes you have, and how to tell in one command."
updated: October 2026
cluster: round 14 (tech) — Klipper GitHub issues and Discourse
competition: LOW
---

# Klipper: "Probe triggered prior to movement"

Klipper checks the probe's state **before** it starts each probing move. If it already reads triggered, it aborts rather than crashing the nozzle into the bed. So the message is not "the probe failed" — it is "the probe says it is touching something right now."

One command tells you most of what you need:

```
QUERY_PROBE
```

```
probe: TRIGGERED
```

With the toolhead clear of the bed, `TRIGGERED` is wrong, and that narrows it to a wiring or configuration problem rather than a mechanical one.

## 1. If QUERY_PROBE reads TRIGGERED with nothing near the bed

**Inverted logic.** The `!` prefix inverts the pin. An NPN NO sensor, an NC switch and a BLTouch all want different combinations:

```ini
[probe]
pin: ^!PA0        # ^ = pull-up, ! = invert
```

Remove or add the `!` and re-run `QUERY_PROBE`. The reading should flip. If it doesn't flip, the pin isn't reading the sensor at all — wrong pin name or a broken wire.

**Missing pull-up.** A bare mechanical switch without `^` floats and reads randomly. Add `^`.

**BLTouch in alarm.** A BLTouch flashing red is in alarm state and reports triggered permanently:

```
BLTOUCH_DEBUG COMMAND=reset
BLTOUCH_DEBUG COMMAND=pin_up
QUERY_PROBE
```

Alarm usually means the pin is stuck (clean it, check for filament debris) or the probe was pushed up while the machine was off.

**Inductive probe too close to the bed.** A PINDA/PL-08 mounted 1 mm from the bed is permanently within range. 1.5–2 mm off the nozzle tip is the usual target; verify by watching the LED while raising Z.

## 2. If QUERY_PROBE reads open but the error appears mid-mesh

Now it is mechanical, and it happens between probe points.

- **`lift_speed` and `sample_retract_dist` too small.** Klipper retracts, moves, probes again. If the retract is 2 mm and your bed is 1 mm out of level, the probe is still touching when the next move begins:

```ini
[probe]
sample_retract_dist: 3.0
lift_speed: 10
samples: 2
samples_tolerance: 0.01
samples_tolerance_retries: 3
```

- **Klicky/Euclid dock probes not attached.** A magnetically-docked probe that fell off mid-run reports triggered. Check the dock geometry and magnet strength, and clean old filament off the mating faces — this is the most reported cause for dockable probes.
- **Bed mesh area outside the probe's reach.** With a probe offset of +30 mm in X, a `mesh_min` at X=0 asks the toolhead to move to X=−30. Klipper will complain, and in some configurations the probe clips the bed edge:

```ini
[bed_mesh]
mesh_min: 35, 35
mesh_max: 285, 285
probe_count: 5,5
```

Account for `x_offset`/`y_offset` in the mesh bounds.

- **Z endstop and probe both wired, both configured.** If `[stepper_z] endstop_pin: probe:z_virtual_endstop` and you also have a physical Z switch connected to the same pin, both pull it.

## 3. Check repeatability before trusting anything

```
PROBE_ACCURACY
```

```
probe accuracy results: maximum 2.512500, minimum 2.505000,
range 0.007500, average 2.508750, standard deviation 0.002372
```

A standard deviation under about 0.005 mm is healthy. Above 0.02 mm you have a mechanical problem — a loose probe mount, a flexing gantry, or a failing sensor — and bed mesh will be meaningless even when it completes.

## What not to do

- **Don't raise `samples_tolerance` to make it pass.** You are hiding a bad probe.
- **Don't run `BED_MESH_CALIBRATE` to diagnose.** Use `QUERY_PROBE` and `PROBE_ACCURACY`; they isolate the fault.
- **Don't flip the `!` randomly and leave it.** Confirm with `QUERY_PROBE` in both the raised and manually-triggered states.
- **Don't ignore an alarming BLTouch.** Reset it and find out why.

## Prevention

| Habit | Why |
|---|---|
| `QUERY_PROBE` after any probe wiring change | Catches inverted logic in five seconds |
| `PROBE_ACCURACY` monthly | Detects a loosening mount before it ruins prints |
| `sample_retract_dist: 3` as a default | Tolerates a bed that isn't perfectly level |
| Mesh bounds that account for the probe offset | Removes the edge-of-bed class |

## FAQ

**Can I probe with the nozzle instead?**
Yes, with a load-cell or strain-gauge setup. Different config, same pre-move check.

**The error appears only when the bed is hot.**
Thermal drift in the mount, or a wire pulling as the gantry expands. Check the probe's Z reading cold and hot with `PROBE_ACCURACY`.

**Does a `z_offset` of 0 cause this?**
No, but it will drive the nozzle into the bed on the first print. Run `PROBE_CALIBRATE` before printing.

**Works on one half of the bed only.**
Physical: either the probe is clipping something, or the gantry is tilted enough that retract distance runs out mid-mesh.
