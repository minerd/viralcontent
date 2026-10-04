---
title: "Bambu Lab Printer Won't Connect to Home Assistant in LAN Mode"
slug: bambu-lab-home-assistant-lan-mode
meta_description: "\"Failed to connect. Check provided settings.\" The three printer toggles, port 8883 not 1883, and the integration still calling the cloud."
updated: October 2026
cluster: round 14 (tech) — greghesp/ha-bambulab GitHub issues and HA community
competition: LOW
---

# Bambu Lab Printer Won't Connect to Home Assistant in LAN Mode

The integration talks to the printer over **MQTT on port 8883 with TLS**, using the printer's serial number and access code. Three things must be true on the printer and one on your network.

## 1. The three printer settings

On the printer's screen:

```
Settings → (gear) → General → LAN Only Mode: ON
Settings → General → Developer Mode / LAN Mode Liveview: ON
Settings → WLAN → note the Access Code
```

- **LAN Only Mode** is what exposes the local MQTT broker. Without it, the printer talks to Bambu's cloud and the local port is closed or restricted.
- **LAN Liveview / Developer Mode** is needed for the camera and, on several firmware versions, for the full MQTT topic set. A printer in LAN mode without it connects and reports almost nothing.
- **The access code** is the MQTT password. It changes when you toggle LAN mode or reset the network — re-copy it after any network change.

Then collect:

| Field | Where |
|---|---|
| Serial number | Printer screen, or the Bambu app's device page |
| Access code | Settings → WLAN on the printer |
| IP address | Settings → WLAN, or your DHCP leases |

## 2. Port 8883, not 1883

A frequent misdiagnosis: connection refused on **1883**. The printer's local broker listens on **8883 with TLS**, using a self-signed certificate.

```bash
# from the Home Assistant host
nc -zv 192.168.1.80 8883
openssl s_client -connect 192.168.1.80:8883 </dev/null 2>&1 | head -5
```

A refused connection on 8883 means LAN mode is off, or the printer is unreachable. A TLS handshake that completes means the broker is there and you're down to credentials.

Test credentials directly:

```bash
mosquitto_sub -h 192.168.1.80 -p 8883 \
  -u bblp -P YOUR_ACCESS_CODE \
  --insecure \
  -t 'device/YOUR_SERIAL/report' -v -C 1
```

The username is literally **`bblp`** on all models. `--insecure` skips certificate verification, which is necessary against the printer's self-signed cert. A report payload here proves everything except the integration.

## 3. The integration still calling the cloud

A documented bug: **the integration making calls to `api.bambulab.com` even in LAN-only mode.** On a network where the printer has no internet, or where you deliberately block it, those calls time out and setup fails with a generic message.

Mitigations:

- Choose the **LAN mode** option explicitly in the config flow rather than cloud, and provide serial, IP and access code.
- Allow the Home Assistant host outbound access during setup even if the printer has none.
- Keep the integration current; this has been addressed across versions.

A related reported symptom: **"Timed out trying to connect to Bambu Lab cloud"** when you never asked for cloud. Same cause.

## 4. Network reachability

- **VLAN isolation.** A printer on an IoT VLAN with no route from Home Assistant cannot be reached. Open 8883 from HA to the printer, and 6000 if you want the camera stream.
- **mDNS** is used for discovery only; manual configuration with the IP bypasses it. Always add manually — it's more reliable and it survives discovery problems.
- **Static DHCP reservation for the printer.** The integration stores the IP; a lease change breaks it silently. This is worth doing before anything else.
- **AP isolation** on the Wi-Fi blocks it entirely.

## 5. The integration breaks Home Assistant generally

Reported: a general connection issue in Home Assistant while this integration is installed. The shape is an integration retrying a blocking call and starving the event loop.

If HA becomes sluggish after adding it:

```bash
grep -iE 'bambu|blocking call' /config/home-assistant.log | tail -40
```

Disable the integration, confirm HA recovers, then update it and re-enable. Running a months-old version of a fast-moving custom integration is the usual reason.

## 6. Firmware

Bambu firmware changes have affected local access more than once, including an authorisation change that broke third-party local control. The practical position:

- **Note your firmware version** before and after any update.
- Read the integration's issues for your model and firmware before updating, if local control matters to you.
- Firmware that exposes MQTT on 8883 and honours the access code is what you need; versions that restrict it cannot be worked around from Home Assistant's side.

```
Printer → Settings → Device → Firmware version
```

## What not to do

- **Don't use port 1883.** It isn't the local broker's port.
- **Don't rely on discovery.** Add manually with the IP.
- **Don't verify the printer's certificate.** It's self-signed; `--insecure` / the integration's own handling is correct.
- **Don't update printer firmware blind** if you depend on local control.

## Prevention

| Habit | Why |
|---|---|
| LAN mode + developer mode + access code recorded | The three things the integration needs |
| Static DHCP reservation for the printer | The integration stores the IP |
| `mosquitto_sub` test before touching the integration | Splits printer from Home Assistant in one command |
| Integration kept current | Cloud-call and auth fixes land in releases |

## FAQ

**Does LAN mode disable the Bambu app?**
Remote access via the app stops; local control from Bambu Studio on the same network continues with the access code.

**Can I use AMS and multi-colour from HA?**
AMS state is exposed; initiating a colour change is limited by what the printer's MQTT interface accepts.

**Camera doesn't work.**
Separate stream on its own port, and it requires LAN Liveview. Some models expose only a snapshot.

**P1 versus X1 differences?**
The X1 series exposes more sensors; the P1 has no chamber camera in the same way. Missing entities are often model limitations rather than faults.
