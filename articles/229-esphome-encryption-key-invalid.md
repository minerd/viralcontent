---
title: "ESPHome 'Encryption Key Is Invalid'? Reload the Integration, Don't Re-Flash"
slug: esphome-encryption-key-invalid
meta_description: "Home Assistant rejects the correct ESPHome API key after a DHCP change or update. Why reloading beats re-adding, what the key format must be, and how to rotate it safely."
updated: October 2026
cluster: round 10 (tech) — HA community threads and GitHub issues only
competition: LOW
---

# ESPHome 'Encryption Key Is Invalid'? Reload the Integration, Don't Re-Flash

A device goes **"Attention required"** in Home Assistant, you're asked for the transport encryption key, you paste the exact key from the YAML — and it's rejected: **"The transport encryption key is invalid."**

**You almost certainly have the right key.** The usual cause is Home Assistant talking to a device it can no longer match to the config entry, most often after the device's **IP address changed**.

## What actually triggers it

- **DHCP reallocated the device's IP.** Reported repeatedly: the integration finds the device at a new address, can't reconcile it with the existing entry, and prompts for the key — then rejects it
- **You regenerated the key** in the YAML and flashed, but Home Assistant still holds the old one (or vice versa: you flashed an old build after changing the key in HA)
- **Two sources of truth**: compiled via the ESPHome web dashboard once and from a local CLI another time, with different `api: encryption: key:` values
- A **packages/blueprint-based config** (NSPanel blueprints are the famous case) that regenerates or drops the key on update
- The key in YAML is a **substituted variable or secret** that didn't resolve — so what got flashed isn't what you're reading

## Fix 1: reload the integration (try this before anything else)

Reloading re-reads the device and its address without discarding your entity history:

1. **Settings → Devices & Services → ESPHome**
2. Find the device → **⋮ → Reload**
3. If that doesn't clear it, **restart Home Assistant** and watch for a discovery notification

Many reports resolve here. You should not have to delete the device, and deleting it is what costs you entity IDs, history and automations.

## Fix 2: confirm the key is byte-for-byte right

The key must be the **base64 form of 32 random bytes** — a 44-character string ending in `=`.

- Read it from the **actual YAML that was compiled**, not a copy in a note
- If it's `!secret api_key`, check `secrets.yaml` — and check for a second `secrets.yaml` in another directory
- No leading/trailing whitespace, no line break in the middle (paste into a plain text editor to check)
- In the ESPHome dashboard, the device's config shows the key in use

## Fix 3: give the device a stable address

If DHCP churn caused this, stop it happening again:

- **DHCP reservation** on your router for the device's MAC, or
- Static IP in the YAML:
  ```yaml
  wifi:
    manual_ip:
      static_ip: 192.168.1.50
      gateway: 192.168.1.1
      subnet: 255.255.255.0
  ```
- Make sure mDNS works on your network — ESPHome relies on `.local` discovery, and a router or VLAN that blocks multicast causes a stream of mystery disconnections

## Fix 4: rotate the key deliberately

If you genuinely want a new key:

1. Generate one (the ESPHome dashboard offers this when you clear the field; it produces a valid 32-byte base64 key)
2. Put it in the YAML, **install** to the device, and wait for it to come back online
3. In Home Assistant, **reload** the device and enter the new key when prompted

Do it in that order. Changing it in Home Assistant first leaves HA unable to talk to the device at all.

## Fix 5: last resorts, in order

1. **Reload** the single device
2. **Restart** Home Assistant
3. **Delete just that device's config entry** and re-add it via discovery (you lose entity IDs unless you rename carefully)
4. **Re-flash over USB** with a known-good YAML — only if the device is also unreachable for OTA
5. **Remove `api: encryption:` temporarily** to prove connectivity, then put it back. Don't leave an unencrypted API exposed on a network you share

## Also check

- **Device actually online?** Ping it. A dead device produces the same prompt
- **ESPHome add-on / integration versions** roughly in step with each other — a very old device build with a new HA can misbehave
- **Two Home Assistant instances** on the network both trying to claim the device (a test instance is a classic)
- **openHAB or another controller** also connecting — the API allows limited concurrent clients

## FAQ

**Do I have to re-flash when the key is rejected?**
No. Reload the integration first; re-flashing is a last resort.

**Why did this start after a power cut?**
Devices came back with new DHCP leases. Reserve their addresses.

**Can I run ESPHome without API encryption?**
You can, but then anything on the network can command the device. Use it only as a short diagnostic.

**Where is the authoritative copy of the key?**
Whatever was compiled into the device. The ESPHome dashboard's config for that device is the thing to trust.
