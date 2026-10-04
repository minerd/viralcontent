---
title: "Nebula: Hosts Reach the Lighthouse But Handshake Times Out"
slug: nebula-handshake-timed-out
meta_description: "Nodes ping the lighthouse and not each other. Symmetric NAT, two hosts behind one IP, punchy settings and the relay that fixes it."
updated: October 2026
cluster: round 14 (tech) — slackhq/nebula GitHub issues
competition: LOW
---

# Nebula: Hosts Reach the Lighthouse But Handshake Times Out

If both nodes talk to the lighthouse and not to each other, the lighthouse is doing its job — it is telling each node where the other is — and the **direct path between them** is failing. That narrows it to NAT traversal.

## 1. Confirm what the lighthouse knows

Nebula exposes debug commands over its control socket:

```bash
# on a node
nebula -config config.yml -test
echo 'query-lighthouse' | nc -U /var/run/nebula.sock
echo 'list-lighthouse-addrmap' | nc -U /var/run/nebula.sock
echo 'list-pending-hostmap' | nc -U /var/run/nebula.sock
```

`list-lighthouse-addrmap` shows the candidate addresses the lighthouse has for each host. If a node's only candidate is a private address the other node can't reach, that's the problem — the node never reported a usable public address.

`list-pending-hostmap` shows handshakes in flight. Entries sitting there are being sent and not answered.

## 2. Two hosts behind the same public IP

A documented failure: when **two Nebula hosts sit behind the same public IP**, handshakes between them (and sometimes to them) fail. Both report the same external address and the NAT can't distinguish the sessions.

The fix is to make the lighthouse a **relay**:

```yaml
# lighthouse config
relay:
  am_relay: true
  use_relays: true

# every other node
relay:
  relays:
    - 10.10.0.1        # the lighthouse's Nebula IP
  am_relay: false
  use_relays: true
```

Relayed traffic goes through the lighthouse. It costs bandwidth and latency at that host, and it works where hole punching cannot. For two nodes on the same LAN, it is also worth letting them find each other locally — see section 4.

## 3. Symmetric NAT and punchy

Carrier-grade NAT and symmetric NAT allocate a different external port per destination, so the address the lighthouse learned is not the address the peer must send to.

```yaml
punchy:
  punch: true
  respond: true
  delay: 1s
  respond_delay: 5s
```

`respond: true` on **both** sides is the setting that matters most; without it, only one end attempts the punch and symmetric NAT defeats it. The documented success pattern for a cloud-to-CGNAT pair is:

- The cloud/VPS side runs Nebula on a **fixed port** with that port open inbound
- `punchy.respond: true` on both ends

```yaml
listen:
  host: 0.0.0.0
  port: 4242        # fixed, not 0, on any host with a public IP
```

A node with `port: 0` picks a random port each start, which breaks any inbound firewall rule you wrote.

## 4. Lighthouse configuration mistakes

**The lighthouse must have a static, reachable address and be listed as such:**

```yaml
# every node, including other lighthouses
static_host_map:
  "10.10.0.1": ["lighthouse.example.com:4242"]

lighthouse:
  am_lighthouse: false
  interval: 60
  hosts:
    - "10.10.0.1"
```

On the lighthouse itself:

```yaml
lighthouse:
  am_lighthouse: true
  hosts: []            # must be empty
```

A lighthouse that lists itself in `hosts` has, in some configurations, processed host queries **for its own address** and started a tunnel with itself, which never completes and burns the handshake timeout. Keep `hosts: []` on lighthouses.

**Local discovery** for nodes on the same LAN:

```yaml
lighthouse:
  local_allow_list:
    "192.168.1.0/24": true
```

Without advertising local addresses, two machines in the same office relay through a VPS on the other side of the world.

## 5. Firewall rules inside Nebula

Handshake success and traffic flow are different things. Nebula has its own firewall and it defaults to deny:

```yaml
firewall:
  outbound:
    - port: any
      proto: any
      host: any
  inbound:
    - port: any
      proto: icmp
      host: any
    - port: 22
      proto: tcp
      groups:
        - admin
```

If the handshake completes and `ping` fails, check `inbound` — ICMP needs an explicit rule, and its absence makes a working tunnel look broken.

## 6. The lighthouse isn't actually listening

A reported case: the log says it is listening and it isn't.

```bash
sudo ss -ulnp | grep 4242
```

Causes: the port is taken, the configured `listen.host` is an address the machine doesn't have, or the process lacks permission to bind. Check from outside too:

```bash
# from another host
nc -zu lighthouse.example.com 4242
```

## What not to do

- **Don't use `port: 0` on a host with a public IP.** You can't firewall a random port.
- **Don't list the lighthouse in its own `lighthouse.hosts`.**
- **Don't skip `punchy.respond: true`.** It's half the hole-punching handshake.
- **Don't expect ICMP to work without a firewall rule.** You'll misdiagnose a working tunnel.

## Prevention

| Habit | Why |
|---|---|
| Fixed port 4242 on anything with a public IP | Makes inbound rules possible |
| `use_relays: true` everywhere, relay on the lighthouse | Covers CGNAT and same-IP pairs |
| `local_allow_list` for your LANs | Same-site traffic stays local |
| ICMP allowed inbound | Makes `ping` a valid test |

## FAQ

**Does relaying read my traffic?**
No — Noise encryption is end-to-end. The relay forwards opaque packets.

**How many lighthouses?**
Two, on different providers, for availability. They don't need to know about each other.

**Certificates expired?**
Nebula certs have a lifetime; `nebula-cert print -path host.crt` shows it. An expired cert fails the handshake with a clear log line.

**Can I run a lighthouse behind NAT?**
Not usefully. It needs to be reachable by everyone.
