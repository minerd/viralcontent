---
title: "ZeroTier: Managed Routes Not Working"
slug: zerotier-managed-routes-not-working
meta_description: "Routes are defined in the controller and never reach the kernel. The two client toggles, the VIA direction, and the route-preference rule."
updated: October 2026
cluster: round 14 (tech) — ZeroTierOne GitHub issues and ZeroTier discussions
competition: LOW
---

# ZeroTier: Managed Routes Not Working

A route defined in the ZeroTier controller is only a *suggestion*. Each member decides whether to install it, and by default it won't install some kinds at all.

Check what the member actually accepted:

```bash
sudo zerotier-cli listnetworks
ip route show | grep -E 'zt|<your subnet>'
```

If `listnetworks` shows the network OK and the route isn't in `ip route`, the member declined it.

## 1. The three per-member toggles

On each member (desktop app, or CLI):

```bash
sudo zerotier-cli set <networkid> allowManaged=1
sudo zerotier-cli set <networkid> allowGlobal=1
sudo zerotier-cli set <networkid> allowDefault=1
```

| Flag | Controls |
|---|---|
| `allowManaged` | Whether managed IPs **and routes** are installed at all |
| `allowGlobal` | Whether routes to **public** IP space are accepted |
| `allowDefault` | Whether a `0.0.0.0/0` default route is accepted |

Defaults vary by platform and version. The two that catch people:

- **`allowManaged=0`** means the interface gets no ZeroTier IP either, so you'd usually notice — but on some clients the IP is assigned and routes still aren't.
- **`allowGlobal=0`** is why a route to a *public* prefix (or to a private range the client considers unusual) is silently ignored while routes to your ZeroTier subnet work fine.

On macOS, managed routes failing to reach the kernel has been a recurring, version-specific problem even with the flags set. If `allowManaged=1` and the route is still absent on macOS, check the ZeroTier version against the issue tracker before rewriting your controller config; a manual route is a valid stopgap:

```bash
sudo route -n add -net 192.168.10.0/24 10.144.223.179
```

## 2. The VIA direction

In the controller's route table, the order is **target VIA gateway**:

```
192.168.10.0/24   via   10.144.223.179
```

- **Target** = the physical LAN you want to reach
- **Gateway** = the **ZeroTier address** of the member that sits on that LAN

Reversing them is a documented root cause of total routing failure, and the UI does not stop you. Double-check that the gateway is a 10.x/172.x ZeroTier-assigned address of a member, and that the target is the remote LAN.

A route with an **empty** gateway means "this subnet is on the ZeroTier network itself" — correct for your ZeroTier subnet, wrong for a LAN behind a member.

## 3. Prefix length and route preference

Routing picks the most specific match. Two consequences people hit:

- A `/23` or `/16` managed route **loses** to the member's own local `/24` for the same space. If the remote LAN is `192.168.10.0/24` and you publish `192.168.10.0/23`, a machine with a local `192.168.10.0/24` keeps using its own interface. Publish the exact prefix.
- Conversely, publishing a `/24` that **overlaps the member's own LAN** breaks that member's local networking. ZeroTier LAN-to-LAN routing requires **non-overlapping subnets at each site**. Two sites both on `192.168.1.0/24` cannot be bridged this way; renumber one.

## 4. The gateway member must actually route

Defining the route doesn't make the member forward packets.

On the gateway member:

```bash
sudo sysctl -w net.ipv4.ip_forward=1
echo 'net.ipv4.ip_forward=1' | sudo tee /etc/sysctl.d/99-zt.conf

# NAT, if the LAN doesn't have a route back to the ZeroTier subnet
sudo iptables -t nat -A POSTROUTING -o eth0 -s 10.144.0.0/16 -j MASQUERADE
sudo iptables -A FORWARD -i ztxxxxxx -o eth0 -j ACCEPT
sudo iptables -A FORWARD -i eth0 -o ztxxxxxx -m state --state RELATED,ESTABLISHED -j ACCEPT
```

Without NAT, hosts on the LAN receive packets from `10.144.x.x` and have no route back — so you see the request arrive and no reply. The alternative to NAT is a static route on the LAN's router pointing the ZeroTier subnet at the gateway member, which is cleaner if you control that router.

## 5. "Managed routes shouldn't apply to this member"

A real limitation: there is no per-member exclusion for a specific managed route, so the gateway member itself receives a route to the LAN it is already on. In practice the more specific local route wins, but on some platforms it causes odd behaviour. The workaround is `allowManaged=0` on that one member plus manual IP configuration — which also means it stops getting its ZeroTier IP automatically, so assign it statically.

## What not to do

- **Don't publish overlapping subnets.** Renumber one site; nothing else fixes it.
- **Don't reverse target and gateway.** Read the route as "to X, via Y".
- **Don't enable `allowDefault=1` casually.** All of that member's traffic then exits via ZeroTier.
- **Don't forget `ip_forward` persistence.** It works until reboot otherwise.

## Prevention

| Habit | Why |
|---|---|
| Distinct /24 per site, planned in advance | Overlap is the one unfixable problem |
| `allowManaged=1`, `allowGlobal=1` on every member, documented | Removes the silent-decline class |
| Static route on the LAN router instead of NAT | Preserves source addresses and makes logs readable |
| Verify with `ip route`, not the controller UI | The controller shows intent; the kernel shows reality |

## FAQ

**ZeroTier or Tailscale for site-to-site?**
Both work. ZeroTier's managed routes are controller-driven; Tailscale advertises routes from the node and requires approval. The overlap rule applies to both.

**Can I bridge rather than route?**
ZeroTier supports L2 bridging, which avoids renumbering but brings broadcast traffic across the WAN. Routing is usually the better choice.

**Members connect but relay instead of going direct?**
Separate issue: UDP 9993 and NAT behaviour. `zerotier-cli peers` shows DIRECT or RELAY per peer.

**Routes work one direction only.**
Almost always the return path: NAT or a missing static route at the far end.
