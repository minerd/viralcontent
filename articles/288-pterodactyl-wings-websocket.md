---
title: "Pterodactyl Console Stuck Loading? The Wings WebSocket and Origin Mismatch"
slug: pterodactyl-wings-websocket
meta_description: "Panel works, server page spins forever. 'websocket: request origin not allowed by Upgrader', domain mismatches between panel and Wings, and proxy requirements."
updated: October 2026
cluster: round 12 (tech) — Pterodactyl panel GitHub issues only
competition: LOW
---

# Pterodactyl Console Stuck Loading? The Wings WebSocket and Origin Mismatch

Wings starts cleanly, the panel loads, server state shows in the admin view — and the **server console page spins forever**. The console is a WebSocket straight from your browser to Wings, so it's the one thing the panel's own health check doesn't prove.

## 1. The error that names the cause

Check Wings' log at debug level while you load the console:

```bash
journalctl -u wings -f
# or
docker logs wings -f
```

The line to look for:

```
encountered HTTP/500 error while handling request
error=websocket: request origin not allowed by Upgrader
```

That's Wings refusing the connection because the **browser's Origin** doesn't match what it expects. Which leads to the actual fix.

## 2. Panel and Wings must agree on the domain

Documented behaviour: when the panel is accessed through a **different domain** than the one Wings knows about, the admin views still work (server-to-server calls) but the **client console doesn't** (browser-to-Wings).

Check both sides:

- **Wings** `config.yml` → `remote:` must be the panel's URL as users actually reach it
- **Panel** → the node's **FQDN** must be the hostname your browser uses for Wings
- If you reach the panel at `panel.example.com` but Wings' `remote` says `http://10.0.0.5`, fix it

Then restart Wings. Mismatched values here are the single most common cause.

Also set `allowed_origins` in Wings' config if you legitimately access the panel from more than one hostname:

```yaml
allowed_origins:
  - https://panel.example.com
  - https://panel.internal.example.com
```

## 3. The node's SSL mode must match reality

- Node set to **use SSL** in the panel but Wings serving plain HTTP → the browser tries `wss://` and fails
- Node set to HTTP while the panel is served over HTTPS → **mixed content**, and the browser blocks the WebSocket silently (check the browser console; this is the one with no server-side error at all)
- Certificate not trusted by the **browser** (self-signed) → the WebSocket fails even though curl with `-k` works

Everything must be HTTPS, with a certificate the browser accepts, or everything plain HTTP on a trusted LAN. Don't mix.

## 4. The reverse proxy in front of Wings

If Wings sits behind nginx/Caddy/Traefik on port 443:

```nginx
location / {
    proxy_pass https://127.0.0.1:8080;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_read_timeout 3600s;
}
```

Short read timeouts drop long-lived consoles; missing upgrade headers prevent them entirely.

**Cloudflare**: the Wings/daemon port needs WebSockets enabled, and Cloudflare only proxies certain ports — people commonly leave the daemon hostname **DNS-only** (grey cloud) for exactly this reason.

## 5. Browser-specific behaviour

Reported: console issues in **Brave** that didn't occur in Chrome. Shields and strict blocking break WebSockets to non-standard hosts.

Test in another browser (and in a private window with extensions off) before changing server config. The browser console's network tab tells you whether the WebSocket got a **101** or died.

## 6. Checklist

```bash
# does wings answer at all?
curl -k https://node.example.com:8080/api/system
# is the token right? (panel: node configuration)
# does the websocket upgrade?
curl -i -N -k -H "Connection: Upgrade" -H "Upgrade: websocket" \
  -H "Sec-WebSocket-Version: 13" -H "Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==" \
  -H "Origin: https://panel.example.com" \
  https://node.example.com:8080/api/servers/<uuid>/ws
```

You want **101**. A 403/500 with an origin message points straight back to section 2.

## Prevention

1. One **canonical panel URL**, used everywhere
2. Keep **node FQDN**, SSL setting and Wings' `remote` in sync
3. Set **`allowed_origins`** if you have more than one access path
4. **DNS-only** for the daemon hostname unless you've configured Cloudflare for it
5. Re-run the node's **configuration deploy** after changing panel URLs

## FAQ

**Why does the admin page work but the console not?**
Admin data comes from the panel; the console is a direct browser-to-Wings WebSocket.

**Where does the origin error come from?**
Wings rejecting a browser Origin it doesn't recognise — usually a panel URL mismatch.

**Does Cloudflare proxying work?**
Only on supported ports with WebSockets enabled. Most people keep the daemon record DNS-only.

**Console works in Chrome but not Brave.**
Browser shields. Test with them off before touching the server.
