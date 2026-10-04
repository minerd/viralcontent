---
title: "qBittorrent Behind Gluetun Loses Connectivity? Port Forwarding and the libtorrent Trap"
slug: qbittorrent-gluetun-no-internet
meta_description: "Torrents stall after Gluetun reconnects, or lose internet after an update. The libtorrent v2 image, the forwarded-port handoff, the ARM Docker bug and server lists."
updated: October 2026
cluster: round 12 (tech) — Gluetun GitHub discussions and homelab forums
competition: LOW
---

# qBittorrent Behind Gluetun Loses Connectivity? Port Forwarding and the libtorrent Trap

Two separate problems, often conflated:

- **No connectivity at all** after an update → Gluetun's VPN connection or Docker networking
- **Torrents stall after working fine for hours** → qBittorrent didn't follow Gluetun's reconnect, or the forwarded port changed

## 1. The reconnect problem (the big one)

Documented behaviour: when Gluetun's health check restarts the VPN, **qBittorrent doesn't switch to the new connection**. Everything looks up, nothing moves.

The reported workaround: use the **libtorrent v1** image rather than the v2 line:

```yaml
qbittorrent:
  image: lscr.io/linuxserver/qbittorrent:libtorrentv1
  network_mode: "service:gluetun"
```

Or use a different client (Transmission is the usual suggestion) if you'd rather not pin an older library.

Alternative mitigations:
- Add a **healthcheck/auto-restart** on the qBittorrent container so a Gluetun reconnect takes it with it
- Reduce how often Gluetun restarts the tunnel (health check tuning) so the problem is rarer rather than solved

## 2. The forwarded port changed

With providers that support port forwarding, Gluetun gets a port and qBittorrent must **use that exact port** for incoming connections. It changes on reconnect.

Symptoms: downloads crawl, "Not connectable", peers only outbound.

Fixes:
- Enable Gluetun's **port-forwarding output file** and a script/container that pushes the new port into qBittorrent's API on change (several small projects do exactly this)
- Check the **actual current port** rather than assuming: read Gluetun's log or `/tmp/gluetun/forwarded_port`, then compare with qBittorrent's listening port
- Don't rely on a port you hardcoded six months ago

A stalled torrent with a "lying" port is the classic homelab afternoon.

## 3. No connectivity at all after an update

Work the layers from the outside in:

```bash
docker compose logs --tail=100 gluetun          # did the tunnel come up?
docker exec gluetun wget -qO- https://ipinfo.io/ip    # VPN IP?
docker exec qbittorrent wget -qO- https://ipinfo.io/ip  # same IP?
```

- **Gluetun itself failing to connect**: provider server lists ship *with each Gluetun release*, and the server you were using may no longer exist in the new list. Set `UPDATER_PERIOD` and `UPDATER_VPN_SERVICE_PROVIDERS` so the list refreshes itself, or pin a Gluetun version that worked
- **Reported ARM issue**: Docker v28.0.0+ appears to break Gluetun's network security setup on ARM builds while x86_64 is fine. If you're on a Pi or an ARM NAS and it died after a Docker upgrade, that's a strong candidate — pin Docker or Gluetun accordingly
- **`network_mode: "service:gluetun"`** containers lose networking entirely when Gluetun restarts and the dependency ordering is wrong. Use `depends_on` with a healthcheck condition

## 4. The WebUI is unreachable

With `network_mode: service:gluetun`, qBittorrent has **no ports of its own** — publish them on **Gluetun**:

```yaml
gluetun:
  ports:
    - 8080:8080      # qbittorrent webui
    - 6881:6881
    - 6881:6881/udp
```

A common post-update break: someone adds `ports:` to the qBittorrent service, Docker refuses or ignores it, and the UI disappears.

Also check **FIREWALL_OUTBOUND_SUBNETS** on Gluetun so your LAN can reach the UI:

```yaml
  environment:
    - FIREWALL_OUTBOUND_SUBNETS=192.168.1.0/24
```

## 5. DNS inside the tunnel

Gluetun runs its own DNS over TLS by default. If your trackers won't resolve:
- Check `DOT=on/off` and `DNS_ADDRESS`
- A Pi-hole/AdGuard upstream unreachable from inside the tunnel
- Tracker domains blocked by your filter lists

## Prevention

1. **Pin both image tags** — Gluetun and qBittorrent
2. Automate the **forwarded port** handoff; don't hardcode
3. Publish ports on **Gluetun**, set `FIREWALL_OUTBOUND_SUBNETS`
4. Keep the server-list **updater** enabled
5. Add a **healthcheck-based restart** for the client so reconnects don't leave it orphaned

## FAQ

**Why does everything look up but nothing downloads?**
qBittorrent is still bound to the pre-reconnect tunnel, or the forwarded port changed.

**Is libtorrent v1 really the fix?**
It's the widely reported workaround for the reconnect behaviour. v2 may be fine for you; test before committing.

**Where do I publish the WebUI port?**
On the Gluetun service, since the client shares its network namespace.

**It broke right after I updated Docker on a Pi.**
Check the ARM/Docker v28 issue — pin and test.
