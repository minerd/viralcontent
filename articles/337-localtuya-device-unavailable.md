---
title: "LocalTuya / tuya-local: Device Unavailable (And the App Is Why)"
slug: localtuya-device-unavailable
meta_description: "A Tuya device connects once then goes unavailable, or never connects. Most devices allow one local connection — and the official app holds it."
updated: October 2026
cluster: round 13 (tech) — localtuya GitHub and HA community
competition: LOW
---

# LocalTuya / tuya-local: Device Unavailable (And the App Is Why)

The thing that explains most of these failures, and that almost no guide states plainly:

> **Most Tuya devices accept exactly one local connection at a time.**

So if the Smart Life / Tuya app is open on your phone on the same network, or another integration is polling the device, Home Assistant cannot connect. The device isn't broken and your local key isn't wrong — the slot is taken.

Close the app fully (not just background it), then retry. If that fixes it, everything below is about keeping that slot free.

## 1. Rule out connection contention first

Things that occupy the single local connection:

- The Tuya/Smart Life app **open and on the same LAN**. Over mobile data it goes via the cloud and doesn't take the local slot.
- **Two integrations**: LocalTuya *and* tuya-local, or LocalTuya *and* the official Tuya cloud integration configured for local control.
- A second HA instance, or a test script left running.
- `tinytuya` scan or wizard still running.

Pick one consumer per device. If you need the app occasionally, expect HA to go unavailable while you use it on Wi-Fi — that's the device's limitation, not a configuration error.

## 2. The three values you need

```yaml
device_id: bf1234567890abcdef
local_key: 1a2b3c4d5e6f7890
host: 192.168.1.77
protocol_version: "3.3"
```

- **`local_key` changes whenever the device is re-paired.** Reset a device, add it back to the app, and the key is new — HA then fails to connect with a decrypt error. Re-fetch the key; don't assume the old one survived.
- **`protocol_version`** is 3.1, 3.3, 3.4 or 3.5 depending on firmware. The wrong one gives a connection that opens and immediately drops, or garbled data. 3.3 is the most common; newer devices use 3.4/3.5 and these need the correct setting or they appear permanently unavailable.
- **`host`** must be stable. A DHCP lease change means HA is talking to nothing, or to a different device. **Set a static DHCP reservation for every Tuya device** — this is the second most common cause of "it worked for a month then stopped".

Getting keys:

```bash
pip install tinytuya
python -m tinytuya wizard
```

The wizard uses a Tuya IoT Platform account and lists every device with its id and local key. Note that Tuya's developer project linkage expires and must be renewed; an expired project makes the wizard return nothing, which is unrelated to your devices.

## 3. "Connected but no entities" / wrong entities

LocalTuya requires you to map **DPs** (datapoints) to entities by hand. The DP numbers vary by device, even between models of the same brand.

```bash
python -m tinytuya scan
```

Watch a device while you operate it physically — the DP that changes is the one you want. Common conventions:

| DP | Usually |
|---|---|
| 1 | main switch / on-off |
| 2 | second gang, or mode |
| 9 | countdown timer |
| 20 | light switch (newer lights) |
| 21 | work mode |
| 24 | colour (HSV string) |

Guessing produces entities that exist and don't work. For **tuya-local**, the device is matched to a YAML config by its DP set; a device with no matching config shows up with generic or missing entities, and the fix is to find or write the config rather than remap DPs.

## 4. Unavailable after a while

- **Device firmware OTA.** Tuya pushes updates. Some change the protocol version or the DP layout. If every device of one model breaks on the same day, that's what happened.
- **Wi-Fi.** Many Tuya devices are 2.4 GHz only and have poor radios. A mesh network steering them to 5 GHz, or an AP with band steering, drops them. Put them on a dedicated 2.4 GHz SSID.
- **Router isolation / IoT VLAN.** Local control needs HA and the device on the same L2 segment, or explicit routing plus the right ports (6668/tcp). Client isolation on a guest network breaks it entirely.
- **Polling interval too aggressive.** LocalTuya holds a persistent connection; frequent reconnects can wedge a device until it's power-cycled.

## 5. Should you block their internet access?

Many people put Tuya devices on a VLAN with no internet. It works for local control and stops cloud dependence. Two consequences to accept:

- No OTA updates (which is partly the point)
- No app control from outside the house
- Some devices become slow to respond to local commands while they retry cloud connections; a few reboot periodically

If you block internet, block it at the firewall and let DNS resolve normally — devices that can't resolve at all often behave worse than those that resolve and fail to connect.

## What not to do

- **Don't run LocalTuya and the cloud Tuya integration for the same device.** Contention, guaranteed.
- **Don't re-pair a device to fix a connection problem** without noting that it invalidates the local key.
- **Don't leave the Smart Life app open on Wi-Fi** and then debug HA for an hour.
- **Don't guess DP numbers from another model.** Scan the actual device.

## Prevention

| Habit | Why |
|---|---|
| Static DHCP reservation per device | Removes address-change failures |
| Record device_id, local_key, protocol_version and DP map in one file | Re-pairing and migrations become minutes, not hours |
| Dedicated 2.4 GHz SSID for IoT | Fixes the flaky-Wi-Fi class |
| One integration per device | Respects the single-connection limit |

## FAQ

**LocalTuya or tuya-local?**
tuya-local has a large library of pre-built device configs and needs less manual DP work; LocalTuya gives you full manual control. Try tuya-local first for a known device.

**Does local control survive a Tuya cloud outage?**
Yes — that's the main reason to use it.

**Can I avoid the Tuya developer account?**
There are methods to extract keys from the app's data, but the IoT Platform wizard is the documented and reliable route.

**Device responds to HA but the app shows it offline.**
Expected if the device has no internet, or if HA holds the local connection. Not a fault.
