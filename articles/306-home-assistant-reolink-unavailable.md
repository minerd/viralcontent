---
title: "Home Assistant Reolink Integration Unavailable? Ports, HTTP and Firmware"
slug: home-assistant-reolink-unavailable
meta_description: "Reolink entities go unavailable, ONVIF push stops, or setup fails outright. The camera settings HA needs enabled and the firmware traps."
updated: October 2026
cluster: round 13 (tech) — HA core Reolink issues
competition: LOW
---

# Home Assistant Reolink Integration Unavailable? Ports, HTTP and Firmware

The Reolink integration doesn't use RTSP for control — it uses the camera's **HTTP API**, plus **ONVIF** for push events. Three different switches on the camera have to be on, and Reolink's firmware turns them off in various combinations depending on model and version.

## 1. The four camera settings that must be enabled

In the Reolink app or web UI, under **Settings → Network → Advanced → Port Settings**:

- **HTTP** — on. This is the one most often off by default on newer firmware, and with it off, setup fails immediately with a connection error. HTTPS alone is not enough for all firmware versions; the integration prefers HTTP on the LAN.
- **ONVIF** — on. Without it the integration still works, but every entity updates only on a 30-second poll instead of instantly. "Motion sensor is slow" is almost always this.
- **RTSP** — on, if you want a stream.
- **RTMP** — can stay off.

Then, under **Settings → Network → Advanced**:

- **UID / Reolink cloud** can be off; the integration is local.

And critically: the HA user account on the camera must be **admin**. A "user"-level account can read but cannot subscribe to ONVIF events, and the integration reports capabilities it then can't use. Create a dedicated admin account for HA rather than reusing the app's.

## 2. Prove the camera answers from the HA host

```bash
curl -s "http://192.168.1.50/api.cgi?cmd=GetDevInfo&user=ha&password=yourpass" | head -40
```

A JSON blob with `model` and `firmVer` means HTTP API access is good. What the failures mean:

- **Connection refused** → HTTP port disabled, or the port moved from 80
- **`"rspCode": -6`** → login failed; wrong credentials or the account is locked out
- **Empty / hangs** → wrong IP, or the camera is on a VLAN HA can't reach
- **A login page in HTML** → you hit the web UI, not the API; check the port

If you changed the HTTP port on the camera, the integration needs that port at setup time — it's in the advanced options of the config flow, not discoverable afterwards without re-adding.

## 3. "Available at setup, unavailable later"

This is the most reported pattern, and there are three distinct causes.

**ONVIF subscription expiry.** The integration subscribes to the camera's ONVIF push and renews. If renewal fails, entities freeze at their last value and eventually go unavailable. In the HA log:

```
Reolink error while subscribing to ONVIF
```

Fixes, in order: reboot the camera (clears stale subscriptions, of which cameras hold a small fixed number), then reduce the number of other things subscribing to the same camera. A camera shared between HA, Frigate's ONVIF, and the Reolink NVR can exhaust its subscription slots — this is a hard device limit, not a bug.

**DHCP address change.** The integration follows DHCP in recent versions, but if your camera lands on an address in a different subnet or a VLAN, it won't. Assign a static DHCP reservation. This is worth doing for every camera regardless.

**Firmware update changed defaults.** Reolink firmware has, more than once, turned HTTP or ONVIF off on upgrade. After any camera firmware update, re-check the four settings in section 1 before debugging anything in HA.

## 4. Battery models behave differently

Argus/Reolink battery cameras sleep. They are **not** continuously available by design, and the integration reflects that: entities show unavailable while asleep. This is correct behaviour, not a fault.

Practical consequences:

- No continuous RTSP stream. Snapshots on motion only.
- Commands queue until the camera wakes.
- Polling them aggressively drains the battery fast.

If you need always-on, these models aren't the right hardware, and no HA setting changes it.

## What not to do

- **Don't delete and re-add the integration on every failure.** It loses entity IDs and your automations break. Reboot the camera first.
- **Don't enable Reolink's cloud/UID to "help connectivity".** The integration is local; cloud adds nothing and exposes the camera.
- **Don't point HA, Frigate's ONVIF, and an NVR at the same camera** and expect all three to get events. Subscription slots are limited; let one subscribe and have the others consume from it.
- **Don't use the camera's `admin` account with its default password.** Reolink cameras are a common target; a dedicated account with a long password costs nothing.

## Prevention

| Habit | Why |
|---|---|
| Static DHCP reservation per camera | Removes address-change failures permanently |
| Re-check HTTP/ONVIF after every firmware update | Firmware resets these more often than you'd expect |
| One ONVIF subscriber per camera | Subscription slots are a finite device resource |
| Dedicated admin account named for HA | Makes camera-side logs readable and revocation easy |

## FAQ

**Does the integration need the Reolink NVR, if I have one?**
It can talk to the NVR and expose its channels, which is usually better than talking to each camera. Add the NVR, not the cameras.

**Streams work but motion events don't.**
ONVIF, specifically. RTSP has nothing to do with events.

**Can I avoid giving HA admin on the camera?**
Not for push events. You can run poll-only with a limited user, accepting ~30 s latency.

**Entities exist but are all unknown after a restart.**
Normal until the first poll or event. If they stay unknown, it's the ONVIF subscription, per section 3.
