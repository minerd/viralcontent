---
title: "shairport-sync: AirPlay Device Not Showing Up"
slug: shairport-sync-not-visible
meta_description: "The speaker vanishes from the AirPlay list, or never appears. Bonjour across subnets, Ubiquiti mDNS settings, VPNs and the disappear-after-use bug."
updated: October 2026
cluster: round 14 (tech) — mikebrady/shairport-sync GitHub issues
competition: LOW
---

# shairport-sync: AirPlay Device Not Showing Up

AirPlay discovery is **Bonjour/mDNS**, and almost every "not visible" case is a network problem rather than shairport-sync. Confirm the service is advertising before anything else:

```bash
systemctl status shairport-sync
avahi-browse -rt _raop._tcp        # AirPlay 1
avahi-browse -rt _airplay._tcp     # AirPlay 2
```

If `avahi-browse` on the same machine shows the service, shairport-sync is doing its job and the problem is between there and your phone.

## 1. The network causes, in order

**A VPN on either device.** This is the one people least expect: if the iPhone is on a VPN and shairport-sync isn't (or vice versa), they are on different networks as far as mDNS is concerned and the AirPlay service is simply not visible. Turn the VPN off to test — it resolves a surprising share of reports.

**Different subnets or VLANs.** mDNS is link-local. An iPhone on the guest VLAN will never see a speaker on the main one without an mDNS reflector:

```bash
# /etc/avahi/avahi-daemon.conf on a router/bridge host
[reflector]
enable-reflector=yes
```

**Ubiquiti and other managed Wi-Fi.** Documented specifically: Ubiquiti router and AP settings occasionally stop Bonjour services from appearing. The relevant toggles are **"Multicast DNS" / mDNS reflector** (must be on, and must include the right networks) and **"Multicast and Broadcast Filtering"** (must not block the service). Enabling mDNS on the networks involved is usually the fix.

**AP / client isolation.** Blocks the discovery outright.

**IGMP snooping** misbehaving on a managed switch silently drops multicast between ports.

## 2. "Sometimes it doesn't appear"

Intermittent visibility, resolving later on its own, with restarts not helping immediately. This pattern is Avahi's name registration racing something else:

- **Two devices advertising the same name.** Avahi renames on collision (`Speaker (2)`), and some clients cache the old name. Give each instance a distinct name:

```conf
# /etc/shairport-sync.conf
general = {
  name = "Kitchen";
};
```

- **A second mDNS responder on the host.** `avahi-daemon` and a Docker container running its own responder, or `mdnsd`, fight. One per host.
- **The host's hostname changed** after DHCP, invalidating the advertised record.

Toggling Wi-Fi on the phone forces a fresh browse and is a legitimate confirmation that it's a caching/discovery issue rather than shairport-sync.

## 3. "Disappears after streaming, or after the second disconnect"

Reported in several forms: the instance stops appearing after a period of use, or consistently vanishes after the second client disconnect, while other AirPlay devices remain discoverable.

Practical handling:

- **Restart on disconnect** as a stopgap:

```ini
# /etc/systemd/system/shairport-sync.service.d/override.conf
[Service]
Restart=always
RestartSec=2
```

- **Check the build.** Reinstalling from source has resolved visibility problems where a distribution package was stale — the project moves faster than most repositories, and AirPlay 2 support in particular has had many fixes.

```bash
shairport-sync -V
```

The version string lists the compiled-in options (`AirPlay2`, `avahi`, `alsa`, `soxr`). A build without `AirPlay2` will not appear to clients that only look for AirPlay 2 services.

## 4. AirPlay 1 vs AirPlay 2

They advertise different service types and have different requirements. A build compiled for AirPlay 1 only is still discoverable by most Apple devices, but:

- AirPlay 2 needs **nqptp** running alongside shairport-sync, and a build with `--with-airplay-2`
- Multi-room grouping is AirPlay 2 only

```bash
systemctl status nqptp
```

`nqptp` not running is the usual reason an AirPlay-2 build is visible but won't connect or won't group.

## 5. Visible but won't play

Separate problem, and worth not conflating:

```bash
journalctl -u shairport-sync -n 50
```

- **ALSA device busy** — another process has the output. One consumer per device.
- **Wrong output device:**

```conf
alsa = {
  output_device = "hw:1";
};
```

```bash
aplay -l
```

- **A password/`password =` set** in the config, which some clients handle poorly.

## What not to do

- **Don't run two mDNS responders on one host.** It's the main cause of intermittent visibility.
- **Don't test with a VPN active.** You'll chase a network problem that isn't there.
- **Don't rely on the distribution package** for AirPlay 2. Check `-V` and build if needed.
- **Don't give two instances the same name.** Collisions produce exactly the symptoms you're debugging.

## Prevention

| Habit | Why |
|---|---|
| Distinct name per instance, set explicitly | Removes collisions and client caching confusion |
| mDNS reflector configured if you use VLANs | Discovery is link-local by design |
| `Restart=always` on the service | Covers the disappear-after-use cases |
| Verify `shairport-sync -V` after upgrades | Build options determine what's even possible |

## FAQ

**Does it work from Android?**
Not natively — AirPlay is Apple's. There are third-party senders of varying quality.

**Can one host serve several rooms?**
Multiple instances with different names and output devices, yes.

**Latency / lip sync?**
shairport-sync honours the AirPlay timing model and is good for audio; video sync depends on the sender.

**Metadata and cover art?**
Available via the metadata pipe or MQTT, with the right build options.
