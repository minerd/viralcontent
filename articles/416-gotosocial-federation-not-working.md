---
title: "GoToSocial: Not Federating With Other Instances"
slug: gotosocial-federation-not-working
meta_description: "Posts don't reach other servers, or remote accounts can't be found. TLS requirements, ports 80 and 443, host immutability and the keys you must not lose."
updated: October 2026
cluster: round 14 (tech) — GoToSocial docs and Codeberg issues
competition: LOW
---

# GoToSocial: Not Federating With Other Instances

Federation has hard prerequisites. Most "not federating" reports are one of them not being met, and two of them cannot be worked around.

## 1. TLS is mandatory

> Most ActivityPub implementations, GoToSocial included, refuse to federate over unencrypted transport.

So HTTP-only is not a configuration you can run and federate from. You need a valid certificate on your public hostname. GoToSocial can obtain one itself:

```yaml
# config.yaml
host: social.example.com
protocol: https
bind-address: "0.0.0.0"
port: 443
letsencrypt-enabled: true
letsencrypt-cert-dir: /gotosocial/storage/certs
letsencrypt-email-address: you@example.com
```

Or you terminate TLS at a reverse proxy and let GoToSocial serve plain HTTP behind it:

```yaml
protocol: https        # still https — this is what GTS advertises
bind-address: "127.0.0.1"
port: 8080
letsencrypt-enabled: false
```

`protocol: https` with a proxy in front is correct: it controls the URLs GoToSocial generates, not how it listens. Setting it to `http` makes every advertised URL wrong and federation fails even though your site loads.

## 2. Ports 80 and 443 must be reachable

- **443** serves the API and ActivityPub endpoints. Every instance you federate with connects here.
- **80** is needed for Let's Encrypt HTTP-01 validation, and for redirects.

```bash
# from outside your network
curl -sI https://social.example.com/.well-known/webfinger?resource=acct:you@social.example.com
curl -s https://social.example.com/.well-known/nodeinfo | head -c 200
```

WebFinger failing is the single most informative symptom: remote servers use it to resolve `@you@social.example.com` to your actor URL. If it 404s, nobody can find you.

Common causes of a WebFinger failure:

- Serving GoToSocial at a subpath. **It must be at the root of its hostname.**
- A proxy that doesn't pass `/.well-known/` through.
- `host` in the config not matching the public hostname.

## 3. The host is effectively permanent

Two documented constraints that catch people after the fact:

**You cannot switch implementations on the same domain.** Running GoToSocial on `example.org` and later moving to Mastodon, Akkoma or Misskey on the same domain causes federation problems — remote servers cache your actor's shape and keys, and the new software presents something incompatible. Choose the software before you choose the domain, or accept a domain change later.

**You cannot change your own domain** without losing your existing federation relationships. Followers point at URLs on the old host.

**The database holds your instance and account keys.** Lose it and you cannot federate again from the same domain — remote servers have your old public key and will reject signatures made with a new one. So:

```bash
# back this up like it's irreplaceable, because it is
cp /gotosocial/storage/sqlite.db /backups/gts-$(date +%F).db
```

For Postgres, a regular `pg_dump`. This is the most consequential backup in a GoToSocial deployment.

## 4. Federation modes

```yaml
instance-federation-mode: "blocklist"   # or "allowlist"
```

- **blocklist** (default) — federate with everyone except blocked domains
- **allowlist** — federate only with explicitly allowed domains

An instance set to allowlist with an empty list federates with nobody, and everything looks broken. Check this before anything else if you inherited the configuration or followed a hardening guide.

## 5. Implementation incompatibilities

> Since every ActivityPub implementation interprets the protocol slightly differently, some servers don't federate properly with GoToSocial yet.

This is real and it is not your configuration. Known areas: certain post types, polls, some media handling, and specific servers' signature validation. If one remote instance fails and twenty others work, it's upstream — check GoToSocial's issue tracker for that software before changing anything locally.

The reverse also happens: other projects have open issues about federating *with* GoToSocial. Both sides being actively worked on is the normal state for a younger implementation.

## 6. Reading the log

```bash
journalctl -u gotosocial -n 100 --no-pager | grep -iE 'federat|deliver|signature|dial'
```

What the lines mean:

- **`signature verification failed`** — key mismatch. If this is for *your* outbound posts at many instances, your keys changed (section 3). For one instance, it's theirs.
- **`dial tcp ... i/o timeout`** — you can't reach them. Their problem, or your egress.
- **`http 401/403` on delivery** — the remote instance is blocking you, or requires authorised fetch and something in your signature isn't acceptable.
- **No delivery attempts at all** — the post didn't leave the queue. Check `instance-federation-mode` and whether the recipient is known.

## What not to do

- **Don't run GoToSocial at a subpath.** WebFinger and actor URLs need the root.
- **Don't set `protocol: http`** behind an HTTPS proxy.
- **Don't change your domain** once you have followers. Plan it before launch.
- **Don't treat the database as recreatable.** It holds your federation identity.

## Prevention

| Habit | Why |
|---|---|
| Domain and software chosen together, before launch | Both are effectively permanent |
| Database backed up off-box, tested | The only copy of your instance keys |
| `curl` your own WebFinger endpoint after any proxy change | The fastest federation smoke test |
| Note your federation mode in your docs | Allowlist mode silently isolates you |

## FAQ

**How do I test federation?**
Follow an account on a large instance from yours, and have someone follow you back. One-directional success is informative: outbound working and inbound failing points at your inbound endpoints.

**Can I migrate from Mastodon to GoToSocial?**
Account moves are supported via the ActivityPub move mechanism, on a **different** domain. Same-domain software swaps are the problem.

**Does it need a lot of resources?**
No — that's the point of the project. A small VPS with SQLite is a supported configuration.

**Media from remote posts doesn't load.**
Remote media is proxied or cached depending on your settings; check storage permissions and the media cleanup schedule.
