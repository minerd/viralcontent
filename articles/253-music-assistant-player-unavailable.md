---
title: "Music Assistant Player Unavailable? mDNS, Ad Blockers and Duplicate Providers"
slug: music-assistant-player-unavailable
meta_description: "Players that vanish, go unavailable after idle, or stop a few seconds into playback. The multicast requirement, the DNS-filter trap and provider conflicts."
updated: October 2026
cluster: round 12 (tech) — Music Assistant GitHub discussions, docs and HA community
competition: LOW
---

# Music Assistant Player Unavailable? mDNS, Ad Blockers and Duplicate Providers

Three symptoms, three different causes. Identify yours first.

- **Players never appear** → discovery (mDNS/multicast)
- **Playback starts then stops after a few seconds** → streaming reachability, often a DNS filter
- **Player works, then goes unavailable after idle** → the device or a duplicate provider

## 1. Players never show up: multicast

Music Assistant discovers most players with **mDNS**, which is multicast. Any network that filters it hides your speakers.

Check:
- MA, Home Assistant and the players on the **same subnet/VLAN**. Across VLANs you need **mDNS reflection/repeater** on the router
- **IGMP snooping / multicast filtering** on managed switches — the usual culprit
- **Client isolation** off on the Wi-Fi the speakers use
- In Docker: **host networking**. Bridge mode breaks discovery
- As a test, add a player **manually by IP** where the provider allows it. If manual works and discovery doesn't, it's multicast, confirmed

## 2. Playback stops after a few seconds: check your DNS filter

This one surprises people, and the project's own troubleshooting calls it out: **AdGuard, Pi-hole and firewall/DNS filtering** break streaming. Symptoms are "unreachable address" errors and playback that dies seconds in.

- **Disable the filter temporarily** to confirm
- Then look at your **query log** while playing — the blocked domain is right there
- Whitelist the streaming provider's CDN domains rather than leaving filtering off
- Same applies to **pfSense/OPNsense** rules and SSL-inspecting proxies

Also check the **stream URL host**: MA serves audio to players from its own address. If that address isn't reachable by the speaker (wrong interface in a multi-NIC host, Docker bridge IP, changed hostname), the player connects, fails and stops. Settings → System → Streams has the advanced options for pinning this.

## 3. Unavailable after idle, or after a power cycle

- Some players (ESP32-based squeezelite builds among them) go unresponsive after idle and need a reboot. That's device firmware, not MA — update the device's firmware
- Give players a **DHCP reservation**. An address change mid-session loses the player and often requires a restart of both ends
- Reported for voice-assistant hardware: after a power cycle the MA media player entity stays unavailable in HA until the integration is reloaded. **Reload the Music Assistant integration** in HA rather than restarting everything

## 4. Duplicate providers fighting over one device

If you have **two providers pointing at the same speaker** — e.g. the native Chromecast provider *and* Home Assistant media players, or Sonos plus HA — they fight, and the player flaps.

The project's advice: use the **native** provider for that device and remove the duplicate. For Chromecast devices, keep the Chromecast provider and remove the HA media player route.

Check **Settings → Providers** for two entries covering the same hardware.

## 5. Order of operations

1. **Power-cycle the player** (the docs' own first suggestion — it fixes a surprising number)
2. Reload the MA **integration** in Home Assistant
3. Restart the **Music Assistant server**
4. Disable **DNS filtering** as a test
5. Check for **duplicate providers**
6. Confirm **multicast** reaches the player's network
7. Read the MA server log while reproducing — it names the failing host or codec

## Prevention

- **Host networking** for the MA container
- **DHCP reservations** for every speaker
- Whitelist streaming domains in your DNS filter deliberately, with a comment, so the next person understands why
- One provider per device
- Keep player firmware updated — cheap ESP32 audio devices are the least reliable part of the chain

## FAQ

**Why does Pi-hole break music playback?**
Streaming providers use CDN domains that overlap with tracker blocklists. The client can't resolve them and the stream dies.

**Should I add players manually or let them be discovered?**
Discovery is better when multicast works. Manual is a valid workaround and a useful diagnostic.

**Why do my players disappear after a router reboot?**
New DHCP leases. Reserve their addresses.

**Chromecast provider or Home Assistant media players?**
The native one for that device. Don't run both.
