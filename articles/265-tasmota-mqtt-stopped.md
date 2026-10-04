---
title: "Tasmota Stopped Connecting to MQTT After a Firmware Update? Use an IP, Not a Hostname"
slug: tasmota-mqtt-stopped
meta_description: "Tasmota devices that drop off MQTT after an upgrade. DNS resolution changes, TLS on 8883, duplicate topics and reading the rc error codes in the console."
updated: October 2026
cluster: round 12 (tech) — Tasmota GitHub discussions and HA community
competition: LOW
---

# Tasmota Stopped Connecting to MQTT After a Firmware Update? Use an IP, Not a Hostname

The device is on Wi-Fi, the web UI loads, and MQTT never connects. Start with the console, which tells you exactly what's failing.

## 1. Read the rc code in the console

**Web UI → Console**, and watch the MQTT attempts. Tasmota prints a result code:

| Code | Meaning |
|---|---|
| `rc 1` | Wrong protocol version |
| `rc 2` | Client ID rejected |
| `rc 3` | Server unavailable |
| `rc 4` | **Bad username or password** |
| `rc 5` | **Not authorised** |
| `-2` | Connect failed (network/DNS/TLS) |

`rc 4`/`rc 5` → credentials or ACLs; see the Mosquitto side. `-2` → the device can't even establish the socket, which is the rest of this list.

## 2. Set the broker as an IP address

The single most effective change. There was a **DNS handling change in Tasmota 12.0.0** (with a fix in 12.0.1), and hostname resolution on these devices remains the least reliable part of the stack.

```
Backlog MqttHost 192.168.1.50; MqttPort 1883; SetOption3 1
```

Then give the broker a **static IP** so the setting stays true. Hostnames depend on DNS at exactly the moment the device is booting, which is when your router is often least helpful.

## 3. TLS on 8883

If you moved MQTT to TLS, Tasmota's TLS support has limits:

- You need a build **with TLS compiled in** (not all precompiled binaries have it)
- Certificate and fingerprint handling is fussy; a renewed certificate breaks a pinned fingerprint
- Reported after updates: `TLS connection error: 1` on 8883

Diagnose by moving that device to **1883 without TLS** temporarily. If it connects, the problem is TLS, not MQTT. Then decide whether per-device TLS is worth it on a trusted VLAN.

## 4. Duplicate topics

Every device needs a **unique topic**. Flashing a precompiled binary resets the topic to the default (`tasmota_XXXX` or `sonoff`), and two devices with the same topic fight — each kicks the other off the broker, producing a flapping loop that looks like an auth failure.

```
Topic devicename
FullTopic %prefix%/%topic%/
```

Check your broker's log for the same client ID connecting and disconnecting repeatedly.

## 5. Your configuration was wiped

A **factory firmware reset** — which some flashing methods do — loses Wi-Fi, MQTT, topics, names, rules and templates. If the device came back on Wi-Fi via saved credentials but has no MQTT settings, that's what happened.

Restore from a config backup (Configuration → Backup Configuration, saved *before* the update), or re-enter settings with a Backlog command.

Keep a text file of your Backlog setup lines per device. Re-provisioning twenty plugs by hand is a lesson you only need once:

```
Backlog MqttHost 192.168.1.50; MqttUser tasmota; MqttPassword secret; Topic kitchen_light; FriendlyName1 Kitchen Light; SetOption53 1
```

## 6. The broker side changed, not Tasmota

Very common in practice: you updated Mosquitto at the same time, and **anonymous logins were removed** or ACLs tightened. Then every device fails at once with `rc 5`.

If *all* devices stopped simultaneously, suspect the broker, not the firmware.

## 7. Wi-Fi beneath it all

- **DHCP reservations** for every device
- Weak signal → association drops take MQTT with them
- Some routers' **band steering** or WPA3-only settings break ESP devices
- `SetOption56`/`SetOption57` (scan and roam options) can help in dense environments

## Prevention

1. **Broker on a static IP**, configured in devices as an **IP**
2. **Config backup** per device before firmware updates (and keep the Backlog lines)
3. **Unique topic** per device, set deliberately
4. **One device first** when updating a fleet
5. Separate **MQTT user per device class**, so one rotation doesn't silence the house

## FAQ

**Why does an IP work when the hostname doesn't?**
The device resolves DNS at boot, when it's least reliable, and Tasmota's resolver has had regressions. An IP removes the dependency.

**All my devices failed at once after I updated things. Where do I look?**
The broker. Device-side causes rarely hit everything simultaneously.

**Do I need TLS for local MQTT?**
On a trusted network, usually not — and on these devices it adds real failure modes.

**How do I avoid re-provisioning after a flash?**
Keep the Backlog command list and the config backup for each device.
