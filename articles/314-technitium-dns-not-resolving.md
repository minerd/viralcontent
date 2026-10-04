---
title: "Technitium DNS Not Resolving? Forwarders, DNSSEC and Port 53"
slug: technitium-dns-not-resolving
meta_description: "Queries time out, some domains fail, or the service won't start on port 53. The five causes, separated by which domains break."
updated: October 2026
cluster: round 13 (tech) — Technitium GitHub and forum
competition: LOW
---

# Technitium DNS Not Resolving? Forwarders, DNSSEC and Port 53

Which domains fail tells you what's wrong. Check that before changing any setting.

```bash
# from a client
dig @192.168.1.10 example.com
dig @192.168.1.10 yourinternalname.lan
```

- **Everything fails** → the service isn't reachable (section 1)
- **External works, internal fails** → zone or conditional forwarder (section 4)
- **Most work, a few fail** → DNSSEC or a specific upstream (section 3)
- **Works then stops after a while** → recursion/cache or rate limiting (section 5)

## 1. Nothing resolves: port 53 is taken

On Ubuntu and most modern systemd distributions, `systemd-resolved` holds 127.0.0.53:53 and, with some configurations, the wildcard. Technitium then fails to bind.

```bash
sudo ss -ulnp | grep ':53 '
```

If `systemd-resolved` appears:

```bash
sudo mkdir -p /etc/systemd/resolved.conf.d
printf '[Resolve]\nDNSStubListener=no\n' | sudo tee /etc/systemd/resolved.conf.d/disable-stub.conf
sudo systemctl restart systemd-resolved
```

Keep `systemd-resolved` running as a client; just stop its stub listener. Disabling the service entirely breaks name resolution on the host itself, which then breaks Technitium's own upstream queries — a self-inflicted loop people hit regularly.

In Docker, the equivalent problem is port mapping. You need both protocols:

```yaml
ports:
  - "53:53/udp"
  - "53:53/tcp"
  - "5380:5380/tcp"
```

**TCP/53 is not optional.** Responses over 512 bytes (common with DNSSEC and many modern records) fall back to TCP. Mapping only UDP gives the "most domains work, some time out" pattern.

## 2. Check Technitium's own view

The admin UI at `:5380` has a **DNS Client** tab. Query from there — it uses the server's own resolution path, so it separates "the server can't resolve" from "clients can't reach the server".

If the DNS Client works and clients fail, it's networking: firewall, the wrong interface bound (Settings → **DNS Server Local End Points**), or clients still pointed at the router.

## 3. A few domains fail: DNSSEC and upstreams

Technitium validates DNSSEC by default in recursive mode. Domains with genuinely broken DNSSEC will correctly fail — and the site may well load for everyone else because their resolver doesn't validate.

To confirm:

```bash
dig @192.168.1.10 problemdomain.example +dnssec
# SERVFAIL with ad flag absent → validation failure
dig @1.1.1.1 problemdomain.example
# works → that resolver isn't validating, or the domain is fine and yours isn't
```

The decision is yours: a validation failure is the resolver doing its job. Don't disable DNSSEC globally to fix one domain. If you must, add that domain to an exception rather than turning validation off.

For **forwarder mode**, the common failure is a forwarder that doesn't support what you asked for:

- Setting the forwarder protocol to **DNS-over-HTTPS** or **TLS** while the address is a plain IP with no DoH path gives total failure.
- A forwarder requiring SNI/hostname verification fails if you entered an IP.
- Setting **both** forwarders and recursion can produce inconsistent behaviour; pick one model.

## 4. Internal names fail

For `*.lan`, `*.home.arpa` or your own domain:

- **Authoritative zone**: create it under **Zones**, add A records. Technitium then answers from it directly.
- **Conditional forwarder**: for a domain served by another server (an AD domain controller, a router's DHCP-fed names), add a **Conditional Forwarder zone** pointing at that server. This is the piece people miss and then wonder why `dig` against the other server works and against Technitium doesn't.

Also relevant: **DHCP-registered names.** If you expect clients to appear automatically, Technitium's own DHCP server must be the one handing out leases, with DNS registration enabled. Leases from your router don't register in Technitium.

And check **Settings → Blocking**. A blocklist that includes a domain you need returns `0.0.0.0` or NXDOMAIN, which looks exactly like a resolution failure. The **Allowed** list overrides blocklists.

## 5. Works, then stops

- **Recursion allowed from the wrong networks.** If recursion is open to the internet, you'll be used as an amplifier and get rate-limited into uselessness. Set **Settings → Recursion → Allow only for private networks** (or an explicit ACL). This is also a security requirement, not just a performance one.
- **Upstream rate limiting.** Pointing every client at one public resolver through a single forwarder can hit per-IP limits. Add two or three forwarders.
- **Cache growth on a small host.** Check the memory limit if Technitium is in a 512 MB container; an OOM kill reads as an intermittent outage.
- **Blocklist update failure.** If a list URL dies, Technitium logs it. An empty list isn't a resolution failure, but a *partially* updated one can be.

## What not to do

- **Don't disable `systemd-resolved` entirely.** Disable only its stub listener.
- **Don't map UDP/53 without TCP/53.** It produces the most confusing symptom set of any single mistake here.
- **Don't leave recursion open to the internet.** You become an attack amplifier and your service degrades.
- **Don't turn off DNSSEC to fix one domain.** Use an exception.
- **Don't point Technitium's forwarder at itself.** The loop is detected, but the error is not obvious.

## Prevention

| Habit | Why |
|---|---|
| Two DNS servers in DHCP, on different hosts | A single resolver is a single point of failure for the whole network |
| Recursion ACL limited to your subnets | Security and stability in one setting |
| Keep a note of which zone type serves which domain | Internal-name failures become instantly diagnosable |
| Back up the config export after changes | Zones and blocklists are tedious to re-enter |

## FAQ

**Can it run alongside Pi-hole?**
On the same host only by moving one off port 53, which defeats the point. Pick one.

**Does it support DoH/DoT for clients?**
Yes, as a server — it can serve DoH and DoT, with a certificate. That's separate from the forwarder protocol setting.

**Queries are slow on first lookup, fast after.**
Normal recursive behaviour. If the first lookup is multiple seconds, check whether your upstream path has IPv6 problems — a failing AAAA path adds timeouts.

**How do I see what's being blocked?**
Dashboard → top blocked domains, and the query log (which must be enabled; it's off by default to save disk).
