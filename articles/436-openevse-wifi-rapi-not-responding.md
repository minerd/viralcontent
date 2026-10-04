---
title: "OpenEVSE: WiFi Module Not Connecting, RAPI Not Responding"
slug: openevse-wifi-rapi-not-responding
meta_description: "The controller stops answering RAPI after a charge, or the WiFi module falls back to AP mode. The RAPI-versus-WiFi conflict, MTU and the 5-minute fallback."
updated: October 2026
cluster: round 14 (tech) — OpenEVSE GitHub and support forum
competition: LOW
---

# OpenEVSE: WiFi Module Not Connecting, RAPI Not Responding

Two things to know before troubleshooting, because they reframe most problems:

> **In WiFi firmware 5.0.0 and above, sending raw RAPI commands is disabled** — it conflicts with the scheduler.

> **Using the RAPI API is no longer recommended if a WiFi module is fitted**, because the WiFi module and your RAPI client both talk to the controller and conflict.

So if you are scripting against RAPI on a unit with the WiFi module, you are using an unsupported combination, and intermittent failures are expected. Use the WiFi module's **HTTP API or MQTT** instead.

## 1. The WiFi module's own API

```bash
curl -s http://openevse.local/status | python3 -m json.tool
curl -s http://openevse.local/config | python3 -m json.tool
```

To change state, use the documented endpoints rather than RAPI pass-through:

```bash
# via MQTT, which is the cleanest integration path
mosquitto_pub -h 192.168.1.10 -t 'openevse/rapi/in/$FS' -m '' 
mosquitto_sub -h 192.168.1.10 -t 'openevse/#' -v
```

MQTT also solves the conflict question: the WiFi module owns the serial link and relays, so there is one consumer of the controller.

## 2. Controller stops answering RAPI at the end of every charge

A documented bug: on controller firmware D9.0.0, the EVSE **stops responding to RAPI at every end of charge**, the WiFi module stays frozen, and **only a power cycle recovers it.**

If that matches your symptom exactly — reliable, tied to session end, needs a power cycle — it is this, and the fix is a controller firmware update rather than anything in your configuration. Check your controller version:

```bash
curl -s http://openevse.local/status | python3 -c "import sys,json;d=json.load(sys.stdin);print(d.get('version'), d.get('evse_ver'))"
```

In the meantime, a scheduled power cycle (a smart plug on the EVSE's control supply, not the charging circuit) is an ugly but effective mitigation. Don't script a power cycle during a session.

## 3. WiFi module falls back to AP mode

> **If connection or re-connection fails — network not found, wrong password — OpenEVSE reverts to WiFi access point mode, and re-connection is attempted every 5 minutes.**

So the module appearing as an access point means it could not join your network. That's informative: it rules out the module being dead.

> **The firmware resets to the OpenEVSE access point if it doesn't connect to the specified access point within 5 minutes.**

Causes, in order:

- **2.4 GHz only.** The ESP-based module cannot use 5 GHz. A band-steering AP that won't offer 2.4 GHz leaves it unable to associate. Create a dedicated 2.4 GHz SSID for IoT.
- **WPA3-only or WPA2/WPA3 transition mode.** Older ESP firmware fails against WPA3. Set the SSID to WPA2-PSK.
- **A hidden SSID.** Supported inconsistently; use a visible one.
- **Special characters in the passphrase** mangled during entry.
- **Signal strength.** The module sits inside a metal enclosure, often in a garage at the edge of coverage. Check RSSI from its own page; anything worse than about −75 dBm is marginal.

## 4. The MTU problem

A specific, documented quirk: **OpenEVSE WiFi has issues with non-standard MTU settings; 1500 bytes is recommended.**

This matters if:

- Your network runs PPPoE (common on DSL) with an MTU of 1492
- You have a VPN or tunnel in the path
- A managed switch or AP is configured with jumbo frames

The symptom is a module that associates, gets an IP, and then fails on larger transfers — firmware updates, API responses, or the emoncms/MQTT connection — while pings work. Set the segment the EVSE is on to a standard 1500 MTU, or accept that its uplink needs clamping:

```bash
# on a Linux router, clamp MSS for that subnet
iptables -t mangle -A FORWARD -s 192.168.1.0/24 -p tcp --tcp-flags SYN,RST SYN \
  -j TCPMSS --clamp-mss-to-pmtu
```

## 5. Main web page won't load but the RAPI page does

Reported over a VPN: the main interface fails while a simpler page works. That's a size or asset-loading problem — the dashboard pulls more resources than the minimal pages. Consistent with section 4 (MTU), and also with a proxy that doesn't handle the module's responses well.

Test directly on the LAN, bypassing any tunnel. If it loads there and not over the VPN, the VPN's MTU is the suspect.

## 6. Firmware updates

The WiFi module and the controller have **separate firmware**, and both matter:

- **WiFi module**: updated over the air from its own web interface, or via USB.
- **Controller**: updated via the WiFi module's update page on recent versions, or with a programmer.

Update the controller firmware if you're on a version with the section-2 bug. Keep a note of both version numbers; many support discussions turn on which pair you're running.

```bash
curl -s http://openevse.local/status | grep -iE 'version|evse_ver'
```

## What not to do

- **Don't script raw RAPI against a unit with the WiFi module.** It's explicitly not recommended, and firmware 5.0.0+ blocks it.
- **Don't put the EVSE on a 5 GHz-only or WPA3-only SSID.**
- **Don't power-cycle during a charging session** as a scripted recovery.
- **Don't run it on a non-1500 MTU segment** and then debug the application.

## Prevention

| Habit | Why |
|---|---|
| MQTT or the HTTP API for integration, never raw RAPI | The supported path, and conflict-free |
| Dedicated 2.4 GHz WPA2 IoT SSID | Removes the association-failure class |
| Standard 1500 MTU on that segment | A documented requirement |
| Both firmware versions recorded | Most known bugs are version-specific |

## FAQ

**Does it work with Home Assistant?**
Yes, via MQTT with discovery, or an integration that uses the HTTP API. MQTT is the more robust route.

**Can I charge without the WiFi module?**
Yes — the controller works standalone. The module adds scheduling, monitoring and remote control.

**Solar-diverting / excess-PV charging?**
Via MQTT current limits from your energy monitoring, or by letting evcc or similar drive it.

**Energy totals reset.**
The controller keeps session and lifetime counters; a firmware update or a factory reset clears them. Record totals externally if they matter.
