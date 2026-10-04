---
title: "Nginx Proxy Manager: \"Internal Error\" When Requesting a Certificate"
slug: nginx-proxy-manager-certificate-internal-error
meta_description: "NPM shows a bare 'Internal Error' on Let's Encrypt requests. How to read the real reason out of the log, and the five causes it hides."
updated: October 2026
cluster: round 13 (tech) — NPM GitHub issues
competition: LOW
---

# Nginx Proxy Manager: "Internal Error" When Requesting a Certificate

The dialog says "Internal Error" and nothing else. That string is NPM swallowing certbot's actual output. The first job is not to fix anything — it's to see the real error.

## 1. Get the real message

```bash
docker logs nginx-proxy-manager --tail 100
```

Or read certbot's own log inside the container, which is more detailed:

```bash
docker exec -it nginx-proxy-manager \
  tail -n 80 /data/logs/letsencrypt.log
```

Everything below depends on which of these you see. Guessing without this step is how people spend an evening.

## 2. Match the message to the cause

**`urn:ietf:params:acme:error:unauthorized` / "Invalid response from http://…/.well-known/acme-challenge/…"**

Let's Encrypt reached something at your domain, but not NPM. Usually:

- Port 80 isn't forwarded to NPM, or is forwarded to a different host
- Your ISP blocks 80 (common on residential connections in several countries)
- Cloudflare proxying is **on** (orange cloud) for that record, so the challenge hits Cloudflare and gets its error page

Test what the world actually sees:

```bash
# from outside your network, e.g. a VPS or phone hotspot
curl -I http://yourdomain.example/.well-known/acme-challenge/test
```

A 404 from nginx is good — it means NPM is answering. A timeout, a Cloudflare page, or a router login page each name a different fix.

**`urn:ietf:params:acme:error:rateLimited` / "too many certificates already issued"**

Five duplicate certificates per week, per exact name set. If you've been retrying a failing request, you can hit this while the underlying problem is still unfixed. The limit resets on a rolling week — nothing to fix, just stop retrying and solve the real cause first.

**`DNS problem: NXDOMAIN looking up A for …`**

The record doesn't exist publicly. Split-horizon DNS is the usual reason: the name resolves inside your LAN via Pi-hole/AdGuard/Unbound and nowhere else. Let's Encrypt resolves from the public internet.

**`Problem binding to port 80: Could not bind to IPv4 or IPv6`**

Something else on the host has 80. Note that certbot in NPM runs in **webroot** mode behind nginx, so this specific error usually means a *second* proxy or a stray container:

```bash
sudo ss -tlnp | grep -E ':(80|443)\s'
```

**`Could not choose appropriate plugin` or a Python traceback**

This is the one genuine "internal" case: a broken certbot plugin install, typically after switching to a DNS challenge provider. The fix is to let NPM reinstall the plugin — delete the half-created certificate entry in **SSL Certificates**, recreate it, and let NPM run its `pip install certbot-dns-…` step fresh.

## 3. If port 80 is unusable: switch to DNS-01

This is the right answer for anyone behind a blocked port 80, behind CGNAT, or wanting a wildcard. In NPM: **SSL Certificates → Add → Use a DNS Challenge**, pick your provider, paste credentials.

The two things that go wrong here:

- **Propagation time too short.** The default is often 30 seconds. Many providers need 60–120. NPM exposes this field; raise it before blaming credentials.
- **Token scope.** A Cloudflare API token needs `Zone:DNS:Edit` **and** `Zone:Zone:Read`, scoped to the zone. A token with only DNS:Edit fails with an authentication error that reads like a wrong key.

```ini
# Cloudflare credentials file as NPM writes it
dns_cloudflare_api_token = your-scoped-token
```

A wildcard (`*.example.com`) **requires** DNS-01. There's no HTTP path to a wildcard, so if that's what you asked for, HTTP challenge failing isn't a bug.

## What not to do

- **Don't delete `/data` to "reset certificates".** That takes your hosts, access lists and existing certs with it. The certificate entries live in `/data/letsencrypt` and the database; a single broken entry can be deleted from the UI.
- **Don't retry the same request repeatedly.** You'll convert a fixable error into a week-long rate limit.
- **Don't leave Cloudflare proxying on and keep trying HTTP-01.** Either grey-cloud the record for the duration or switch to DNS-01 permanently.
- **Don't put NPM behind another reverse proxy** unless you've thought about who terminates TLS. Two proxies both wanting 80/443 produce exactly this error with no clue in the dialog.

## Prevention

| Habit | Why |
|---|---|
| Use DNS-01 from the start | Immune to port 80, CGNAT, and ISP blocks; supports wildcards |
| Keep one public A record per name, no split-horizon surprise | Removes the NXDOMAIN class |
| Check `docker logs` before clicking retry | Prevents self-inflicted rate limits |
| Renew with 30 days' headroom (NPM's default) | A failed renewal leaves time to debug before expiry |

## FAQ

**Certificate shows as created but the site is still untrusted.**
The cert exists; the proxy host isn't using it. Edit the proxy host → SSL tab → select the certificate, and enable Force SSL.

**Can I import a certificate I already have?**
Yes — "Add Certificate → Custom", paste the fullchain and private key. Renewals are then yours to handle.

**Does NPM renew automatically?**
Yes, via an internal cron. If renewals fail silently, the cause is usually the same one that's failing now; fix it once and renewal follows.

**Internal Error appears instantly, with no log line at all.**
That pattern points at a full disk or read-only `/data` volume. Check `df -h` and the mount.
