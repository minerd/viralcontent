---
title: "Blocky Not Blocking Anything"
slug: blocky-not-blocking
meta_description: "Lists are configured and nothing is blocked. Client groups, the default group name, list download failures and confirming clients actually use it."
updated: October 2026
cluster: round 14 (tech) — 0xERR0R/blocky docs and GitHub
competition: LOW
---

# Blocky Not Blocking Anything

Three questions, in order. Most "not blocking" is answered by the first.

1. Are your clients actually resolving through Blocky?
2. Did the lists download?
3. Is the group that holds the lists applied to those clients?

## 1. Are clients using Blocky?

```bash
# from a client
dig @192.168.1.10 doubleclick.net +short
dig doubleclick.net +short
```

The first query goes to Blocky explicitly; the second uses whatever the client is configured with. If the first returns `0.0.0.0` and the second returns a real address, **Blocky works and your client isn't using it.**

Reasons a client bypasses it:

- **DHCP hands out the router's DNS**, not Blocky's. Change the DHCP DNS option, and note that existing leases keep the old value until renewal.
- **The browser uses DNS-over-HTTPS.** Chrome and Firefox bypass the system resolver entirely. Disable "Secure DNS" / "DNS over HTTPS" to test.
- **Hardcoded DNS in a device.** Smart TVs, Chromecasts and some IoT devices ignore DHCP and query 8.8.8.8 directly. Block outbound 53 at the firewall except from Blocky, and redirect it if you want to be thorough.
- **IPv6.** A client with an IPv6 address and a router advertising an IPv6 resolver will use that instead. Either advertise Blocky over IPv6 or disable RDNSS.

Blocky's query log is the authoritative record of what it was asked:

```yaml
queryLog:
  type: csv
  target: /logs
  logRetentionDays: 7
```

An empty query log while browsing is conclusive: nothing is reaching Blocky.

## 2. Did the lists download?

```bash
docker logs blocky --tail 100 | grep -iE 'download|list|refresh|error'
```

```yaml
blocking:
  denylists:
    ads:
      - https://raw.githubusercontent.com/StevenBlack/hosts/master/hosts
      - https://big.oisd.nl/
  clientGroupsBlock:
    default:
      - ads
  blockType: zeroIp
  blockTTL: 1m
  loading:
    refreshPeriod: 24h
    downloads:
      timeout: 60s
      attempts: 5
      cooldown: 10s
    strategy: blocking
```

Points that matter:

- **`loading.strategy: blocking`** makes Blocky wait for lists before serving. The default (`blocking` in recent versions, `fast` in older) determines whether Blocky answers queries *unfiltered* while lists are still downloading. With `fast`, a slow download means a window where nothing is blocked — and if the download fails, that window is permanent until the next refresh.
- **`downloads.timeout`** — the default is short for large lists on a slow link. 60s is safer.
- A **404 or 403** on a list URL leaves that list empty. Lists move and die; check them when something stops being blocked.

Confirm what's loaded:

```bash
curl -s http://192.168.1.10:4000/api/blocking/status | python3 -m json.tool
```

## 3. Client groups

This is the configuration most often wrong. Lists are grouped, and groups are mapped to clients:

```yaml
blocking:
  clientGroupsBlock:
    default:
      - ads
      - malware
    192.168.1.50:
      - ads
    laptop.lan:
      - ads
      - social
```

- **`default` applies to clients with no specific entry.** A configuration with only specific entries and no `default` leaves everything else unfiltered.
- **Client matching is by IP, CIDR, or hostname** from reverse DNS. If matching by name, Blocky must be able to resolve the client's name — and on many networks it can't, so the specific group never applies and `default` is used instead.
- A group name in `clientGroupsBlock` that doesn't exist under `denylists` silently blocks nothing.

Use IPs or CIDRs rather than hostnames unless your reverse DNS is solid:

```yaml
    192.168.1.0/24:
      - ads
```

## 4. Allowlists overriding

```yaml
blocking:
  allowlists:
    ads:
      - |
        example.com
        cdn.example.net
```

Allowlist entries win. An over-broad allowlist (a bare domain allowing all its subdomains) disables blocking for a large surface. Note that the allowlist is **per group** — keying it under `ads` applies it only where `ads` applies.

## 5. What DNS filtering cannot do

Worth being clear about, because it accounts for a share of "not blocking" reports that aren't bugs:

> DNS filtering works by refusing to resolve a domain. It only helps when the unwanted content comes from a domain of its own.

YouTube and Spotify serve ads from the **same domains** as content. Blocking the ad means blocking the service. No list achieves YouTube ad blocking at the DNS layer, and lists claiming to will break YouTube instead.

Similarly, apps with hardcoded IPs, or ads served from the first-party domain, are out of scope.

## 6. Verify a block end to end

```bash
dig @192.168.1.10 doubleclick.net
```

```
;; ANSWER SECTION:
doubleclick.net.   60   IN   A   0.0.0.0
```

`blockType: zeroIp` returns 0.0.0.0; `nxDomain` returns NXDOMAIN. Both are valid; NXDOMAIN is faster for clients but some applications handle it badly.

Then check the query log shows the block, which proves the whole chain.

## What not to do

- **Don't add ten overlapping lists.** More lists means more false positives and a slower startup, not better blocking.
- **Don't use hostname-based client groups** without working reverse DNS.
- **Don't run Blocky alongside Pi-hole or AdGuard on the same port.** One per host.
- **Don't expect DNS to block in-stream ads.** It cannot.

## Prevention

| Habit | Why |
|---|---|
| Query log enabled | The only record of what Blocky was actually asked |
| `default` group always populated | Catches every unlisted client |
| `strategy: blocking` with generous download timeouts | No unfiltered window at startup |
| Firewall outbound 53 except from Blocky | Stops devices bypassing you |

## FAQ

**Can it serve DoH/DoT to clients?**
Yes, with certificates configured. That also stops clients using someone else's DoH, if you point them at yours.

**Conditional forwarding for internal domains?**
`conditional.mapping` sends specific domains to a specific upstream — the right way to handle an internal authoritative zone.

**Does it cache?**
Yes, with configurable TTL bounds including minimum TTL, which materially improves perceived speed.

**Prometheus metrics?**
Exposed on the HTTP port; useful for graphing block rate, which is the fastest way to notice a list that silently died.
