---
title: "Pangolin: Newt Site Shows Offline"
slug: pangolin-newt-site-offline
meta_description: "The Newt tunnel won't connect or drops the site offline. Outbound UDP 51820, the Docker network case, and reading the newt log."
updated: October 2026
cluster: round 13 (tech) — Pangolin GitHub issues and discussions
competition: LOW
---

# Pangolin: Newt Site Shows Offline

Newt is the client that dials out from your private network to the Pangolin VPS. "Site offline" means that outbound connection isn't established — and because it's outbound, you need no port forwarding, which narrows the causes considerably.

## 1. Read the newt log

```bash
# systemd
journalctl -u newt -n 50 --no-pager
# docker
docker compose logs newt --tail 50
```

The error text maps directly to a cause:

| Log line | Cause |
|---|---|
| `SendMessageInterval timed out after 10 attempts for message type: newt/wg/get-config` | Newt reached Pangolin's control plane but can't complete the WireGuard setup — usually UDP blocked |
| `failed to read ICMP packet: i/o timeout` | Tunnel up, data path failing |
| `Ping failed: use of closed network connection` | The tunnel was torn down; reconnect in progress |
| Auth/401 errors | Wrong site id or secret |
| DNS resolution failures | Newt can't resolve the Pangolin hostname |

A control-plane connection that works while the WireGuard handshake doesn't is the most common shape, and it's section 2.

## 2. Outbound UDP 51820

Newt establishes WireGuard to the VPS on UDP/51820 by default. Test it from the machine running Newt:

```bash
nc -zu <your-vps-ip> 51820
```

`nc -zu` on UDP is not conclusive on its own (UDP gives no handshake), so also check from the VPS side whether packets arrive:

```bash
# on the VPS
sudo tcpdump -ni any udp port 51820
```

If nothing appears while Newt is retrying, the packets aren't getting out. Causes:

- **Corporate or ISP firewall blocking outbound UDP** to non-standard ports. Some networks allow only 53/443 UDP.
- **A VPN already active on the Newt host**, routing the traffic elsewhere.
- **CGNAT with aggressive UDP timeouts** — the tunnel establishes and dies repeatedly. WireGuard's persistent keepalive mitigates this; Pangolin sets it, but a very short NAT timeout can still break it.
- **The VPS firewall not allowing 51820 inbound.** On a cloud provider, both the host firewall and the provider's security group must permit it:

```bash
sudo ufw allow 51820/udp
```

If outbound UDP is genuinely blocked on the Newt side, Pangolin supports relaying over other transports in recent versions — but the first step is establishing that this is the problem rather than guessing.

## 3. Newt in Docker

```yaml
services:
  newt:
    image: fosrl/newt
    restart: unless-stopped
    environment:
      - PANGOLIN_ENDPOINT=https://pangolin.example.com
      - NEWT_ID=your-site-id
      - NEWT_SECRET=your-site-secret
```

Two things specific to the container case:

- **Newt must be able to reach the resources it proxies.** If your services are on another Docker network, or on the host, Newt can't see them. The common solutions are `network_mode: host`, or attaching Newt to the same networks as the targets. A tunnel that connects but serves nothing is this.
- **Target addresses are from Newt's perspective.** In Pangolin's resource configuration, `localhost:3000` means *Newt's* localhost. With Newt in its own container, that's the container, not your service. Use the service name (if on a shared network) or the host's LAN IP.

Confirm from inside the container:

```bash
docker exec newt wget -qO- http://target-service:3000/ | head -5
```

## 4. Flapping / brief outages

A site that goes offline for a few minutes and returns is usually a reconnect, not a configuration problem. Newt detects a dead tunnel, backs off, and re-establishes.

What makes it worse:

- **A hung Newt process.** It can hang rather than exit, so the site stays offline until restarted. A healthcheck with `restart: unless-stopped` is the practical mitigation:

```yaml
    healthcheck:
      test: ["CMD-SHELL", "pgrep newt > /dev/null"]
      interval: 60s
```

A process check doesn't prove the tunnel works, so for anything you depend on, monitor the resource's external URL rather than the process.

- **The VPS rebooting or Pangolin restarting.** Newt reconnects, but during the window the site is offline.
- **Health-check state lag.** A known behaviour: when a Newt site goes offline, target health checks routed through it can keep reading "healthy" in the dashboard even though the site is correctly marked offline. So trust the site status over the target status.

## 5. Auth and identity

```bash
# verify the site credentials
journalctl -u newt -n 20 | grep -i 'auth\|unauthor\|401'
```

- `NEWT_ID` and `NEWT_SECRET` come from the site you created in Pangolin. Re-creating the site generates new ones; the old pair stops working.
- One credential pair per site. Running two Newt instances with the same id causes them to fight, and the site flaps.
- `PANGOLIN_ENDPOINT` must be the full URL with scheme, matching the certificate's name.

## What not to do

- **Don't forward ports for Newt.** It's outbound-only; inbound rules on your home router are unnecessary and a sign you've misread the architecture.
- **Don't run two Newt instances with one site id.** Create a second site.
- **Don't point a resource at `localhost`** when Newt is in its own container.
- **Don't expose Pangolin's own admin interface without its authentication configured.** It's the control plane for your whole tunnel.

## Prevention

| Habit | Why |
|---|---|
| `restart: unless-stopped` plus external monitoring of a resource URL | Covers both the hang and the real-outage cases |
| Newt on the same network as its targets, or host networking | Removes the reachability class |
| One site per Newt instance, credentials recorded | Prevents flapping from duplicate ids |
| UDP 51820 verified in both directions at setup | The single most common blocker |

## FAQ

**Can I run Newt on a different machine from the services?**
Yes, as long as Newt can reach them over the LAN. Target addresses are relative to Newt.

**Does it work behind CGNAT?**
Yes — that's a main use case, since the connection is outbound.

**Multiple sites to one Pangolin?**
Yes, each with its own Newt and credentials. That's how you reach several locations.

**Is the traffic end-to-end encrypted?**
The tunnel is WireGuard. TLS termination happens at the VPS by default, so the VPS sees plaintext HTTP unless you configure otherwise — worth knowing before putting sensitive services behind it.
