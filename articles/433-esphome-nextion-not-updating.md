---
title: "ESPHome: Nextion Display Components Not Updating"
slug: esphome-nextion-not-updating
meta_description: "set_component_value does nothing, or components stop updating after a page change. Sleep state, page scope, baud rate and the update_all_components call."
updated: October 2026
cluster: round 14 (tech) — esphome/issues and the ESPHome Nextion docs
competition: LOW
---

# ESPHome: Nextion Display Components Not Updating

Four causes, and three of them are the Nextion's own behaviour rather than ESPHome's.

## 1. The Nextion does not retain data across page changes

This is the single most important fact, and it explains most reports:

> **The Nextion does not retain data on page changes. If the page is changed and the component name does not exist on that page, nothing is updated.**

So a value written to `page0.temp` while `page1` is displayed goes nowhere, and when you return to `page0` the component shows whatever the HMI design set — not your last value.

Two consequences for how you write configs:

- **Qualify component names with the page** where the component lives, and only write while that page is current, or
- **Re-push everything on page change**, which is what the helper exists for:

```yaml
display:
  - platform: nextion
    id: nextion1
    uart_id: nextion_uart
    on_page: 
      then:
        - lambda: 'id(nextion1).update_all_components();'
```

`update_all_components()` sends the current state of every registered component. Call it on page change and on wake, and the "values are stale after navigating" class disappears.

Alternatively, use the Nextion's own variable components (`vaX`) with the *global* scope attribute set in the Nextion Editor — then values survive page changes on the display side, which is the cleaner design if you control the HMI.

## 2. Sleep suppresses updates

> **The Nextion does not accept commands or updates while in sleep mode.**

Updates sent during sleep are discarded, not queued. ESPHome re-sends component states when the display wakes, which covers the common case — but a one-shot command sent while asleep is simply lost.

```yaml
display:
  - platform: nextion
    id: nextion1
    uart_id: nextion_uart
    on_wake:
      then:
        - lambda: 'id(nextion1).update_all_components();'
```

Also check whether the HMI design puts the display to sleep on a timeout; `thsp`/`thup` in the Nextion Editor control that, and a 30-second sleep timeout makes the display look permanently stale.

A component explicitly **hidden** (`vis 0`) likewise won't show updates — the write succeeds and nothing is visible.

## 3. The UART and the logger fight over the port

The Nextion wants a hardware UART at **115200** (ESPHome's default for the component) or whatever you set in the HMI. The ESPHome logger defaults to the same hardware serial on many boards, and the two interleave bytes.

```yaml
logger:
  baud_rate: 0        # disable serial logging

uart:
  id: nextion_uart
  tx_pin: GPIO17
  rx_pin: GPIO16
  baud_rate: 115200
```

`baud_rate: 0` disables the logger's UART output entirely while keeping logs over the network and the API. This is the standard configuration for Nextion and NSPanel projects, and omitting it produces exactly "updates sometimes work".

Confirm the display's own baud rate matches — the Nextion stores it, and a mismatch gives no communication at all rather than partial.

## 4. Version regressions

Two documented cases worth knowing:

- **Nextion updates working on 2025.7.2 and not on 2025.7.3**, with `set_component_value()` silently not updating.
- **`update_all_components()` not working** as expected on particular releases.

The diagnostic is the same as for any ESPHome regression: pin the previous minor version and reflash.

```bash
pip install esphome==2025.7.2
esphome clean device.yaml
esphome run device.yaml
```

If it works on the older version with an unchanged config, it's upstream. Report it with your config and keep the pin until it's fixed. Note the working version in a comment in your YAML — you will want it again.

## 5. Check what's actually on the wire

```yaml
logger:
  level: VERBOSE
  logs:
    nextion: VERBOSE
```

Verbose Nextion logging prints each command sent and each response byte. What you learn:

- **Commands sent, no acknowledgement** → baud rate, wiring, or the display asleep.
- **No commands sent at all** → your automation isn't firing, or the component id is wrong.
- **`Nextion reported component ID invalid`** → the component name doesn't exist on the current page (section 1), or is misspelled. The Nextion returns a specific error code and ESPHome logs it.

That last one is decisive: the display is talking back and telling you the name is wrong.

## 6. Writing values correctly

```yaml
sensor:
  - platform: homeassistant
    id: ha_temp
    entity_id: sensor.living_room_temperature
    on_value:
      then:
        - lambda: |-
            id(nextion1).set_component_text_printf("temp", "%.1f°C", id(ha_temp).state);
```

- **`set_component_value`** writes to a numeric component's `.val` — integers only. Sending a float does nothing useful.
- **`set_component_text`/`set_component_text_printf`** writes to a text component's `.txt`.
- Using the wrong one for the component type fails silently, which is a common first mistake.

## What not to do

- **Don't leave the logger on the hardware UART.** It corrupts the Nextion protocol.
- **Don't write to components on pages that aren't displayed** without re-pushing on page change.
- **Don't send floats with `set_component_value`.** Use the text variant with formatting.
- **Don't upgrade ESPHome mid-project** on a working display without noting the version you came from.

## Prevention

| Habit | Why |
|---|---|
| `logger: baud_rate: 0` | Prerequisite for reliable Nextion communication |
| `update_all_components()` on page change and wake | Removes the stale-value class entirely |
| Verbose nextion logging during development | The display's own error codes are definitive |
| Working ESPHome version in a YAML comment | Regressions here have shipped more than once |

## FAQ

**Can I update the HMI file over the air?**
Yes — the component supports TFT upload over HTTP. The file must be served from a URL the ESP can reach, and the upload is slow.

**Does it work on an ESP8266?**
It can, with a software or the single hardware UART, and it's marginal. ESP32 with a dedicated UART is the sane choice.

**Touch events back into Home Assistant?**
Nextion binary sensors and `on_touch` triggers, mapped to HA entities.

**NSPanel specifics?**
The Sonoff NSPanel is a Nextion-family display behind an ESP32, and everything here applies — plus a vendor HMI you usually replace.
