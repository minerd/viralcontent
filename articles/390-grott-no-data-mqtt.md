---
title: "Grott: No Growatt Data Reaching MQTT"
slug: grott-no-data-mqtt
meta_description: "Grott runs and nothing publishes. The static IP requirement, the nomqtt comment trap, inverter type defaults and how to confirm packets arrive."
updated: October 2026
cluster: round 14 (tech) — johanmeijer/grott GitHub and HA community
competition: LOW
---

# Grott: No Growatt Data Reaching MQTT

Grott works by **intercepting** the traffic from your Growatt datalogger to Growatt's servers. Nothing it does is initiated by Grott, which means the first question is always: *are packets arriving at all?*

```bash
docker logs grott --tail 50
```

A healthy Grott logs a line per packet:

```
- Grott - Growatt packet received
- Grott - Growatt original packet:
- Grott - MQTT message message published
```

| What you see | Where to look |
|---|---|
| No "packet received" lines | The datalogger isn't sending to Grott — section 1 |
| Packets received, no MQTT lines | MQTT config — section 2 |
| Packets received, decode errors | Inverter type / layout — section 3 |

## 1. The datalogger must be pointed at Grott, and Grott must not move

Grott's host needs a **static IP address**. The datalogger is configured with Grott's address, and a DHCP change silently ends the data flow — this is the single most common cause of "it stopped working".

Set a DHCP reservation for the Grott host, and then point the datalogger at it. The two usual methods:

- **ShineTools / the datalogger's own web interface**: set the server address to Grott's IP, port 5279.
- **Transparent redirection** at the router: DNAT traffic destined for Growatt's server IP on port 5279 to Grott. This avoids touching the datalogger at all and survives firmware updates.

```bash
# confirm Grott is listening
docker exec grott sh -c 'netstat -ltnp 2>/dev/null | grep 5279' || ss -ltnp | grep 5279
```

```yaml
services:
  grott:
    image: ledidobe/grott
    ports:
      - "5279:5279"
    volumes:
      - ./grott.ini:/app/grott.ini
    restart: unless-stopped
```

If no packets arrive, nothing else in this article matters. Verify with a packet capture on the host if you need certainty:

```bash
sudo tcpdump -ni any port 5279
```

## 2. The `nomqtt` comment trap

This one catches many people, because the sense is inverted from what you'd expect:

```ini
[MQTT]
# nomqtt = True        ← must stay commented out
ibroker = 192.168.1.10
iport = 1883
mtopic = energy/growatt
iuser = mqttuser
ipassword = mqttpass
retain = True
```

**`nomqtt = True` disables MQTT.** The shipped config has it commented; uncommenting it (or leaving a stray uncommented copy) turns publishing off while everything else looks healthy. If you see "packet received" and no "message published", check this line first.

Other MQTT points:

- `ibroker` must be an address Grott can reach. In Docker, not `localhost`.
- `retain = True` keeps the last value visible to Home Assistant between reports — worth having, because Growatt dataloggers report every few minutes and entities otherwise look unavailable.
- Credentials: Mosquitto 2.x refuses anonymous connections by default, so a config with no user/password fails against a modern broker.

Test the broker from inside the container:

```bash
docker exec grott sh -c 'mosquitto_pub -h 192.168.1.10 -u mqttuser -P mqttpass -t test/grott -m hello' 2>&1
```

## 3. Inverter type and record layout

Grott decodes Growatt's binary protocol using a record layout. If the layout doesn't match your inverter, you get packets and either no publish or nonsense values.

```ini
[Generic]
invtype = default
includeall = False
blockcmd = False
verbose = True
```

Guidance that matters:

- **Start with `invtype = default`** and no custom settings. Changing parameters from defaults has been reported to stop packets being processed entirely. Get it working on defaults, then customise.
- Newer models (NEO series, some hybrids) may need a layout that isn't in your Grott version. Check the version and the project's layout files before writing your own.
- `verbose = True` while commissioning prints the raw packet and the matched layout, which is the only way to see a layout mismatch.

An unknown record type logs something like:

```
- Grott - Growatt unknown record layout received, no processing done
```

That is a layout problem, not a network or MQTT one.

## 4. It stopped after working

- **DHCP change** on the Grott host (section 1)
- **Datalogger firmware update** resetting its server address — the DNAT approach is immune to this
- **Grott process alive but wedged.** Restarting has been the documented remedy for a stalled Grott:

```bash
docker restart grott
```

If you need that regularly, add a healthcheck and let Docker restart it.

## 5. Home Assistant sees the topic but no entities

MQTT discovery isn't automatic for Grott. Either enable its Home Assistant auto-discovery option, or define sensors by hand:

```yaml
mqtt:
  sensor:
    - name: "Solar Power"
      state_topic: "energy/growatt"
      value_template: "{{ value_json.values.pvpowerout | float / 10 }}"
      unit_of_measurement: "W"
      device_class: power
      state_class: measurement
```

Note the `/10` — Growatt reports many values scaled by 10. Values that are exactly ten times too large are this, not a decode error.

## What not to do

- **Don't run Grott on a DHCP address.** It will break.
- **Don't change inverter settings from defaults before it works.** It's a documented way to stop processing.
- **Don't block the datalogger's internet access** unless you've decided to give up the Growatt app. Grott can forward on to Growatt's servers; blocking breaks that.
- **Don't trust silence.** `verbose = True` during setup, off afterwards.

## Prevention

| Habit | Why |
|---|---|
| Static IP / DHCP reservation for the Grott host | The dominant cause of later failures |
| DNAT redirection rather than configuring the datalogger | Survives datalogger firmware updates |
| `retain = True` | Sensible availability in Home Assistant |
| Note your working `invtype` and layout version | Needed again after every upgrade |

## FAQ

**Does Grott stop data reaching Growatt's cloud?**
Only if you configure it to. By default it forwards, so the app keeps working.

**Can it write settings to the inverter?**
Grott supports some commands; `blockcmd` controls whether remote commands from Growatt are passed through. Blocking them is a reasonable security posture.

**Alternatives?**
Modbus over RS485 directly to the inverter gives richer data and no dependence on the datalogger — more wiring, more control.

**Values are ten times too big.**
Growatt's scaling. Divide by 10 (or 100 for some registers) in your template.
