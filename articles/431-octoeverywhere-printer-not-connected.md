---
title: "OctoEverywhere: \"Printer Is Not Connected\" (Error 601)"
slug: octoeverywhere-printer-not-connected
meta_description: "Error codes 601, 602 and 612 explained, plus what to check on the plugin side when they persist rather than clearing on their own."
updated: October 2026
cluster: round 14 (tech) — OctoEverywhere API docs and plugin repositories
competition: LOW
---

# OctoEverywhere: "Printer Is Not Connected" (Error 601)

OctoEverywhere's error codes are documented and specific, which makes this unusually diagnosable. Three you'll actually see:

| Code | Meaning | Nature |
|---|---|---|
| **601** | Printer is not connected to OctoEverywhere — the plugin has no live connection to the service | Temporary |
| **602** | OctoEverywhere's connection to the plugin timed out — connected, but too slow to respond | Temporary |
| **612** | Plugin error — an error in the plugin prevented the call completing | Usually a plugin bug |

All three are marked temporary or transient, which means **a single occurrence is not a fault.** If it clears within a minute, there is nothing to fix. The rest of this is about codes that persist.

## 1. Is the plugin running and connected?

**OctoPrint:**

```bash
sudo systemctl status octoprint
sudo journalctl -u octoprint -n 50 | grep -i octoeverywhere
```

**Klipper (Moonraker plugin):**

```bash
sudo systemctl status octoeverywhere
sudo journalctl -u octoeverywhere -n 60 --no-pager
```

A healthy plugin logs a successful connection to the service and periodic keepalives. What the log tells you:

- **`Connection closed` repeatedly** — the plugin is reconnecting. Network, or the service.
- **TLS or certificate errors** — the host's CA bundle or clock. Check `date`.
- **Nothing at all** — the plugin isn't loaded. For OctoPrint, confirm it's enabled in the plugin manager; for Klipper, that the service is enabled.

## 2. Network from the printer outward

The plugin makes an **outbound** connection — no port forwarding needed, which rules out a whole class of problems and narrows the rest to egress:

```bash
# on the printer host
curl -sI https://octoeverywhere.com | head -3
nslookup octoeverywhere.com
```

Causes of persistent 601:

- **DNS.** A Pi pointed at a dead internal resolver fails everything outbound. Test with `nslookup ... 1.1.1.1` to compare.
- **A restrictive firewall or guest VLAN** blocking outbound HTTPS/websockets. The connection is long-lived; a firewall that drops idle connections causes repeated reconnects rather than a clean failure.
- **IPv6 half-working.** A host with an IPv6 address and no working IPv6 route times out before falling back. Confirm by preferring IPv4 temporarily.
- **Clock skew.** TLS fails on a large offset:

```bash
timedatectl status
```

## 3. 602: timeouts

The plugin is connected and too slow. Almost always the host:

```bash
uptime
top -b -n1 | head -15
vcgencmd get_throttled    # Raspberry Pi
```

- **A Pi doing camera streaming at 1080p plus Klipper plus OctoEverywhere** is CPU-starved. Reduce the stream resolution; 720p15 is plenty for monitoring.
- **`get_throttled` non-zero** means undervoltage or thermal throttling. A marginal power supply is a frequent cause of everything-is-slow on a Pi.
- **SD card exhaustion.** An old, worn card makes every operation slow:

```bash
dd if=/dev/zero of=/tmp/t bs=1M count=100 oflag=direct 2>&1 | tail -1
```

Single-digit MB/s on that write is a dying card.

## 4. 612: plugin errors

The documented guidance is that repeated 612s warrant contacting support — it indicates a plugin bug rather than a configuration problem. Before that:

- **Update the plugin.** The majority of 612s are fixed in later releases.
- **Check for a conflicting plugin.** On OctoPrint, two plugins doing remote access (OctoEverywhere plus Obico plus a tunnel) can interfere.
- **Reinstall rather than reconfigure.** For the Klipper plugin:

```bash
cd ~/octoeverywhere
git pull
./install.sh
```

The installer re-links the service and re-registers with Moonraker, which fixes state problems that configuration edits don't.

## 5. Webcam works, printer state doesn't (or the reverse)

These are separate data paths:

- **Printer state** comes from OctoPrint's or Moonraker's API. A Moonraker that isn't trusting the plugin's client address returns 401s:

```ini
# moonraker.conf
[authorization]
trusted_clients:
    127.0.0.1
    ::1
```

- **Webcam** comes from your stream URL. A wrong snapshot/stream URL gives a working printer with no image. The plugin discovers it from Moonraker's config, so fixing it in `moonraker.conf` fixes it here:

```ini
[webcam monitor]
stream_url: /webcam/?action=stream
snapshot_url: /webcam/?action=snapshot
```

## 6. Multiple printers

Each printer needs its own plugin installation and its own printer ID. A cloned SD card carries the previous printer's ID, and both printers then fight over one identity — producing intermittent 601s on both. Re-run the installer and link as a new printer on the clone.

## What not to do

- **Don't forward ports.** The architecture is outbound-only; opening ports adds risk and no capability.
- **Don't act on a single 601 or 602.** They're documented as temporary.
- **Don't clone a printer's SD card without re-linking.** Duplicate IDs cause exactly this.
- **Don't run two remote-access plugins.** Pick one.

## Prevention

| Habit | Why |
|---|---|
| Adequate Pi power supply, verified with `get_throttled` | Undervoltage causes 602s and much else |
| 720p15 camera stream | Leaves CPU for Klipper and the plugin |
| Plugin kept current | Most 612s are fixed upstream |
| Re-link after cloning an SD card | Prevents duplicate printer IDs |

## FAQ

**Does it work without an account?**
No — the service brokers the connection, so an account is required.

**Is my printer exposed to the internet?**
Not directly; the plugin dials out and the service mediates. That's the security advantage over port forwarding.

**Can I self-host the relay?**
No. If you want fully self-hosted remote access, a VPN (Tailscale, WireGuard) to your printer is the alternative.

**Notifications stopped.**
Separate from connectivity — check the notification settings in your account and that the plugin version supports them.
