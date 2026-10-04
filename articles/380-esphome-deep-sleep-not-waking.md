---
title: "ESPHome Deep Sleep: Device Won't Wake Up"
slug: esphome-deep-sleep-not-waking
meta_description: "The ESP sleeps and never comes back, or wakes instantly. The GPIO16-to-RST wire, the ESP32 wakeup pin rules, and how to get back in to reflash."
updated: October 2026
cluster: round 14 (tech) — esphome/issues and HA community
competition: LOW
---

# ESPHome Deep Sleep: Device Won't Wake Up

Deep sleep is where a working ESPHome device becomes unreachable, and the causes split cleanly between hardware and the fact that **a sleeping device cannot receive an OTA update**.

Read that second point first, because it determines your escape route.

## 1. Always configure a way back in

Before flashing deep sleep to anything you can't easily reach with a cable:

```yaml
deep_sleep:
  id: deep_sleep_1
  run_duration: 30s
  sleep_duration: 15min

api:
  encryption:
    key: !secret api_key

# let Home Assistant hold it awake
switch:
  - platform: template
    name: "Prevent Deep Sleep"
    optimistic: true
    turn_on_action:
      - deep_sleep.prevent: deep_sleep_1
    turn_off_action:
      - deep_sleep.allow: deep_sleep_1
```

A `run_duration` of 30 seconds and that switch means you have a window each cycle to push an OTA. With `run_duration: 5s` and no prevent switch, you will be soldering.

If you're already locked out: power-cycle the device and start the OTA immediately, retrying until it catches the boot window. ESPHome's `esphome run` retries automatically, which usually wins within a few cycles.

## 2. ESP8266: the GPIO16 → RST wire

The ESP8266's deep sleep wake mechanism is **physical**: the RTC pulls GPIO16 low at the end of the sleep period, and that must be wired to RST to reset the chip.

- **No wire between GPIO16 and RST = it never wakes.** On a bare ESP-12 or a Wemos D1 Mini, that wire is not present by default. On the D1 Mini, GPIO16 is labelled **D0**.
- Consequence: **D0 cannot be used for anything else** once wired. A config using D0 for an I²C pin or a sensor will fight the reset line — remove D0 from any other role.

```yaml
# ESP8266 — nothing in the YAML enables the wake; the wire does
esphome:
  name: sensor1
esp8266:
  board: d1_mini
deep_sleep:
  run_duration: 20s
  sleep_duration: 10min
```

A related reported symptom: **wakes instantly, over and over.** That is RST being held low, or a flaky connection on that wire. Check the solder joint; a 10 kΩ pull-up on RST helps on marginal boards.

On some ESP8266-12F modules with awkward PCB layouts, a 12–22 kΩ pull-up on MISO (pin 10) has been needed to come out of deep sleep reliably — a board-level quirk, not a config one.

## 3. ESP32: timer and pin wakeup

The ESP32 wakes itself from timer sleep with no external wiring, so "never wakes" on an ESP32 is usually configuration or power.

For pin wakeup:

```yaml
deep_sleep:
  run_duration: 10s
  sleep_duration: 30min
  wakeup_pin:
    number: GPIO33
    allow_other_uses: false
  wakeup_pin_mode: INVERT_WAKEUP
```

Rules:

- **The pin must be an RTC GPIO.** On the classic ESP32 that is GPIO 0, 2, 4, 12–15, 25–27, 32–39. GPIO 5 or 18 will not wake it, and ESPHome does not always refuse the config.
- **GPIO 34–39 are input-only with no internal pull-up/pull-down.** A floating wakeup pin there wakes randomly. Add an external resistor.
- `wakeup_pin_mode: INVERT_WAKEUP` matters when the pin is already in the wake state at sleep time — without it the device sleeps and wakes immediately in a loop.
- **ESP32-S2/S3/C3 variants** have different RTC pin sets and different sleep behaviour. Reported fixes include setting the variant explicitly and adjusting boot priority:

```yaml
esp32:
  board: esp32-s2-saola-1
  variant: esp32s2
```

## 4. Power

A device that sleeps correctly and wakes into a brown-out looks identical to one that never wakes.

- **A cheap or far-away power supply** sags during the Wi-Fi transmit burst right after wake. Try a known-good 2 A supply as a test — this is a surprisingly common cause.
- **Battery-powered**: a near-flat LiPo has enough voltage at rest to hold the RTC and not enough to connect. The device appears dead, then revives on charge.
- **A 10 µF–100 µF capacitor across the module's 3V3 and GND** smooths the wake burst on marginal supplies.

```bash
# watch the serial console across a sleep cycle
esphome logs device.yaml --device /dev/ttyUSB0
```

The boot banner on wake tells you it woke; silence means it didn't, and a reset-reason line distinguishes a brown-out from a timer wake.

## 5. Sleep works, Home Assistant marks it unavailable

Expected. A sleeping device isn't reachable, so HA shows it unavailable between cycles. Options:

- Accept it, and read the last reported value from history.
- Mark the sensors as retained via MQTT instead of the native API — MQTT with `retain: true` keeps the last value visible:

```yaml
mqtt:
  broker: 192.168.1.10
  discovery: true
  birth_message:
  will_message:
```

Clearing `birth_message` and `will_message` stops HA marking entities unavailable when the device disconnects — which is what you want for an intentionally sleeping sensor.

## What not to do

- **Don't flash deep sleep with a short `run_duration` and no prevent switch.** It's the single most common way to lock yourself out.
- **Don't use D0 for anything else on an ESP8266** once it's wired to RST.
- **Don't pick a non-RTC pin for `wakeup_pin`.** It silently won't work.
- **Don't debug sleep over Wi-Fi.** Use the serial console; it's the only view that survives a reboot loop.

## Prevention

| Habit | Why |
|---|---|
| `run_duration: 30s` + a prevent-sleep switch | Keeps OTA possible forever |
| GPIO16→RST wire documented per device | ESP8266's wake is hardware, not software |
| Known-good power supply during bring-up | Removes brown-out from the variables |
| MQTT with cleared birth/will for sleepers | Sensible availability behaviour in HA |

## FAQ

**How much power does deep sleep actually save?**
An ESP32 drops from ~80 mA active to tens of microamps. The win comes from a short `run_duration` — most of the budget is the Wi-Fi connect.

**Can it wake on a touch or ULP sensor?**
ESP32 supports touch wake and ULP programs; ESPHome exposes touch wake on some variants.

**Why does the first wake take so long?**
Wi-Fi association plus DHCP. A static IP and a fixed channel cut it substantially:

```yaml
wifi:
  manual_ip:
    static_ip: 192.168.1.60
    gateway: 192.168.1.1
    subnet: 255.255.255.0
```

**Does OTA ever work on a sleeping device?**
Only during `run_duration`. Hence the window.
