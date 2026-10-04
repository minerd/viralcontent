---
title: "WLED Won't Connect to Wi-Fi After an Update? Erase Flash, Then Fix Power"
slug: wled-not-connecting-wifi
meta_description: "WLED stuck in AP mode or unreachable after an OTA update. Why a full flash erase fixes it, the power-supply trap, and settings that keep it on the network."
updated: October 2026
cluster: round 12 (tech) — WLED Discourse and GitHub issues only
competition: LOW
---

# WLED Won't Connect to Wi-Fi After an Update? Erase Flash, Then Fix Power

After an update, WLED either stays on **WLED-AP**, joins the router and becomes unreachable, or rejects the AP password you know is right.

## 1. Erase the flash and reflash (the fix that actually works)

Reported repeatedly, including for the 14.x line: an upgrade leaves the device unreachable, and **erasing all flash before uploading** resolves it. Leftover config from an older schema is the cause.

- Flashing from a browser installer: choose the option to **erase the device** first
- From the Arduino IDE / esptool: enable **"erase all flash before sketch upload"**, or:
  ```bash
  esptool.py --port /dev/ttyUSB0 erase_flash
  esptool.py --port /dev/ttyUSB0 write_flash 0x0 WLED_X.X.X_ESP32.bin
  ```
- You lose your settings and presets — **back them up first** from Config → Security & Updates → *Backup* (a small JSON file)

If you can still reach the UI, take that backup **now**, before experimenting.

## 2. Keep the AP available so you're never locked out

**Config → WiFi Setup → AP behaviour → "Always"**. The device then offers WLED-AP regardless of whether it reaches your router, which turns every future failure into a two-minute fix instead of a soldering session.

Also there:
- **Disable WiFi sleep** — reported as resolving flaky connectivity, and worth having on permanently for an always-on controller
- Set a **static IP**, or give it a DHCP reservation on the router
- Check the **mDNS name** isn't colliding with another device

## 3. Power is the underrated cause

Wi-Fi draws current in spikes. An ESP32 on a marginal supply — a long thin USB cable, a laptop port, a shared LED supply with voltage sag — boots, tries to associate, browns out, and repeats.

- Power the ESP from a **solid 5V source**, not the far end of an LED strip
- Inject power properly on long strips; don't rely on strip copper to feed the controller
- Use a **short, thick** USB cable if you power it that way
- Symptom to recognise: it works on your desk and fails in the installation. That's power, not firmware

## 4. Router-side causes

- **2.4 GHz only.** ESP32/ESP8266 can't see a 5 GHz-only SSID. Split the bands or enable a 2.4 GHz SSID
- **WPA3-only** or 802.11w (PMF) **required** breaks ESP devices — set WPA2/WPA3 mixed, PMF optional
- **Hidden SSID** support is patchy
- MAC filtering or a **full DHCP pool**
- Channel width 40 MHz on 2.4 GHz and some mesh setups cause association failures

## 5. If the password "is wrong" when it isn't

Two things do this:
- A **stale credential** in old flash → section 1
- Special characters in the SSID/password that the config page mangles. Test with a simple temporary password to prove it, then decide

## 6. Recovering a device you can't reach

1. Power-cycle and look for **WLED-AP** (default password `wled1234`)
2. Check the **router's DHCP leases** for the hostname/MAC
3. Scan the subnet: `nmap -p 80 --open 192.168.1.0/24`
4. If none of that works, **USB flash** with erase — the reliable path
5. For a device that's physically awkward, this is why "AP always" and a backup matter before you install it

## Prevention

1. **Back up the config JSON** before every update
2. **AP behaviour: Always**, and **disable WiFi sleep**
3. **DHCP reservations** for every controller
4. **Decent power**, injected properly
5. Update **one device first** when you have several, and keep the previous binary

## FAQ

**Will erasing flash delete my presets?**
Yes. Back up the config JSON from the UI first.

**Why does it work at my desk but not where it's installed?**
Power or Wi-Fi signal. Both are environmental, not firmware.

**Can WLED use 5 GHz?**
No. 2.4 GHz only.

**Should I update WLED at all if it's working?**
Only when you want a new feature or a fix — and always with a config backup and physical access to the device.
