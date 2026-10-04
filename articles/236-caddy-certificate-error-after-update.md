---
title: "Caddy Can't Get a Certificate After an Update? Rate Limits, Challenges and the ACME Folder"
slug: caddy-certificate-error-after-update
meta_description: "Caddy restarts and TLS breaks: obtaining certificate failed. How to read the real ACME error, rate limits, challenge reachability and when to switch issuer."
updated: October 2026
cluster: round 11 (tech) — caddy.community threads and GitHub issues
competition: LOW
---

# Caddy Can't Get a Certificate After an Update? Rate Limits, Challenges and the ACME Folder

Caddy restarts after an update and every site is broken with some variant of **`obtaining certificate: ... challenge failed`** or **`one or more domains had a problem`**.

The error you see in the first line is usually not the useful one. Get the real one first.

## Step 1: read the actual ACME error

```bash
journalctl -u caddy -n 200 --no-pager          # systemd
docker compose logs --tail=200 caddy           # docker
```

Look for the **`detail`** field in the ACME problem document. It says exactly what the CA could not do, and it determines everything below:

| Detail says | Meaning |
|---|---|
| `too many certificates already issued` | **Rate limit** — do not retry |
| `Timeout during connect` / `connection refused` | The CA can't reach you on **port 80/443** |
| `DNS problem: NXDOMAIN` | The name doesn't resolve publicly |
| `Invalid response ... 404` | HTTP challenge path not reaching Caddy |
| `x509: certificate signed by unknown authority` | Caddy doesn't trust the **CA it's talking to** (internal ACME) |
| `unauthorized` on DNS challenge | Wrong API token or zone for the DNS provider |

## Step 2: if it's a rate limit, stop

Let's Encrypt limits **certificates per registered domain per week**. A restart loop after an update — Caddy retrying on every start — burns through that fast, which is how an unrelated bug turns into a week-long outage.

- **Stop Caddy** while you fix the underlying problem. Don't leave it looping
- Test against the **staging** endpoint while debugging:
  ```
  {
    acme_ca https://acme-staging-v02.api.letsencrypt.org/directory
  }
  ```
  Staging certificates aren't trusted by browsers, but they prove your config works without spending real quota
- Caddy can use **ZeroSSL** as an alternative issuer (`tls { issuer zerossl }`), which has separate limits — useful as a bridge, not as a fix for a broken challenge

## Step 3: challenge reachability

**HTTP-01** needs the CA to reach `http://your-domain/.well-known/acme-challenge/...` on **port 80**, from the public internet.

Common post-update breakages:
- A container that no longer **publishes port 80** (people map only 443 and wonder why renewal stopped)
- Something else grabbed port 80 after a host reboot
- A firewall or ISP blocking 80
- A reverse proxy in front that intercepts `.well-known`
- An AAAA record pointing at an IPv6 address that doesn't actually serve

**TLS-ALPN-01** needs port 443 reachable, and breaks if anything terminates TLS before Caddy (another proxy, Cloudflare in full-proxy mode).

**DNS-01** is the answer for wildcards, for hosts not publicly reachable, and when 80/443 are blocked. It needs the matching **DNS provider module** compiled in — and that's a classic post-update failure: you installed a plain Caddy binary over your custom build and lost the plugin. Rebuild with `xcaddy`, or use the container image that includes your provider.

## Step 4: the data directory

Caddy stores accounts, keys and certificates in its **data directory** (`/data` in Docker, `~/.local/share/caddy` or `/var/lib/caddy` on systemd).

After an update:
- Confirm the **volume is still mounted** at the same place. A Caddy that lost its data directory re-registers and re-requests everything — straight into the rate limit
- Confirm **permissions**: the `caddy` user must own it
- Deleting the ACME **users/accounts** folder is a known last-resort fix for a stuck account state, but it forces a fresh registration, so don't do it while rate-limited

For Docker, the single most valuable line in your compose file is a **named volume for `/data`**. Without it, every recreate is a fresh ACME account.

## Step 5: internal CA / local HTTPS

If you serve internal names, Caddy issues from its **own local CA** — and `x509: certificate signed by unknown authority` means the client (or an upstream Caddy) doesn't trust that CA. Install the root with `caddy trust` on the machine that needs it, and make sure the container has `ca-certificates` installed. Don't point an internal name at a public CA; it can't validate it.

For upstreams with self-signed certificates, the proxy needs to be told explicitly:
```
reverse_proxy https://backend:8443 {
    transport http {
        tls_insecure_skip_verify
    }
}
```

## Prevention

1. **Named volume for `/data`** — this is the one that saves you
2. **Pin the image tag**, including custom builds with DNS plugins
3. Use **DNS-01** for anything not publicly reachable on 80/443
4. Keep **port 80 open** even on an HTTPS-only site, for the challenge and the redirect
5. Test config before reload: `caddy validate --config /etc/caddy/Caddyfile`

## FAQ

**Why did certificates work before the update?**
They were already issued and cached. The update either lost the data directory or broke the challenge path, and you only find out at renewal — or at restart.

**Can I use Caddy's staging mode permanently?**
No — staging certs aren't trusted. Use it only while debugging.

**Do I need port 80 if I only serve HTTPS?**
For HTTP-01, yes. Otherwise use DNS-01 or TLS-ALPN-01.

**I'm rate-limited. What now?**
Stop Caddy, fix the root cause with staging, and wait out the window. Switching issuer is a bridge, not a licence to keep retrying.
