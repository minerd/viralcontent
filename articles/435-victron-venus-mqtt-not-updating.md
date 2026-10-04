---
title: "Victron Venus OS: MQTT Data Not Updating in Home Assistant"
slug: victron-venus-mqtt-not-updating
meta_description: "Values arrive once then stop. The keepalive Venus requires, version-specific breakages, and the broker bridge configuration."
updated: October 2026
cluster: round 14 (tech) — Victron Community and HA community
competition: LOW
---

# Victron Venus OS: MQTT Data Not Updating in Home Assistant

The behaviour that explains most of these reports:

> **Venus OS stops publishing to MQTT unless it receives a periodic keepalive.** Values arrive when you first connect, then stop within a minute.

That is by design — it avoids a GX device publishing continuously to nobody. Anything consuming Venus MQTT must send the keepalive.

## 1. Send the keepalive

Publish an empty message to the keepalive topic at least every 30 seconds (the window is 60):

```
R/<portal-id>/keepalive
```

```bash
# find your portal id (the VRM id, shown in Venus settings)
mosquitto_sub -h 192.168.1.50 -t 'N/+/system/0/Serial' -C 1 -v
```

```bash
# keepalive loop
while true; do
  mosquitto_pub -h 192.168.1.50 -t 'R/abc123def456/keepalive' -m ''
  sleep 30
done
```

In Home Assistant, as an automation:

```yaml
automation:
  - alias: Victron MQTT keepalive
    trigger:
      - platform: time_pattern
        seconds: "/30"
    action:
      - service: mqtt.publish
        data:
          topic: "R/abc123def456/keepalive"
          payload: ""
```

A documented cause of "stops after a random period" is **keepalives not being sent properly** — either not at all, or to the wrong portal id. If your data stops after roughly a minute every time, this is it.

Note: integrations and custom components that handle Venus MQTT send the keepalive for you. If you are consuming the topics directly with MQTT sensors, it's yours to do.

## 2. Enable MQTT on the GX device

```
Venus → Settings → Services → MQTT on LAN (SSL) / MQTT on LAN (plaintext)
```

- **Plaintext** on 1883 is simplest on a trusted LAN.
- **SSL** on 8883 requires the device's certificate to be trusted by your client, which is where bridging gets fiddly.

Confirm it's publishing:

```bash
mosquitto_sub -h 192.168.1.50 -t 'N/#' -v | head -20
```

Nothing at all means the service is off or the firewall is blocking. Values once and then silence means section 1.

## 3. Version-specific breakages

Two documented cases worth checking before anything else:

- **Venus OS 3.20 broke MQTT**, with users resolving it by rolling back to 3.14.
- **Venus OS v3.31 was released specifically to fix an empty-username login problem** that prevented MQTT connections.

So if MQTT stopped working immediately after a firmware update, check the release notes rather than your configuration. And if you are connecting with an **empty username**, move to v3.31 or later, or supply a username.

```
Venus → Settings → General → Firmware version
```

Victron keeps the previous version available for rollback on the device, which makes bisecting easy.

## 4. Bridging to your own broker

The usual architecture is a Mosquitto bridge from Venus into your main broker, so Home Assistant has one broker:

```conf
# /share/mosquitto/victron.conf  (HA Mosquitto add-on)
connection victron
address 192.168.1.50:1883
topic N/# in 0
topic R/# out 0
topic W/# out 0
bridge_protocol_version mqttv311
cleansession true
try_private false
```

Specifics that matter:

- **`try_private false`.** Not all brokers support the private-bridge extension, and Venus's embedded broker is one case where leaving it true causes the bridge to fail to establish.
- **`R/#` and `W/#` outbound** — `R` carries read requests *and the keepalive*, `W` carries writes. Bridging only `N/#` inbound means you receive data and cannot send the keepalive, so you're back to section 1.
- **A reported Mosquitto quirk:** the add-on not picking up configuration files until you open Addons → Mosquitto, change a setting, save, and restart. If your bridge config appears to be ignored, do that.

```bash
# in the HA add-on
docker logs addon_core_mosquitto --tail 50 | grep -i bridge
```

## 5. Writable topics stopped working

A reported regression in a 3.70 beta: the `homeassistant` MQTT topic no longer writeable. Writes to Venus go to `W/<portal-id>/...`:

```bash
mosquitto_pub -h 192.168.1.50 -t 'W/abc123def456/settings/0/Settings/CGwacs/BatteryLife/State' \
  -m '{"value": 9}'
```

If reads work and writes don't:

- Confirm you're publishing to `W/`, not `N/`
- Check the bridge forwards `W/#` outbound (section 4)
- On a beta firmware, check the release notes

## 6. Full restart sometimes required

Reported and worth knowing: stopping Home Assistant entirely for a few minutes and restarting it restored MQTT. That points at a stale subscription or a half-open connection on the broker side rather than at Venus.

Less disruptive first attempts:

```bash
# restart just the broker
# then reload the MQTT integration in HA
```

If a full HA restart is regularly needed, look at the broker's connection state — a client that reconnects without a clean disconnect can leave a subscription that receives nothing.

## What not to do

- **Don't consume Venus MQTT without sending keepalives.** It will stop, every time.
- **Don't bridge only the inbound topics.** You need `R/` outbound for the keepalive.
- **Don't update Venus firmware mid-project** without reading the notes; MQTT has broken and been fixed across versions.
- **Don't expose the GX device's MQTT to the internet.** `W/` topics can change inverter settings.

## Prevention

| Habit | Why |
|---|---|
| Keepalive automation, independent of anything else | The dominant cause of data stopping |
| `try_private false` and `R/#`/`W/#` in the bridge | A bridge that actually works both ways |
| Note the working Venus version | Firmware regressions have hit MQTT twice |
| Portal id recorded in your config comments | Every topic depends on it |

## FAQ

**Is there an alternative to MQTT?**
Modbus TCP on the GX device is the other local interface, and it needs no keepalive. Register maps are published by Victron. Many people prefer it for exactly that reason.

**Does it work without VRM/internet?**
Yes, MQTT on LAN is entirely local.

**Why are some values missing?**
Venus publishes per-service trees; a device not on the GX bus has no topics. `N/#` shows everything available.

**Values update slowly.**
Venus publishes on change with a minimum interval. Modbus polling gives you control over the rate.
