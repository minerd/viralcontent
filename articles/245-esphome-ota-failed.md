---
title: "ESPHome OTA Update Failing? Memory, Encryption and the ESP8266 Problem"
slug: esphome-ota-failed
meta_description: "OTA uploads that stall, time out at 'Finishing update' or lock the device up. Why ESP8266 needs free flash, what interrupts break uploads, and how to recover over USB."
updated: October 2026
cluster: round 11 (tech) — ESPHome GitHub issues and HA community threads
competition: LOW
---

# ESPHome OTA Update Failing? Memory, Encryption and the ESP8266 Problem

OTA used to just work. Now uploads stall at a percentage, time out with *"Error receiving acknowledge chunk OK: timed out"*, fail at *"Finishing update"*, or the device locks up and needs a power cycle.

The causes differ sharply between **ESP8266** and **ESP32**, so start there.

## ESP8266: the flash-space problem

An ESP8266 OTA writes the new firmware into the **free half of the flash** while running from the other half. If your compiled binary is larger than the free space, OTA **cannot** work, no matter how good your Wi-Fi is.

Symptoms: uploads fail consistently at roughly the same point, or fail right at the end, while USB flashing works fine.

What to do:
- **Shrink the binary.** Remove components you don't use — `web_server`, `captive_portal`, `mdns`, extra sensors, large fonts and images are the heavy ones. `web_server` especially
- Check the **compile output**: it prints flash usage. If you're near the limit, OTA has no room
- Use `esp8266: restore_from_flash: false` if you don't need it
- Consider moving the device to an **ESP32** if your config has outgrown the chip
- Flash over **USB** once to get out of trouble

The reported pattern "upgraded ESPHome and now all my D1 minis fail OTA and need a reboot" is usually this: the new ESPHome version's baseline binary grew, and devices that were just inside the limit fell outside it.

## Interrupt-heavy components

`remote_receiver`, some `dallas`/one-wire setups, PWM and certain I²S configurations keep the CPU busy enough that the OTA handshake times out or the device locks up mid-write.

The practical approach:
- Temporarily **comment out `remote_receiver`** (and similar) and flash; then restore it
- Or do the update over **USB**
- Or add a **safe mode** entry point, below

## Encryption and version mismatch

- With `api: encryption:` enabled, the key must match **what Home Assistant holds**. Mismatches present as *"connection dropped immediately after encrypted hello"*
- `ota:` needs a **platform** declared in modern ESPHome:
  ```yaml
  ota:
    - platform: esphome
      password: !secret ota_password
  ```
  Configs written for older versions can silently end up without a working OTA component — then there is simply nothing listening to upload to
- An **old device build with a much newer ESPHome** can refuse the handshake. If the gap is years, plan on one USB flash

## Network causes

- **mDNS not resolving** — use the device's **IP address** in the dashboard (or `use_address:`) rather than `name.local`
- The device is on a **different VLAN/subnet** from the ESPHome dashboard, with multicast blocked
- **Weak signal**: check the device's `wifi_signal` sensor. OTA needs a stable connection for the whole transfer; marginal RSSI fails at random percentages
- **Wi-Fi power saving** on the device, or an AP with band-steering/roaming moving it mid-upload
- A **Docker host network** mismatch: the ESPHome add-on/container needs to reach the device directly

## Recovery when a device is half-flashed

1. **Power-cycle** it. Many devices come back on the old firmware because the new image was never finalised
2. If it boots but won't accept OTA, use **safe mode**: ESPHome's `safe_mode` (part of the OTA platform in current versions) boots a minimal firmware that only does Wi-Fi + OTA. Trigger it by power-cycling several times in quick succession if you've configured it
3. If it's unreachable, **flash over USB**. Keep one serial adapter and a known-good cable in the drawer; it turns a dead device into a five-minute job
4. For devices you can't physically reach, this is the argument for always keeping `safe_mode` enabled

## Make OTA reliable

1. **Keep `safe_mode` configured** on every device
2. **Static IPs or DHCP reservations** for ESP devices, and `use_address:` where mDNS is unreliable
3. Keep binaries small on ESP8266; prefer **ESP32** for anything non-trivial
4. **Update in batches**, not all 40 devices at once, and watch the first few
5. Keep **USB access** possible for anything you'd hate to lose
6. Note the **ESPHome version** you're on before a bulk update, so rolling back is an option

## FAQ

**Why does USB work but OTA doesn't?**
USB writes the whole flash; OTA needs free space for a second image and a stable network session. On ESP8266 that space is the usual blocker.

**Does disabling the web server really help?**
On ESP8266, yes — it's one of the largest components and often the difference between fitting and not.

**My device is pingable but won't take an OTA.**
Check the `ota:` platform is in the config, the password/key matches, and whether an interrupt-heavy component is starving the handshake.

**Should I update all devices after an ESPHome release?**
Do a couple first. Binary sizes and requirements change between releases, and ESP8266 devices are the ones that fall off the edge.
