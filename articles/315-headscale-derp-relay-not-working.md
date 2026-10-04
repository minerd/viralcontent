---
title: "Headscale: Nodes Only Connect via DERP (or Not at All)"
slug: headscale-derp-relay-not-working
meta_description: "Tailscale clients show 'relay' instead of direct, or can't reach the embedded DERP at all. STUN, port 3478 and the config fields that matter."
updated: October 2026
cluster: round 13 (tech) — Headscale GitHub issues
competition: LOW
---

# Headscale: Nodes Only Connect via DERP (or Not at All)

Two separate problems that get reported together:

- **`tailscale status` shows `relay "xyz"`** — connectivity works, but through a relay, so it's slow. NAT traversal is failing.
- **Nodes can't connect at all** — the DERP server itself is unreachable, or the control plane is misconfigured.

Start by finding out which:

```bash
tailscale status
tailscale netcheck
```

`netcheck` is the important one. It reports whether UDP works, your NAT mapping behaviour, and the latency to each DERP region.

## 1. Nodes can't connect at all

**Check the control plane first.** Nodes talk to Headscale over HTTPS:

```bash
curl -s https://headscale.example.com/health
```

If that fails, nothing else matters. Common causes:

- `server_url` in `config.yaml` doesn't match what clients use. It must be the **external** URL, including scheme, no trailing slash.
- A reverse proxy not forwarding the websocket/long-poll upgrade. Headscale needs it:

```nginx
location / {
    proxy_pass http://127.0.0.1:8080;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
    proxy_read_timeout 86400s;
    proxy_buffering off;
}
```

The long `proxy_read_timeout` and `proxy_buffering off` are both required. Without them nodes connect, then drop every 60 seconds and reconnect — which presents as flapping, not as a clean failure.

- **Cloudflare proxy.** The control connection is a long-lived poll. Cloudflare's free tier will cut it. Grey-cloud the record.

## 2. The embedded DERP

Headscale can run its own DERP. The config:

```yaml
derp:
  server:
    enabled: true
    region_id: 999
    region_code: "headscale"
    region_name: "Headscale Embedded DERP"
    stun_listen_addr: "0.0.0.0:3478"
    private_key_path: /var/lib/headscale/derp_server_private.key
    automatically_add_embedded_derp_region: true
  urls:
    - https://controlplane.tailscale.com/derpmap/default
  paths: []
  auto_update_enabled: true
  update_frequency: 24h
```

What goes wrong:

- **UDP/3478 not open or not forwarded.** This is the STUN port, and it is the single most common cause of relay-only connections. It is **UDP**, and many people forward only TCP ports when setting up Headscale. Without STUN, nodes cannot discover their external mappings and fall back to relaying every packet.

```bash
# from outside
nc -zuv your.public.ip 3478
```

- **DERP itself needs the HTTPS port.** The embedded DERP is served by the same listener as the control plane, so it inherits the reverse proxy's behaviour, including the websocket requirement above.
- **Leaving `urls:` populated** keeps Tailscale's public DERP map, which is usually what you want as a fallback. Removing it means your single DERP is a single point of failure. Removing it *and* having a broken embedded DERP means total failure.

## 3. Relay-only: fixing NAT traversal

`tailscale netcheck` output to read carefully:

```
UDP: true
IPv4: yes, 203.0.113.5:41641
MappingVariesByDestIP: false
PortMapping: UPnP, NAT-PMP
```

- **`UDP: false`** — UDP is blocked outbound. Nothing will go direct. Check for an outbound firewall rule or a captive network.
- **`MappingVariesByDestIP: true`** — hard NAT (symmetric). Direct connections between two such endpoints are not possible; one end must be easier. This is common on carrier-grade NAT mobile networks.
- **`PortMapping: ` empty** — no UPnP/NAT-PMP/PCP. Enabling one on the router helps a lot, and is the easiest single win.
- **Both nodes behind the same NAT but still relaying** — the LAN discovery path is blocked. Check for client isolation on the Wi-Fi, and that UDP/41641 is permitted within the LAN.

Also: a node with `--accept-routes` through an exit node routes its DERP traffic over the tunnel, which can make everything relay. Check `tailscale status` for an exit node in use.

## 4. Verifying it improved

```bash
tailscale ping other-node
```

```
pong from other-node (100.64.0.3) via 203.0.113.9:41641 in 14ms
```

`via <public ip>:<port>` is direct. `via DERP(headscale)` is relayed. `tailscale ping` is the right test because it reports the path, which `ping` does not.

Note that connections **start** relayed and upgrade to direct after a few seconds. A single ping immediately after connecting showing DERP is normal.

## What not to do

- **Don't remove the public DERP URLs** until your own DERP is proven. You'll have no fallback.
- **Don't forward only TCP.** UDP/3478 and UDP/41641 matter more than anything TCP here.
- **Don't put the control plane behind Cloudflare's proxy** and then debug for hours. It's a known-bad combination for long-poll connections.
- **Don't run DERP on a 1 vCPU VPS and expect throughput.** Relayed traffic is all decrypted-and-re-encrypted by the client, but the relay still moves every byte; a small VPS's network is the ceiling.

## Prevention

| Habit | Why |
|---|---|
| Keep both your DERP and the public map | Fallback costs nothing |
| Open UDP 3478 and 41641 at setup time | Prevents the relay-only default |
| Enable UPnP or NAT-PMP on home routers | Biggest single improvement to direct-connection rate |
| Check `tailscale netcheck` before changing server config | Most relay problems are client-network, not server |

## FAQ

**Do I need my own DERP at all?**
No. Tailscale's public DERPs work with Headscale and are geographically distributed. Run your own for privacy or where the public ones are blocked.

**Is relayed traffic readable by the relay?**
No — WireGuard encryption is end-to-end; the relay forwards opaque packets. It's a performance issue, not a confidentiality one.

**Nodes connect but can't reach subnet routes.**
Different problem: the route must be advertised (`--advertise-routes`) *and* approved in Headscale (`headscale nodes route enable`).

**ACLs work in Tailscale but not Headscale.**
Policy file syntax and feature support differ by Headscale version. Check the version's own documentation rather than Tailscale's.
