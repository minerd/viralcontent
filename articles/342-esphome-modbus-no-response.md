---
title: "ESPHome Modbus: \"No response received\" and Sensors Showing Unknown"
slug: esphome-modbus-no-response
meta_description: "The ESP sends and nothing comes back. RS485 wiring, send_wait_time, the 5V adapter problem, and the version regressions worth knowing about."
updated: October 2026
cluster: round 13 (tech) — ESPHome GitHub issues and HA community
competition: LOW
---

# ESPHome Modbus: "No response received" and Sensors Showing Unknown

The log line that matters:

```
[W][modbus:097]: Modbus CRC Check failed!
[W][modbus_controller:032]: No response received for address 0x00
```

Both mean the ESP is transmitting. "No response" means nothing came back; "CRC failed" means something came back malformed. The second is more encouraging — the bus works and something is nearly right.

## 1. Confirm the basics of the config

```yaml
uart:
  id: mod_uart
  tx_pin: GPIO17
  rx_pin: GPIO16
  baud_rate: 9600
  stop_bits: 1
  parity: NONE

modbus:
  id: modbus1
  uart_id: mod_uart
  flow_control_pin: GPIO4     # DE/RE on the transceiver, if not auto

modbus_controller:
  - id: meter
    address: 1
    modbus_id: modbus1
    update_interval: 30s
    setup_priority: -10

sensor:
  - platform: modbus_controller
    modbus_controller_id: meter
    name: "Voltage"
    address: 0x0000
    register_type: holding
    value_type: U_WORD
    unit_of_measurement: V
```

Things to get right before touching hardware:

- **`address`** is the Modbus slave ID (often 1, sometimes 2 or 247 by default). Wrong ID = no response, every time. Check the device's manual or its display menu.
- **Baud rate, parity, stop bits must match the device exactly.** 9600-8N1 is common; 9600-8E1 and 19200-8N1 are both frequent. A mismatch gives CRC errors or silence.
- **`register_type`**: `holding` (function 3) vs `read` (input registers, function 4). Many device manuals list addresses without saying which function; trying both is faster than reading the manual twice.
- **Address base.** Manuals often list register 40001 meaning holding register 0. Subtracting the 40001/30001 offset is a standard source of "no response" — the register simply doesn't exist.

## 2. The RS485 transceiver

Most problems are here.

- **MAX485 modules want 5 V.** The chip is specified for 5 V; running it from the ESP's 3.3 V rail often *appears* to work on a short bench wire and fails on a real bus. Power the module from 5 V, keep the data lines at 3.3 V logic (the MAX485's input threshold accommodates this), and share ground. If you have intermittent CRC errors, this is the first thing to change.
- **`flow_control_pin`.** The DE/RE pins control transmit/receive direction. Modules with automatic direction control don't need the pin; those with DE/RE tied together do. Omitting it on a manual module means the transceiver never listens, so you get "no response" with a perfect transmit.
- **A/B polarity.** Swapped A/B = total silence. There is no damage; just swap them. Note that vendors label them inconsistently (A/B, D+/D−, 485+/485−), so swapping is a legitimate diagnostic step rather than a guess.
- **Termination.** 120 Ω at each end of a long bus. On a short bench run it's optional; on 50 m it isn't.
- **Common ground.** RS485 is differential but still needs a reference between nodes. Two separately-powered devices with no ground link fail intermittently.

## 3. Timing

```yaml
modbus:
  id: modbus1
  uart_id: mod_uart
  send_wait_time: 500ms
```

`send_wait_time` is how long ESPHome waits for a reply before giving up. The default is tight for devices that are slow to turn their transceiver around — many inverters and energy meters need 200–500 ms. **Raising this is the single most effective software change** for a bus that responds intermittently.

Also:

- **`update_interval`** too short for the number of registers means commands queue and time out. With 30 sensors at 10 s, you're asking for 3 reads per second from a device that may handle one.
- **Multiple controllers on one bus** must share the `modbus` id and have different slave addresses. Two devices at address 1 collide and produce CRC errors.

## 4. After an ESPHome update it stopped working

This has happened more than once, in both directions — a UART batching change and a modbus-controller change have each broken working configurations in specific releases.

The diagnostic is simple and definitive:

1. Note your current ESPHome version.
2. Pin the previous minor version in your configuration and reflash.
3. If it works, it's a regression, not your wiring.

```yaml
esphome:
  name: meter
# in the HA add-on, pin the add-on version;
# in the CLI: pip install esphome==2026.1.4
```

Report it with your log and config; these get fixed quickly, but in the meantime a pinned version is a working system. Keep a note of the last known-good version for every Modbus device you run — it's the cheapest insurance available.

## 5. Reading the log properly

```yaml
logger:
  level: VERBOSE
  logs:
    modbus: VERBOSE
    modbus_controller: VERBOSE
```

With verbose modbus logging you see the exact bytes sent and received:

```
[V][modbus:xxx]: Modbus write: 01.03.00.00.00.02.C4.0B (8)
[V][modbus:xxx]: Modbus received: 01.03.04.09.1E.00.00.FA.3D (9)
```

- **Nothing received** → wiring, address, or direction control
- **Received but CRC failed** → electrical (power, termination, noise) or a baud mismatch
- **Received a Modbus exception** (function code with the high bit set, e.g. `83`) → the device answered and refused: wrong register or wrong function. This is good news; you're one register away.

That byte-level view turns guesswork into a two-minute diagnosis.

## What not to do

- **Don't power a MAX485 from 3.3 V** and then chase intermittent CRC errors for a week.
- **Don't poll 50 registers every 5 seconds.** Group what you need and slow it down; most energy data is useful at 30–60 s.
- **Don't add a second device to the bus before the first works.** One variable at a time.
- **Don't assume the manual's register numbers are zero-based.** Check both interpretations.

## Prevention

| Habit | Why |
|---|---|
| `send_wait_time: 500ms` as a starting point | Covers slow devices, costs nothing |
| Note the working ESPHome version per device | Makes regressions a one-step rollback |
| Verbose modbus logging while commissioning | Turns silence into specific information |
| 5 V to the transceiver, shared ground, terminated bus | Removes the whole electrical class |

## FAQ

**Can one ESP talk to several Modbus devices?**
Yes — one `modbus` bus, several `modbus_controller` blocks with different addresses.

**TCP instead of serial?**
ESPHome's modbus is serial. For Modbus TCP, use Home Assistant's own modbus integration, which speaks TCP directly.

**Values are wrong rather than missing.**
`value_type` mismatch — U_WORD vs S_WORD vs U_DWORD, and byte/word order. Try `register_count: 2` with `U_DWORD` and its reversed variant.

**It works then stops after hours.**
Usually thermal or power: a transceiver on a marginal 3.3 V supply, or a device that resets its serial port. Check `dmesg`-equivalent in the ESP log for reboots.
