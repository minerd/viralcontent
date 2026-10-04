---
title: "Nextcloud Behind a Cloudflare Tunnel: Fixing Clients, Certificates and Upload Limits"
slug: nextcloud-cloudflare-tunnel
meta_description: "Nextcloud works in a browser through a Cloudflare tunnel but the desktop and mobile clients fail. Trusted domains, trusted proxies, TLS verify and the 100 MB body limit."
updated: October 2026
cluster: round 10 (tech) — Nextcloud/Cloudflare forums and GitHub discussions only
competition: LOW
---

# Nextcloud Behind a Cloudflare Tunnel: Fixing Clients, Certificates and Upload Limits

The classic version of this problem: **the web interface works perfectly through the tunnel, but the desktop client and the phone apps refuse to connect** — often with *"The hostname did not match any of the valid hosts for this certificate."*

Browsers are forgiving. The sync clients are not. Here's the full set of things that have to line up.

## 1. Tunnel origin settings

In the Cloudflare dashboard, on your public hostname's **origin** configuration:

- **Service type**: `HTTP` if Nextcloud is serving plain HTTP locally; `HTTPS` if it has its own certificate
- With `HTTPS`, enable **No TLS Verify** — otherwise cloudflared rejects a self-signed origin certificate
- Set **Origin Server Name** and **HTTP Host Header** to your **public hostname** (`cloud.example.com`), not the container name or IP
- Point the service at a **host IP and port** (`http://192.168.1.50:11000`) rather than a Docker network alias, unless cloudflared shares that network

That certificate error in the clients is nearly always the **Host Header / Origin Server Name** mismatch.

## 2. Nextcloud's own config

In `config/config.php`:

```php
'trusted_domains' => [ 'cloud.example.com' ],
'overwrite.cli.url' => 'https://cloud.example.com',
'overwriteprotocol' => 'https',
'overwritehost' => 'cloud.example.com',
'trusted_proxies' => [ '172.18.0.0/16' ],   // the cloudflared container/host range
'forwarded_for_headers' => [ 'HTTP_CF_CONNECTING_IP', 'HTTP_X_FORWARDED_FOR' ],
```

Why each matters:
- **trusted_domains** — without your public hostname, Nextcloud refuses the request outright
- **overwriteprotocol: https** — the tunnel terminates TLS, so Nextcloud sees HTTP and generates `http://` links. Clients then mix schemes and fail. This single line fixes a lot of "works in browser, not in client"
- **trusted_proxies** — otherwise every login shows cloudflared's IP, brute-force protection throttles your real users, and rate limits trip
- **forwarded_for_headers** — so the real client IP is read from Cloudflare's header

With the AIO (all-in-one) image, set the equivalents as environment variables rather than editing the file by hand.

## 3. The upload limit nobody warns you about

Cloudflare's proxy enforces a **request body size limit** — **100 MB on Free plans** (higher on paid tiers). A tunnel is still the Cloudflare edge, so this applies.

Symptoms: photos sync fine, **videos and big files fail**, sometimes with a 413.

Options:
- Enable Nextcloud's **chunked upload** path and keep chunk size under the limit (desktop/mobile clients chunk by default; check `max_chunk_size`)
- Put large transfers over a **VPN (Tailscale/WireGuard) or a direct LAN connection** instead of the tunnel
- Pay for a plan with a larger limit
- Keep bulk restores off the tunnel entirely

Also set the server-side limits so they aren't the smaller constraint: `upload_max_filesize`, `post_max_size`, PHP `max_execution_time`, and `client_max_body_size` if nginx is in the path.

## 4. WebDAV, sync and the long-request problem

- `.well-known` redirects for `caldav`/`carddav`/`webdav` must be served, or clients complain at setup
- Cloudflare's edge will cut **very long-running requests**; big server-side operations (first scan, large moves) can die mid-flight. Run those from the console (`occ`) rather than through the tunnel
- **WebSockets / Notify Push** need to pass through; enable WebSockets for the hostname and check the push service's own path

## 5. Cloudflare settings that break things quietly

- **Rocket Loader / Auto Minify / Mirage** — turn them off for this hostname
- **Browser Integrity Check** and some **WAF managed rules** block sync clients' user agents. If the browser works and the client doesn't, check the WAF event log
- **Access (Zero Trust) policies** in front of the hostname will block the desktop and mobile clients, which can't complete an interactive login. Either bypass Access for the Nextcloud hostname or use service tokens — this is the second most common cause of "browser yes, client no"
- **Caching rules** on `/remote.php` or `/dav` — exclude them

## Debug order

1. `occ config:list system` — check the overwrite and trusted values
2. `curl -I https://cloud.example.com` from outside — look at the scheme and any redirect
3. Browser **and** client, side by side
4. Cloudflare **WAF / Access event log** while the client fails
5. `docker logs cloudflared` and the Nextcloud log at the same moment
6. Test the same thing over **LAN** to prove whether the tunnel is the variable

## FAQ

**Why does the browser work but the desktop client not?**
Usually `overwriteprotocol`, a Host Header mismatch, or a Cloudflare Access/WAF rule the client can't satisfy.

**Is the 100 MB limit really unavoidable?**
On Free plans, yes, for a single request. Chunked uploads keep each request under it; large transfers are better off a tunnel.

**Do I need a certificate on the origin?**
No — plain HTTP origin with the tunnel is fine and simpler. If you do use HTTPS locally, enable No TLS Verify.

**Why are all my logins coming from one IP?**
`trusted_proxies` isn't set, so Nextcloud sees cloudflared instead of the real client.
