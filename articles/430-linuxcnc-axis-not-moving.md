---
title: "LinuxCNC: Steppers Work in Stepconf But Not in AXIS"
slug: linuxcnc-axis-not-moving
meta_description: "The Stepconf test moves the motors and the GUI doesn't. The amplifier-enable inversion nobody expects, plus following-error causes."
updated: October 2026
cluster: round 14 (tech) — LinuxCNC forum and documentation
competition: LOW
---

# LinuxCNC: Steppers Work in Stepconf But Not in AXIS

This exact pattern has one dominant cause, and it is counter-intuitive:

> **Stepconf's axis test does not drive the amplifier-enable signal. AXIS does.** Many stepper drivers' "enable" input is actually a *disable*, so when AXIS asserts enable, it switches the drives off.

That's why the test works and the real application doesn't.

## 1. Invert the enable signal

```ini
# the .hal file, or via Stepconf's pin configuration
net estop-out => parport.0.pin-01-out
setp parport.0.pin-01-out-invert 1
```

In Stepconf's parallel-port pin dialogue, each pin has an **Invert** checkbox. Tick it for the amplifier-enable pin and re-test in AXIS.

The documented alternatives, both valid:

- **Invert the enable signal** so the polarity matches your drives.
- **Disconnect amplifier enable entirely** while testing, since Stepconf doesn't use it. If the motors then run in AXIS, you've confirmed the diagnosis.

Many drivers also have a charge-pump requirement or an enable that must be *actively* held. Check the driver's datasheet for whether the input is active-high or active-low — that one line of documentation resolves this faster than any amount of configuration.

## 2. Make sure the machine is actually enabled

Before blaming the signal chain, confirm the software state:

- **E-stop cleared** (F1), then **machine on** (F2). An un-homed, powered-off machine ignores jog commands silently.
- **Homing.** With `HOME_SEQUENCE` configured, axes must be homed before coordinated motion. Jogging usually works un-homed; a G-code run won't.
- **Limit switches tripped.** A switch stuck active holds the axis in a fault state. `halmeter` on the limit pin tells you:

```bash
halmeter
# add pin: parport.0.pin-10-in
```

`halmeter` and `halshow` are the tools for this — they show live pin state, which removes all guesswork about polarity.

## 3. Following errors

```
joint 0 following error
```

LinuxCNC compares commanded and expected position and faults when they diverge. On a **stepper** system there is no feedback, so a following error means LinuxCNC calculated it cannot keep up — a configuration problem, not a mechanical one.

```ini
[JOINT_0]
TYPE = LINEAR
MAX_VELOCITY = 25.0
MAX_ACCELERATION = 250.0
STEPGEN_MAXACCEL = 312.5
FERROR = 0.05
MIN_FERROR = 0.01
```

The documented causes, in order:

- **`FERROR` or `MIN_FERROR` too small** — tighten only after everything else is right.
- **`MAX_VELOCITY` too high** for your step timings. The step rate implied by velocity × steps-per-unit must be achievable by the base thread.
- **`STEPGEN_MAXACCEL` must exceed `MAX_ACCELERATION`** — conventionally by 25%. Equal values cause following errors at the acceleration limit.

```
steps/unit × MAX_VELOCITY = step rate
```

A software-stepped parallel-port system tops out around 20–25 kHz with a 25 µs base period. 2000 steps/mm at 25 mm/s is 50 kHz — not achievable, and the symptom is a following error.

## 4. Motors stall or lose steps at any speed

If the axis doesn't move correctly even at very low velocity, the documented checklist is:

- **Step waveform timings.** `DIRSETUP`, `DIRHOLD`, `STEPLEN`, `STEPSPACE` must meet the driver's minimums:

```ini
DIRSETUP   = 5000
DIRHOLD    = 5000
STEPLEN    = 5000
STEPSPACE  = 5000
```

Values in nanoseconds. Too short and the driver misses pulses; the driver's datasheet gives the minimums and doubling them costs nothing at these speeds.

- **Pin inversion on the step pins.** A driver expecting active-low steps fed active-high pulses may move erratically or not at all.
- **Cabling.** Unshielded step/direction wiring next to motor phases picks up noise. This is a real cause of random missed steps.
- **Mechanical.** Coupling slip, a binding leadscrew, an over-tight gib. Turn the screw by hand with the motor disconnected.

## 5. One axis works, another doesn't

Swap the drives or the cables between two axes. If the fault follows the cable, it's wiring; if it stays with the axis, it's mechanical or that driver. Two minutes, and it halves the search space.

Also check the obvious configuration asymmetry:

```bash
grep -A10 '\[JOINT_1\]' ~/linuxcnc/configs/myconfig/myconfig.ini
```

A `SCALE` sign error gives an axis that moves the wrong way; a magnitude error gives one that moves the wrong distance. Neither is a "not moving" fault, but both get reported as one.

## 6. Latency

```bash
latency-test
```

A servo thread max jitter above about 50 µs makes software stepping unreliable, and the failures look mechanical. Causes: SMI on some chipsets, power management, a GPU driver. If latency is bad, no amount of timing configuration helps — fix latency or move to a hardware step generator (Mesa card).

## What not to do

- **Don't trust Stepconf's test as proof the machine works.** It bypasses amplifier enable by design.
- **Don't loosen `FERROR` to stop following errors.** Fix velocity and acceleration first.
- **Don't run with `STEPGEN_MAXACCEL` equal to `MAX_ACCELERATION`.** Leave headroom.
- **Don't ignore a bad latency test.** It invalidates everything downstream.

## Prevention

| Habit | Why |
|---|---|
| Driver datasheet timings, doubled, in the ini | Removes missed-pulse failures |
| `halmeter` on every input before wiring conclusions | Shows polarity definitively |
| `latency-test` before commissioning | Software stepping depends on it |
| Back up the whole config directory | Hand-tuned HAL files are hours of work |

## FAQ

**Is the parallel port still viable?**
It works, with latency caveats. A Mesa card removes the real-time requirement from the CPU and is the standard upgrade.

**Can I use a USB breakout board?**
Not for step generation — USB has no real-time guarantees. Ethernet or PCI(e) interfaces only.

**Following error only on rapid moves.**
Classic velocity/step-rate ceiling. Lower `MAX_VELOCITY` and confirm.

**Homing moves the wrong way.**
`HOME_SEARCH_VEL` sign. Negative searches toward the minimum.
