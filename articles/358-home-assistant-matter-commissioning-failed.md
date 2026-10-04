---
title: "Home Assistant: Matter Device Commissioning Failed"
slug: home-assistant-matter-commissioning-failed
meta_description: "Commissioning stops at network connectivity, node discovery fails, or attestation is refused. IPv6 and mDNS are the real requirements."
updated: October 2026
cluster: round 14 (tech) — home-assistant core and addons GitHub
competition: LOW
---

# Home Assistant: Matter Device Commissioning Failed

Matter's requirements are specific and unusual for a home network:

> **Local IPv6 must work, and multicast (mDNS) must flow freely between the phone, Home Assistant, the Matter Server and the device.**

Almost every commissioning failure is one of those two. The error messages — "checking network connectivity", "could not discover node with discriminator", "device is not trustworthy" — are symptoms.

## 1. IPv6 must be enabled, everywhere in the path

Matter uses IPv6 link-local and ULA addressing. It is not optional and there is no IPv4-only mode.

```bash
# on the Home Assistant host
ip -6 addr show
# you want more than just ::1 on lo
```

Specific blockers:

- **IPv6 disabled on the router or the HA host.** Re-enable it. You do not need public IPv6 connectivity — link-local is enough — but the stack must be up.
- **Docker without IPv6.** A Matter Server container on a bridge network with no IPv6 cannot reach devices. Run it with `network_mode: host`:

```yaml
  matter-server:
    image: ghcr.io/home-assistant-libs/python-matter-server:stable
    network_mode: host
    volumes:
      - ./matter-data:/data
    security_opt:
      - apparmor=unconfined
    cap_add:
      - NET_ADMIN
      - NET_RAW
```

- **Thread border router in Docker needs IP forwarding:**

```bash
sudo sysctl -w net.ipv6.conf.all.forwarding=1
echo 'net.ipv6.conf.all.forwarding=1' | sudo tee /etc/sysctl.d/99-thread.conf
```

The second line matters — without it the setting reverts on reboot and commissioning that worked yesterday fails today.

## 2. Multicast must flow

- **VLANs.** Phone on one VLAN, device on another, HA on a third: mDNS doesn't cross without a reflector (`avahi-daemon` with reflector mode, or your firewall's mDNS repeater). For a first attempt, put everything on one VLAN.
- **IGMP snooping** misbehaving on a managed switch silently drops multicast. Turning it off is a valid test.
- **Multicast filtering / "AP isolation"** on the Wi-Fi. Disable for the SSID.
- **Enterprise mesh systems** that proxy mDNS selectively often don't carry what Matter needs.

This is why Matter commissioning so often works on a flat consumer network and fails on a carefully segmented one.

## 3. The Android-specific permission

A real and easily-missed cause: on Android, commissioning hands off to Google's Matter UI, which puts the Home Assistant Companion app in the background. Android then restricts background apps from reading the Wi-Fi SSID, so the app cannot tell the device which network to join — and you get stuck at **"Checking network connectivity"**.

Fix: set the Companion app's **Location permission to "Allow all the time"**, not "while using the app". Then retry.

On iOS, the equivalent stumbling block is a **"Thread border router required"** message for a Thread device when no border router is available or its credentials haven't been shared with the phone.

## 4. Device-side causes

- **Already commissioned into another fabric.** A Matter device holds a limited number of fabrics and must be either factory reset or have a new pairing code generated from the app that owns it. "Multi-admin" sharing produces a fresh code — use that rather than resetting, if you want to keep the other ecosystem.
- **The QR code / 11-digit code is for a different device.** They are not interchangeable.
- **Attestation failure** ("device is not trustworthy") means the device's certificate isn't in the trusted set. For development or uncertified hardware, Matter Server has an option to allow it; for a retail device it usually means a counterfeit or a firmware problem.

## 5. Reading the actual error

```bash
docker logs matter-server --tail 100
# or, as an add-on: Settings → Add-ons → Matter Server → Log
```

Useful lines mention the discriminator, the commissioning stage, and `CHIP` error codes. `Device discovery failed` with no further detail is the mDNS case; a timeout during *interview* after discovery succeeded is usually Thread or Wi-Fi handover.

## What not to do

- **Don't disable IPv6 to simplify your network.** Matter stops working entirely.
- **Don't commission across VLANs on your first attempt.** Prove it works flat, then segment deliberately.
- **Don't factory reset a device that's working in another ecosystem.** Use multi-admin sharing.
- **Don't run Matter Server on a bridge network.** Host networking, every time.

## Prevention

| Habit | Why |
|---|---|
| IPv6 enabled and `forwarding` persisted | The two settings that break silently |
| One flat network for commissioning, segment after | Removes the mDNS class during setup |
| Companion app location permission "always" | The Android blocker |
| Note which fabrics each device is in | Avoids unnecessary factory resets |

## FAQ

**Does Matter need internet?**
No, once commissioned. Commissioning via a phone app may require it for certificate checks.

**Thread or Wi-Fi Matter devices — which is easier?**
Wi-Fi, because there's no border router in the path. Thread needs a working border router whose credentials your phone holds.

**Device commissioned but entities missing.**
The interview must complete. Check the Matter Server log for the node's cluster enumeration.

**Can I move a device between HA instances?**
Only by removing it from the old fabric or using multi-admin; there's no export.
