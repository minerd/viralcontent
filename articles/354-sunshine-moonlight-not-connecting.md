---
title: "Sunshine and Moonlight: Host Not Found or Black Screen"
slug: sunshine-moonlight-not-connecting
meta_description: "Moonlight can't see the PC, pairing fails, or the stream connects to a black screen. Ports, mDNS, and the headless-display problem."
updated: October 2026
cluster: round 14 (tech) — LizardByte discussions and moonlight-docs
competition: LOW
---

# Sunshine and Moonlight: Host Not Found or Black Screen

Three distinct failures. The symptom tells you which:

- **Host never appears / "Host not found"** → discovery or ports (section 1)
- **Host appears, pairing fails** → the PIN flow (section 2)
- **Stream starts, screen is black** → no active display on the host (section 3)

## 1. Host not found

Moonlight finds hosts by **mDNS on the local network**. That breaks in predictable ways:

- **Different subnet or VLAN.** mDNS doesn't cross subnets without a reflector. Add the host manually by IP instead — this works regardless and is worth doing first as a test.
- **Client isolation** on the Wi-Fi AP. Disable it for the relevant SSID.
- **Sunshine not running, or bound to the wrong interface.** Check the web UI at `https://localhost:47990`.
- **A VPN on either device.** If the phone is on a VPN and the host isn't, they are effectively on different networks.

The ports Sunshine needs (defaults):

| Port | Protocol | Use |
|---|---|---|
| 47984 | TCP | HTTPS |
| 47989 | TCP | HTTP |
| 47990 | TCP | Web UI |
| 48010 | TCP | RTSP |
| 47998–48000 | UDP | Video/audio/control |
| 48002 | UDP | — |

Those UDP ports are the ones people miss, and without them the host pairs and then the stream never starts.

```bash
# on the host
sudo ss -tulnp | grep -E '4798[0-9]|4799[0-9]|480(0[0-9]|10)'
```

On Windows, Sunshine's installer adds firewall rules; a third-party firewall will need them added by hand.

## 2. Pairing fails

Moonlight shows a PIN; you enter it in Sunshine's web UI under **PIN**. Failures:

- **Entering the PIN in the wrong place.** It goes into Sunshine's web UI, not into Moonlight.
- **The web UI isn't reachable** from the machine you're typing on. It's bound to localhost by default in some builds; use the host's own browser, or enable external access in Sunshine's config.
- **Clock skew.** The certificate exchange is time-sensitive.
- **Stale pairing from a previous install.** Remove the host in Moonlight and unpair all clients in Sunshine, then pair fresh.

## 3. Black screen after connecting

This is the common one on a headless or VM host, and the cause is simple: **Sunshine captures a display that must exist and be active.**

- **No monitor attached.** With no display, there is nothing to capture. Use an HDMI dummy plug (the cheap, reliable answer), or a virtual display driver.
- **The host is at a locked screen or logged out.** On Windows, the session must be active; Sunshine running as a service can capture the login screen only with the right privileges.
- **Wrong output selected.** Sunshine's config has an `output_name` / adapter setting. On a multi-GPU laptop, capturing the wrong adapter gives a black frame. Sunshine's web UI lists the available outputs — pick explicitly rather than leaving it automatic.
- **Linux: Wayland vs X11.** Capture support differs by compositor and by Sunshine version. If a Wayland session gives a black screen, test an X11 session to confirm which side the problem is on. KMS capture needs the right capability:

```bash
sudo setcap cap_sys_admin+p $(readlink -f $(which sunshine))
```

- **HDR enabled.** HDR capture has produced black or washed-out output in several combinations. Turn HDR off on the host as a test.

## 4. Stream starts then stutters or drops

- **Bitrate too high for the link.** Start at 10–20 Mbps on Wi-Fi, not the 150 Mbps maximum.
- **5 GHz only.** A 2.4 GHz connection will not carry a usable stream.
- **Software encoding.** Check Sunshine's log for the encoder in use; if it fell back to software, the GPU encoder isn't available (driver, or a VM without passthrough) and performance will be poor.

```bash
grep -iE 'encoder|nvenc|vaapi|quicksync' ~/.config/sunshine/sunshine.log | tail
```

## What not to do

- **Don't forward ports to the internet** to play remotely. Use a mesh VPN (Tailscale, Nebula) — exposing these ports publicly exposes an input-injection surface.
- **Don't debug discovery before testing a manual IP.** It splits the problem in thirty seconds.
- **Don't expect a headless host to stream without a dummy plug or virtual display.** This is not configurable away.
- **Don't run Sunshine and another streaming host simultaneously.** They fight over the encoder and the ports.

## Prevention

| Habit | Why |
|---|---|
| HDMI dummy plug on any headless host | Eliminates the black-screen class permanently |
| Static IP for the host, added manually in Moonlight | Immune to mDNS problems |
| Explicit output/adapter in Sunshine's config | Prevents wrong-GPU capture |
| Mesh VPN for remote play | Secure, and usually lower latency than a port forward |

## FAQ

**Does it work over the internet?**
Yes, over a VPN or with careful port forwarding. Latency and jitter matter far more than bandwidth.

**Controller not detected?**
Moonlight maps it; on the host, Sunshine creates a virtual gamepad. On Linux that needs `uinput` permissions.

**Audio missing?**
Sunshine captures a specific sink. On Linux, it creates a virtual sink; if another application grabbed the default, select the sink explicitly.

**Multiple clients at once?**
One session at a time per host by default.
