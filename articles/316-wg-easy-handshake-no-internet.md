---
title: "wg-easy: Handshake Succeeds But No Internet"
slug: wg-easy-handshake-no-internet
meta_description: "WireGuard connects, the handshake is recent, but nothing routes. IP forwarding, the NAT rule, AllowedIPs and the DNS trap."
updated: October 2026
cluster: round 13 (tech) — wg-easy GitHub issues
competition: LOW
---

# wg-easy: Handshake Succeeds But No Internet

A recent handshake means the tunnel is up. Everything after that is routing, and there are exactly four places it breaks. Work them in order; the first two account for most cases.

Confirm the tunnel state first:

```bash
docker exec wg-easy wg show
```

```
peer: abc...
  latest handshake: 32 seconds ago
  transfer: 1.2 KiB received, 8.4 KiB sent
```

Received bytes with almost nothing sent back = packets arrive and die on the server. That's this article.

## 1. IP forwarding on the host

The container can't route if the kernel won't forward.

```bash
sysctl net.ipv4.ip_forward
```

Must be `1`. Set it persistently:

```bash
echo 'net.ipv4.ip_forward=1' | sudo tee /etc/sysctl.d/99-wg.conf
sudo sysctl --system
```

In Docker this is needed on the **host**, not inside the container, even though the container has `NET_ADMIN`. And the container needs:

```yaml
    cap_add:
      - NET_ADMIN
      - SYS_MODULE
    sysctls:
      - net.ipv4.ip_forward=1
      - net.ipv4.conf.all.src_valid_mark=1
```

`src_valid_mark=1` is the one people omit. Without it, WireGuard's reverse-path filtering drops the return traffic — handshake fine, no data. If you change exactly one thing after reading this, make it this line.

## 2. The NAT rule

Traffic needs masquerading on the way out. wg-easy generates this from its config, and the variable that controls it is the one most often wrong:

```yaml
environment:
  - WG_HOST=vpn.example.com
  - WG_DEFAULT_ADDRESS=10.8.0.x
  - WG_DEFAULT_DNS=1.1.1.1
  - WG_ALLOWED_IPS=0.0.0.0/0,::/0
  - WG_POST_UP=iptables -t nat -A POSTROUTING -s 10.8.0.0/24 -o eth0 -j MASQUERADE; iptables -A FORWARD -i wg0 -j ACCEPT; iptables -A FORWARD -o wg0 -j ACCEPT
  - WG_POST_DOWN=iptables -t nat -D POSTROUTING -s 10.8.0.0/24 -o eth0 -j MASQUERADE; iptables -D FORWARD -i wg0 -j ACCEPT; iptables -D FORWARD -o wg0 -j ACCEPT
```

Two details:

- **`-o eth0` must be the real outbound interface.** On many hosts it's `ens3`, `enp0s3` or `eth0`. Check with `ip route get 1.1.1.1`. A masquerade rule on a nonexistent interface silently does nothing.
- **The subnet in the rule must match `WG_DEFAULT_ADDRESS`.** If you changed the address pool and not the POST_UP, NAT applies to a subnet nobody is on.

Verify the rule landed:

```bash
docker exec wg-easy iptables -t nat -L POSTROUTING -n -v
```

## 3. AllowedIPs on the client

`WG_ALLOWED_IPS` decides what the client sends through the tunnel.

- **`0.0.0.0/0,::/0`** — full tunnel. Everything goes over the VPN.
- **`10.8.0.0/24,192.168.1.0/24`** — split tunnel. Only the VPN subnet and your LAN. General internet does **not** go through, which is correct behaviour and frequently mistaken for a fault.

If you want a full tunnel and see no internet, check that the client config actually contains `0.0.0.0/0`. Changing this env var only affects **newly created** clients — existing configs keep the old value. Re-download the config, or edit AllowedIPs in the client app.

The IPv6 part matters more than it looks: a client with IPv6 connectivity and `AllowedIPs` lacking `::/0` will try IPv6 outside the tunnel. If your server has no working IPv6, those attempts time out and sites appear broken while ping works. Either include `::/0` or disable IPv6 on the client.

## 4. DNS

With a full tunnel and no working DNS, nothing resolves and it looks like "no internet". Test precisely:

```bash
# on the client, while connected
ping -c2 1.1.1.1        # routing
nslookup example.com    # DNS
```

Routing fine, DNS failing means `WG_DEFAULT_DNS`:

- Pointing at a resolver only reachable on the server's LAN (a Pi-hole at 192.168.1.5) requires that the client's AllowedIPs include that subnet. Full tunnel covers it; split tunnel might not.
- Pointing at the Docker-internal address of another container won't work from a client.
- Pointing at `127.0.0.1` never works.

If you run Pi-hole/AdGuard on the same host, use the host's LAN IP, and make sure that resolver accepts queries from `10.8.0.0/24` — most block non-local subnets by default, which is a one-line allowlist change on the resolver side.

## What not to do

- **Don't recreate clients repeatedly.** The handshake works; the client config is rarely the issue beyond AllowedIPs.
- **Don't open `WG_PORT` on TCP.** WireGuard is UDP only; a TCP forward does nothing and a missing UDP forward means no handshake at all (a different symptom from this one).
- **Don't run wg-easy in `network_mode: host` alongside a POST_UP that assumes bridge networking.** The interface names and rules differ.
- **Don't skip `src_valid_mark`.** It is the most common single cause of exactly this symptom.

## Prevention

| Habit | Why |
|---|---|
| Keep POST_UP's subnet and interface in sync with the rest of the config | They're three settings that must agree |
| Note whether you intend full or split tunnel | Half of these reports are expected behaviour |
| Test with an IP ping before testing DNS | Separates routing from resolution immediately |
| Set `ip_forward` persistently | Otherwise it works until the next reboot |

## FAQ

**Can clients reach each other?**
Only with `FORWARD` rules permitting it and client-to-client not blocked. By default wg-easy allows it.

**Handshake never happens at all.**
Different problem: UDP port not reachable. Check the port forward and that `WG_HOST` resolves to your public address.

**It works on mobile data but not on a hotel Wi-Fi.**
Some networks block UDP on non-standard ports. Try moving the server to UDP/443.

**Throughput is poor.**
Check MTU. Lowering the client MTU to 1380 fixes a surprising amount of slow-but-working VPN behaviour over PPPoE links.
