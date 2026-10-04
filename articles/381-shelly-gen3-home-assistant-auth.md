---
title: "Shelly Gen3 Won't Add to Home Assistant"
slug: shelly-gen3-home-assistant-auth
meta_description: "Invalid authentication, not discovered, or no entities created. The firmware 1.8 auth change, the version requirement, and ShellyForHass conflicts."
updated: October 2026
cluster: round 14 (tech) — HA community and Shelly community
competition: LOW
---

# Shelly Gen3 Won't Add to Home Assistant

The answer for most current reports is a version requirement, and it's worth leading with because it saves everything else:

> **Shelly firmware 1.8+ changed device authorisation in a way older Home Assistant releases can't handle. To use a password-protected Gen3 device on firmware 1.8.99 / 2.0.0 or newer, you need Home Assistant 2026.5.0 or newer.**

So: check both version numbers first.

```
Settings → About                    (Home Assistant version)
Shelly web UI → Settings → Firmware (device version)
```

## 1. If you can't update Home Assistant yet

The documented workaround is to **disable the password on the device**:

```
Shelly web UI → Settings → Authentication → disable
```

Then add it to Home Assistant. This is acceptable only on a network where the device isn't reachable from anywhere untrusted — an unauthenticated Shelly accepts relay commands from anything on the LAN. Put IoT devices on their own VLAN if you do this.

Re-enable authentication once Home Assistant is current.

## 2. Use the core Shelly integration, not ShellyForHass

The old HACS custom component (`ShellyForHass`) and the built-in integration conflict. Symptoms: devices appear twice, entities with `_2` suffixes, or the core integration refusing to add a device the custom one already holds.

The clean order:

1. Remove the device's configuration from ShellyForHass
2. Uninstall ShellyForHass from HACS
3. **Restart Home Assistant**
4. Add the device through **Settings → Devices & Services → Add integration → Shelly**

Skipping the restart leaves the old component's listeners alive and the add still fails.

## 3. Not discovered at all

Gen3 devices are discovered by **mDNS**. Failures:

- **Different VLAN or subnet.** mDNS doesn't cross without a reflector. Add the device manually by IP — the integration's dialog accepts one, and this works regardless of discovery:

```
Add integration → Shelly → enter the device's IP
```

- **Client isolation** on the AP.
- **The device is in AP mode** — it never joined your Wi-Fi. Its own SSID (`ShellyXXX-...`) will be visible; connect to it and configure Wi-Fi.
- **2.4 GHz only.** Shellys don't do 5 GHz. A band-steering AP that won't hand out a 2.4 GHz association leaves them unable to join.

```bash
# confirm it's there and answering
curl -s http://192.168.1.77/shelly | python3 -m json.tool
```

That endpoint works without authentication on Gen2/Gen3 and returns the model, generation and firmware version — the fastest way to confirm you have the right IP and see what firmware you're on.

## 4. Added but no entities

- **The device is still initialising.** Gen3 devices enumerate components on connect; wait a minute and reload the integration.
- **Battery-powered models** (H&T, Door/Window) sleep. They create entities on their first wake-up report; press the button to force one. Showing unavailable between reports is normal.
- **A component disabled on the device.** If you disabled the relay or an input in the Shelly web UI, no entity is created for it.
- **Outbound websocket not enabled** for battery devices: these push to Home Assistant rather than being polled. In the device's web UI, **Settings → Outbound WebSocket** must be enabled and pointed at Home Assistant:

```
ws://<home-assistant-ip>:8123/api/shelly/ws
```

The integration configures this automatically when it can reach the device; it fails silently if the device can't reach Home Assistant back — which is the usual VLAN problem in reverse.

## 5. Invalid authentication with the right password

- Gen2/Gen3 use digest auth with the username **`admin`** fixed. Only the password is yours.
- A password containing characters the device's own UI mangled on entry — reset it to something simple ASCII and retry.
- Firmware mid-upgrade. Let it finish.

## What not to do

- **Don't leave authentication disabled permanently** on a device that controls mains wiring.
- **Don't run both Shelly integrations.** Remove one properly, with a restart.
- **Don't add Gen3 devices by cloud.** The integration is local; cloud adds a dependency and no capability.
- **Don't downgrade device firmware** to work around the auth change. Update Home Assistant instead.

## Prevention

| Habit | Why |
|---|---|
| Keep Home Assistant current before updating device firmware | The auth change broke the old direction |
| Static DHCP reservations for every Shelly | Discovery problems become irrelevant |
| Dedicated 2.4 GHz IoT SSID | Shellys cannot use 5 GHz |
| One integration per device class | Removes the duplicate-entity class |

## FAQ

**Does it work with no internet?**
Yes, entirely local. Disable the cloud connection in the device's settings if you want.

**Can I use MQTT instead?**
Yes — Gen2/Gen3 speak MQTT and work with HA's MQTT discovery. More setup, but it decouples you from integration version requirements.

**Scripts on the device?**
Gen2/Gen3 run JS scripts locally, which survive a Home Assistant outage. Useful for safety-critical behaviour.

**Energy values reset after a reboot.**
Shelly's counters are device-side; use HA's utility meter helper for durable totals.
