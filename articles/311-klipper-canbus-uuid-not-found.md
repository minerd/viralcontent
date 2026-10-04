---
title: "Klipper CAN Bus: \"Unable to find UUID\" and canbus_query Returning Nothing"
slug: klipper-canbus-uuid-not-found
meta_description: "canbus_query finds no devices, or Klipper can't find a UUID it found yesterday. Bitrate, termination, the can0 interface and the bootloader state."
updated: October 2026
cluster: round 13 (tech) — Klipper GitHub issues and Klipper Discourse
competition: LOW
---

# Klipper CAN Bus: "Unable to find UUID" and `canbus_query` Returning Nothing

Two different errors, two different causes:

- **`canbus_query.py` returns nothing** — the bus isn't working at the link layer. Nothing in Klipper's config is relevant yet.
- **`Unable to find UUID` at startup** — the bus works, but the device isn't answering with that UUID: it's in its bootloader, flashed with a different bitrate, or the UUID in printer.cfg is stale.

## 1. Is `can0` up, and at what bitrate?

```bash
ip -details link show can0
```

You need `state UP` and a bitrate. If the interface doesn't exist, Klipper hasn't got a bus to query.

```bash
# /etc/network/interfaces.d/can0
auto can0
iface can0 can static
    bitrate 1000000
    up ip link set $IFACE txqueuelen 1024
```

Two numbers matter:

- **Bitrate must match the firmware on every board on the bus.** 1 Mbit (1000000) is the modern default; older guides use 500000. A board flashed at 500k on a 1M bus is invisible — no error, just absent. This is the most common cause of an empty `canbus_query`.
- **`txqueuelen 1024`.** Without it you get `Timer too close` and dropped frames under load. The symptom appears mid-print, not at startup, so it's rarely connected to CAN setup.

Check for bus errors:

```bash
ip -s -d link show can0
```

A rising `bus-error` or `restart` count means electrical trouble — go to section 3.

## 2. Query the bus

```bash
~/klippy-env/bin/python ~/klipper/scripts/canbus_query.py can0
```

Expected:

```
Found canbus_uuid=a1b2c3d4e5f6, Application: Klipper
```

Interpreting the result:

- **`Found ... Application: CanBoot`** (or Katapult) — the board is sitting in its bootloader, not running Klipper. Flash it:

```bash
~/klippy-env/bin/python ~/katapult/scripts/flashtool.py \
  -i can0 -u a1b2c3d4e5f6 -f ~/klipper/out/klipper.bin
```

- **Total silence** — bitrate mismatch, wiring, or termination. Sections 1 and 3.
- **The UUID differs from printer.cfg** — update printer.cfg. A UUID changes if you reflash with a different chip ID source, or if you've swapped the board.
- **Two devices with the same UUID** — you have two identically flashed boards; reflash one.

## 3. Termination and wiring

CAN needs **exactly two 120 Ω terminators**, one at each physical end of the bus. Not three, not one.

```bash
# with the printer powered off, measure across CAN-H and CAN-L
# correct bus: ~60 Ω (two 120 Ω in parallel)
```

60 Ω is right. 120 Ω means only one terminator is active. 40 Ω means three. Open circuit means a broken wire. This single measurement diagnoses most physical CAN faults in thirty seconds.

Most toolhead boards and most CAN bridge boards have a termination jumper. The classic mistake: both the bridge *and* the toolhead board are terminated (correct for a two-node bus), then a third board is added in the middle and also terminated.

Other physical causes:

- **CAN-H and CAN-L swapped.** No damage, no communication.
- **Unshielded wire run beside the stepper or heater wiring.** Works at 500k, fails at 1M. If the bus is error-free at 500k and unreliable at 1M, that's the diagnosis.
- **No common ground** between the bridge and the toolhead board. CAN is differential but still needs a ground reference.
- **Insufficient wire gauge for the toolhead's 24 V.** Voltage drop under heater load browns out the board, which drops off the bus mid-print and comes back — appearing as a random `Unable to find UUID` on the next start.

## 4. The USB-CAN bridge specifically

If your main board runs in **USB-to-CAN bridge mode**, it is both the bus master and a CAN node. Two implications:

- Its own UUID appears in `canbus_query` and must be in printer.cfg as `canbus_uuid` on the `[mcu]` section, not a serial path.
- Reflashing it drops the whole bus. After flashing the bridge, every board is unreachable until the bridge is back.

```ini
[mcu]
canbus_uuid: 1122aabbccdd

[mcu EBBCan]
canbus_uuid: a1b2c3d4e5f6
```

## What not to do

- **Don't change the bitrate on one board only.** Every node and `can0` must match; a partial change makes the working boards disappear too.
- **Don't add termination "to be safe".** Over-termination is as broken as under-termination.
- **Don't skip `txqueuelen`.** The resulting `Timer too close` failures look like a mainboard problem and waste hours.
- **Don't run CAN wiring in the same bundle as the heater cartridge leads.** It's the most common cause of intermittent bus errors on an otherwise correct setup.

## Prevention

| Habit | Why |
|---|---|
| Write every UUID in a comment in printer.cfg | Makes a board swap a two-minute job |
| Measure 60 Ω after any wiring change | Catches termination mistakes before they're intermittent |
| Standardise on 1 Mbit everywhere | One number to remember, and it's the current default |
| Twisted pair, shielded, away from motor wiring | Eliminates the whole intermittent class |

## FAQ

**Can I run CAN over the same cable as 24 V power?**
Yes, that's the normal umbilical — but use twisted pair for H/L and adequate gauge for power.

**`canbus_query` finds the board but Klipper says UUID not found.**
Almost always the bootloader case: the query sees Katapult, Klipper wants a Klipper node. Flash it.

**Do I need Katapult/CanBoot?**
Not strictly, but without a bootloader every firmware update means physically removing the toolhead board to flash over USB.

**Bus works cold, fails when the hotend heats.**
Voltage drop or thermal expansion on a marginal connector. Check the 24 V at the toolhead board while the heater is at full power.
