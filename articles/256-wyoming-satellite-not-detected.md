---
title: "Wyoming Satellite Not Detected in Home Assistant? Add It by IP"
slug: wyoming-satellite-not-detected
meta_description: "A voice satellite that never appears, or stops working after a power cycle. Manual setup on port 10700, the stale-connection problem and how to verify the service."
updated: October 2026
cluster: round 12 (tech) — HA community threads and GitHub issues
competition: LOW
---

# Wyoming Satellite Not Detected in Home Assistant? Add It by IP

Two separate problems here:

- **Never discovered** → add it manually; discovery is a convenience, not a requirement
- **Worked, then stopped after a reboot/power cycle** → a stale connection on the Home Assistant side

## 1. Add it manually (do this first)

Don't wait for discovery:

**Settings → Devices & Services → Add Integration → Wyoming Protocol**, then enter the satellite's **IP address** and port **10700**.

If that works, discovery was the only thing broken, and you have a working satellite. Discovery relies on zeroconf/mDNS, which fails across VLANs, with multicast filtering, or when the HA container isn't on host networking.

## 2. Verify the satellite is actually serving

On the satellite (Pi Zero 2 W, Pi 4, whatever):

```bash
systemctl status wyoming-satellite
systemctl status wyoming-openwakeword   # if you run local wake word
journalctl -u wyoming-satellite -n 50 --no-pager
ss -lntp | grep 10700
```

You want the service **active** and something **listening on 10700**. From another machine:

```bash
nc -vz SATELLITE_IP 10700
```

If the port isn't open, it's a satellite problem — check the unit file's arguments (`--uri tcp://0.0.0.0:10700` rather than binding to localhost) and that the service started after the network came up.

## 3. Audio devices are the usual satellite-side failure

The service starts and dies, or runs with no audio:

```bash
arecord -l        # capture devices
aplay -l          # playback devices
arecord -D plughw:CARD=seeed2micvoicec,DEV=0 -r 16000 -c 1 -f S16_LE -t wav test.wav
aplay test.wav
```

The `--mic-command` / `--snd-command` device strings in your service file must match what `arecord -l` reports. A HAT that enumerates differently after a kernel update is a very common cause of "it stopped working" — and a reason to use `CARD=` names rather than `hw:1,0`.

## 4. It stops after power-cycling the satellite

Documented behaviour: HA **holds the old connection open**. Wake word detection and streaming start on the satellite, but HA's "Assist in progress" never becomes active because the stale session was never dropped.

Fixes, cheapest first:
- **Reload the Wyoming integration** (Settings → Devices & Services → Wyoming → ⋮ → Reload)
- **Restart Home Assistant**
- Avoid the problem: give the satellite a **static IP/DHCP reservation**, and bring it up and down cleanly rather than yanking power

Related: a satellite rediscovered as a **new device** on every restart usually means its advertised name or address keeps changing — pin both.

## 5. Networking details that bite

- HA in Docker needs **host networking** for zeroconf
- Satellite and HA on the **same VLAN**, or mDNS reflection plus a route for TCP 10700
- No **client isolation** on the Wi-Fi
- Firewall on the satellite allowing 10700 inbound

## 6. A note on the project's status

Wyoming Satellite as a DIY project has been **deprecated** in favour of ready-made voice hardware, while still working with the Wyoming protocol. If you're building new, factor that in; if you have one running, nothing stops working because of it — but expect fewer fixes upstream, which makes pinning a known-good OS image worthwhile.

## Prevention

1. **Static IP** for every satellite
2. Use **`CARD=` names** in the service file, not `hw:1,0`
3. Keep a **working SD card image** — cloning a known-good satellite is the fastest recovery, as several people have found
4. Note HA's **integration reload** as your first move after any satellite restart
5. Document the satellite's service arguments somewhere other than the satellite

## FAQ

**Which port does Wyoming use?**
10700 for the satellite. Other Wyoming services (Whisper, Piper, wake word) use their own.

**Does discovery need to work?**
No. Manual setup by IP is fully supported and more reliable.

**Why does it need HA restarted after the satellite reboots?**
HA can keep a stale connection. Reload the integration instead of restarting everything.

**Audio worked, then stopped after an OS update.**
The capture device name changed. Check `arecord -l` and your service file.
