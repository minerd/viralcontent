---
title: "Klipper: ADXL345 Not Detected? Wiring, SPI Bus and the mcu Prefix"
slug: klipper-adxl345-not-detected
meta_description: "ACCELEROMETER_QUERY gives 'Invalid adxl345 id (got ff vs e5)' or 'adxl345 not found'. The four real causes, in the order worth checking."
updated: October 2026
cluster: round 13 (tech) — Klipper GitHub issues and Klipper Discourse
competition: LOW
---

# Klipper: ADXL345 Not Detected? Wiring, SPI Bus and the `mcu` Prefix

The error text tells you which of two failures you have, and they have nothing in common:

- **`Invalid adxl345 id (got ff vs e5)`** — Klipper is talking to the SPI bus but getting nothing back. Wiring or chip select.
- **`Unable to open config file` / `adxl345 not found`** — Klipper never got as far as the bus. Config problem.
- **`got 00 vs e5`** — power. The board is pulled low, usually a missing or wrong-rail VCC.

`ff` means the MISO line is floating high. `00` means it's held low. That single byte localises the fault before you touch a wire.

## 1. Confirm which MCU the sensor is actually on

The most common config mistake. If the accelerometer is plugged into your **toolhead** board (an SB2209, EBB36, a CAN board) but the config has no `mcu:` line, Klipper looks for it on the **main** MCU and finds nothing.

```ini
[adxl345]
cs_pin: EBBCan: PB12
spi_bus: spi1
axes_map: x,y,z
```

Note the `EBBCan:` prefix on the pin — it has to match the name you gave the board in `[mcu EBBCan]`. A pin without a prefix is a main-board pin. This is why the identical config works for someone else and fails for you.

For a Raspberry Pi-attached ADXL (the classic setup), the prefix is the Linux MCU:

```ini
[mcu rpi]
serial: /tmp/klipper_host_mcu

[adxl345]
cs_pin: rpi:None
spi_bus: spidev0.0
```

`cs_pin: rpi:None` is not a typo — on the Pi the kernel driver handles chip select, so Klipper is told not to.

## 2. For the Pi: enable SPI and install the host MCU

Two steps people skip, and each produces a different error.

```bash
sudo raspi-config   # Interface Options → SPI → Enable
ls -l /dev/spidev*  # must list spidev0.0
```

If `/dev/spidev0.0` doesn't exist, nothing in Klipper will help. Then build and install the host MCU:

```bash
cd ~/klipper
make menuconfig     # Microcontroller Architecture → Linux process
make flash
sudo service klipper restart
```

Missing the Linux MCU gives `Unable to connect` on `/tmp/klipper_host_mcu`, not an ADXL error, which is why it's worth confirming early.

## 3. Then, and only then, check the wiring

With the config right and the bus enabled, `got ff` is physical. Four things, roughly in order of frequency:

| Symptom | Likely cause |
|---|---|
| `got ff vs e5` | CS not connected, or SDO/SDI swapped |
| `got 00 vs e5` | VCC missing or on the wrong rail |
| Intermittent, works cold | the breakout's own header solder joints |
| Works, data is garbage | 3.3 V part fed 5 V, or very long unshielded wires |

The ADXL345 breakouts sold for Klipper are **3.3 V**. Feeding 5 V sometimes works and sometimes quietly corrupts readings. Check the board's own regulator before assuming 5 V tolerance.

SPI naming is also a reliable trap: on the sensor the pins are often labelled **SDO** (data out → MCU MISO) and **SDA/SDI** (data in → MCU MOSI). Boards that label them MISO/MOSI from the *host's* perspective lead people to wire them straight through, which is backwards.

Keep the wires short. Over about 30 cm of unshielded ribbon on a moving toolhead, SPI starts failing intermittently — which reads as a flaky sensor rather than a wiring problem.

## 4. Query it

```bash
ACCELEROMETER_QUERY
```

A working sensor returns something like:

```
accelerometer values (x, y, z): 470.719200, 941.438400, 9728.196800
```

The Z value should sit near 9800 (1 g in mm/s²) with the printer at rest and the sensor mounted flat. If Z reads near zero and another axis reads 9800, your `axes_map` is wrong — not broken, just rotated. Fix it in config rather than remounting:

```ini
axes_map: z,-y,x
```

## What not to do

- **Don't start by replacing the sensor.** `ff` is a bus-level symptom and a new board on the same wiring gives the same byte.
- **Don't run `TEST_RESONANCES` to diagnose detection.** It needs a working sensor; its failure tells you nothing new.
- **Don't leave the ADXL wired for daily printing.** Input shaper is a one-off measurement. Long toolhead SPI wiring that sits there is a future intermittent fault, and the `[adxl345]` section left in config makes Klipper refuse to start once you unplug it.
- **Don't trust a 5 V "tolerant" claim** without reading the breakout's schematic.

## Prevention

| Habit | Why |
|---|---|
| Comment out `[adxl345]` after measuring | Klipper won't fail to start when it's unplugged |
| Note the `mcu` prefix in a comment | Future-you moves the sensor between boards |
| Record the `axes_map` that worked | Re-measuring after a mod takes two minutes instead of twenty |
| Keep SPI runs under ~20 cm | Removes the intermittent-failure class entirely |

## FAQ

**Can I use an MPU-9250/LIS2DW instead?**
Yes, and the config section differs (`[mpu9250]`, `[lis2dw]`). The MPU variants use I²C, so the whole SPI section above doesn't apply — but the `mcu` prefix rule does.

**Does the sensor have to be on the toolhead?**
For X/Y resonance, yes — it measures what the toolhead experiences. For a bed-slinger's Y axis, mounting it on the bed is correct.

**`ACCELEROMETER_QUERY` works but `TEST_RESONANCES` errors out.**
That's a different problem: usually a missing `[resonance_tester]` section with `accel_chip` and `probe_points` set.

**Why does it work on the Pi but not on the toolhead board?**
Different `spi_bus` name. Toolhead boards expose `spi1` or a software SPI triple; copying the Pi's `spidev0.0` into a CAN board's config cannot work.
