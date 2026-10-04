---
title: "AdGuard Home: Wildcard DNS Rewrites Not Working"
slug: adguard-home-dns-rewrite-wildcard
meta_description: "*.example.com returns nothing while the bare name works, or only the first of several rewrites applies. The matching order and the AdBlock-style alternative."
updated: October 2026
cluster: round 14 (tech) — AdguardTeam/AdGuardHome GitHub issues
competition: LOW
---

# AdGuard Home: Wildcard DNS Rewrites Not Working

Wildcard rewrites in AdGuard Home have several long-standing rough edges. Knowing which one you've hit saves a lot of trial and error.

Test precisely — always query AdGuard directly, not through a client with a cache:

```bash
dig @192.168.1.10 app.example.com +short
dig @192.168.1.10 example.com +short
dig @192.168.1.10 deep.sub.example.com +short
```

## 1. The bare domain is not covered by the wildcard

`*.example.com` matches `app.example.com` but **not** `example.com` itself. If you want both, add two rewrites:

```
*.example.com  →  192.168.1.10
example.com    →  192.168.1.10
```

This is standard wildcard semantics, and it's the most common "it doesn't work" that isn't a bug.

## 2. Only the first matching rewrite is returned

A reported behaviour: with **several rewrite entries for the same wildcard**, `nslookup` returns only the first, whereas non-wildcard names return all matching rewrites. If you were relying on two A records under one wildcard for round-robin, it won't work.

Use a single rewrite per wildcard, and if you need multiple addresses, point the wildcard at a name you control elsewhere.

## 3. Specificity doesn't win

The behaviour people expect — the more specific rule overriding the broader one — is not reliable here. With:

```
*.example.com           →  192.168.1.10
*.internal.example.com  →  192.168.1.20
```

the lookup can match the **broader** rule first, because the rules are evaluated in list order rather than by specificity. `host.internal.example.com` then resolves to `.10`.

Two workarounds:

- **Order matters** — put the most specific rules first in the list. Reorder and retest.
- **Enumerate the exceptions explicitly** rather than relying on a nested wildcard:

```
host1.internal.example.com  →  192.168.1.20
host2.internal.example.com  →  192.168.1.20
*.example.com               →  192.168.1.10
```

Tedious, deterministic, and it works.

## 4. Exceptions via AdBlock-style DNS rewrites

For anything beyond the simplest case, the **custom filtering rules** are more expressive than the Rewrites table. They live under **Filters → Custom filtering rules** and use `$dnsrewrite`:

```
||*.server^$dnsrewrite=10.0.0.11,denyallow=null-host.server
||null-host.server^$dnsrewrite=0.0.0.0
```

The pattern above rewrites everything under `.server` to `10.0.0.11` **except** `null-host.server`, using `denyallow` to carve out the exception. This is the mechanism to reach for when the Rewrites UI can't express what you need, and it's where the exception logic actually behaves.

Simpler forms:

```
||internal.example.com^$dnsrewrite=NOERROR;A;192.168.1.20
||example.com^$dnsrewrite=NOERROR;CNAME;real.example.net
```

Note the precedence: **custom filtering rules are evaluated before the Rewrites table**, so a `$dnsrewrite` rule overrides a conflicting rewrite entry. That's useful — and it's also why a forgotten rule in the filtering list makes the Rewrites UI look broken.

## 5. Things that look like rewrite failures

- **Client-side caching.** Browsers and the OS cache aggressively. Test with `dig @<adguard-ip>` and nothing else until it works.
- **DNS-over-HTTPS in the browser.** Chrome and Firefox bypass your resolver entirely when DoH is on. Disable it to test.
- **The client isn't using AdGuard.** Many devices ignore DHCP DNS (hardcoded 8.8.8.8 in a smart TV, for example). Check with `dig` from the client to confirm which resolver answers.
- **A blocklist entry beats the rewrite.** Check the query log — it shows which rule matched. The **Allowed** list overrides blocklists; the query log is the authoritative record of what happened to the query.
- **Rewrites not applying to the AdGuard host itself** if it resolves via a different path.

## 6. Rewrites behave differently for AAAA

A wildcard rewrite to an IPv4 address does not stop AAAA queries. Clients with IPv6 connectivity may query AAAA, get a public answer (or NODATA), and behave inconsistently. For internal names, add an explicit AAAA rewrite or return NODATA:

```
||internal.example.com^$dnsrewrite=NOERROR;AAAA;
```

## What not to do

- **Don't nest wildcards and expect specificity to resolve it.** Order the list, or enumerate.
- **Don't test from a browser.** Use `dig` against AdGuard's address.
- **Don't mix Rewrites and `$dnsrewrite` rules for the same name.** Pick one place.
- **Don't forget AAAA.** Half-resolved names cause slow, intermittent failures that look like something else.

## Prevention

| Habit | Why |
|---|---|
| One wildcard per domain, exceptions enumerated | Avoids the specificity problem entirely |
| `$dnsrewrite` rules for anything conditional | The only place exception logic works properly |
| Check the query log after every change | It names the rule that matched |
| Explicit AAAA handling for internal names | Removes a whole class of intermittent failures |

## FAQ

**Does this work the same in Pi-hole?**
Pi-hole uses dnsmasq config for wildcards (`address=/example.com/192.168.1.10`), which handles the bare domain and subdomains in one line and respects specificity properly.

**Can a rewrite point at a CNAME?**
Yes, with `$dnsrewrite=NOERROR;CNAME;target`.

**Rewrites work for some clients only.**
Those clients aren't using AdGuard, or are using DoH. Check with `dig` from each.

**Should I use rewrites for split-horizon DNS?**
It's the common approach, and it's why the wildcard limitations matter. A real internal authoritative zone (Unbound, Technitium, dnsmasq) is more predictable for anything complex.
