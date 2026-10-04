---
title: "Homebridge Child Bridge Shows 'No Response' in Home? Fix It Without Re-Pairing"
slug: homebridge-child-bridge-no-response
meta_description: "Accessories work in Homebridge but HomeKit says No Response. The mDNS advertiser setting, the persist folder, and how to recover a child bridge in the right order."
updated: October 2026
cluster: round 12 (tech) — Homebridge GitHub issues only
competition: LOW
---

# Homebridge Child Bridge Shows 'No Response' in Home? Fix It Without Re-Pairing

The accessory updates fine in the Homebridge UI, the plugin log looks healthy, and the Home app still shows **No Response**. This is a HomeKit pairing/advertising problem, not a plugin problem.

Work down this list. Each step is cheaper than the one after it.

## 1. Restart the child bridge, then Homebridge

In the Homebridge UI, open the plugin and use **Restart child bridge**. If that doesn't clear it, restart Homebridge itself. A plain restart genuinely fixes a large share of these — it re-publishes the Bonjour advertisement HomeKit lost track of.

## 2. Check the mDNS advertiser

This is the setting that causes it most often. **Homebridge UI → Settings → Advanced → mDNS Advertiser**, with the options `Bonjour HAP`, `Ciao` and `Avahi`.

Child bridges stopping communication after someone switched from **Bonjour HAP to Ciao** is a documented pattern. Switch it back, restart, and watch. If you're on Bonjour HAP already, try Ciao — the right answer depends on your host OS and network.

## 3. Rule out the network

HomeKit discovery is multicast, and it breaks in predictable places:

- Homebridge and your **Apple TV / HomePod hub** must be on the **same subnet/VLAN**
- **mDNS reflection** needed if they aren't (and multicast/IGMP snooping settings on managed switches)
- **Client isolation** off on the Wi-Fi the hub uses
- Homebridge host on a **static IP or DHCP reservation** — an address change orphans the pairing
- In Docker: **host networking**, not bridge. Bridge mode breaks HomeKit discovery

## 4. Remove and re-add the single accessory

If one accessory is stuck and the rest are fine: remove the accessory in the Home app, restart the child bridge, and add it again from the Homebridge UI's pairing card.

## 5. Clear persistence (the real reset)

Only when the above fails. In the Homebridge storage directory's **`persist/`** folder:

1. Note the child bridge's **username/MAC** from its plugin settings
2. Delete **`AccessoryInfo.<MAC>.json`**
3. Delete **`IdentifierCache.<MAC>.json`** — the one with the *same* MAC
4. Restart Homebridge
5. Pair the bridge again in Home with the fresh code

Deleting both files for one bridge leaves your other bridges untouched. Delete only the pair that matches.

A gentler route from the UI: **Homebridge Settings → Reset → Unpair Bridges / Accessories**, picking just the one child bridge.

## 6. Version and plugin issues

- If it started with a Homebridge update, check the GitHub issues for that version — releases have broken main-bridge pairing before
- Update the **plugin** too; "No Response" can be a plugin that stopped answering within HomeKit's timeout
- A plugin that's slow to respond (cloud API, rate limits) shows as No Response even when it eventually returns. That's a reason to put that plugin in its own child bridge, which is what child bridges are for

## Prevention

- **One child bridge per flaky plugin** — it stops one slow plugin taking the whole bridge down
- **Static IP** for the Homebridge host
- **Host networking** in Docker
- **Back up** the Homebridge config and `persist/` directory (the UI has a backup button) — restoring is faster than re-pairing 40 accessories
- Keep a note of which bridge owns which MAC

## FAQ

**Why does the UI show the accessory working while Home says No Response?**
The plugin is fine; HomeKit can't reach or recognise the bridge's advertisement. That's mDNS or pairing state.

**Do I lose my automations if I unpair a child bridge?**
Automations referencing those accessories break and need rebuilding — which is why persistence clearing is step five, not step one.

**Bonjour HAP or Ciao?**
Whichever works on your host. If one gives you No Response after an update, try the other.

**Is Docker bridge networking really a problem?**
Yes. HomeKit needs multicast on the LAN; use host networking.
