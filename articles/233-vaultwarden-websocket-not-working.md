---
title: "Vaultwarden WebSockets Not Working After an Update? It's the Reverse Proxy"
slug: vaultwarden-websocket-not-working
meta_description: "Vault changes don't sync live and the log fills with WebSocket errors. Why port 3012 is gone, the HTTP/1.1 upgrade requirement, and working nginx and Caddy config."
updated: October 2026
cluster: round 10 (tech) — Vaultwarden GitHub discussions and forum threads only
competition: LOW
---

# Vaultwarden WebSockets Not Working After an Update? It's the Reverse Proxy

Symptoms: a password saved on your laptop doesn't appear on your phone until you force a sync, and the Vaultwarden log carries lines like **`Upgraded websocket I/O handler failed: WebSocket protocol error`**.

**The cause is almost always reverse proxy configuration** — and the thing that changed is where WebSockets live.

## What changed: no more port 3012

Vaultwarden used to serve notifications over a **separate WebSocket port, 3012**, with `WEBSOCKET_ENABLED=true`. Newer versions moved to an implementation **built into Rocket, on the normal HTTP port**.

So after an update:

- `WEBSOCKET_ENABLED` is **no longer needed** for the built-in path
- Proxy config that routes `/notifications/hub` to **`:3012`** now points at nothing
- Exposing 3012 in your compose file does nothing useful

**Fix:** delete the special-case 3012 routing and the extra port mapping, and proxy `/notifications/hub` to the **same backend and port** as everything else — with WebSocket upgrade headers set.

## The one requirement: HTTP/1.1 upgrade

WebSockets require an **HTTP/1.1 Upgrade handshake**. If your proxy speaks HTTP/2 or HTTP/1.0 to the backend and doesn't switch to 1.1 for this request, the handshake fails. That is the underlying reason behind nearly every one of these reports.

### nginx

```nginx
map $http_upgrade $connection_upgrade {
    default upgrade;
    ''      close;
}

server {
    # ...
    location / {
        proxy_pass http://vaultwarden:80;
        proxy_http_version 1.1;
        proxy_set_header Upgrade    $http_upgrade;
        proxy_set_header Connection $connection_upgrade;
        proxy_set_header Host              $host;
        proxy_set_header X-Real-IP         $remote_addr;
        proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

The `map` block is the part people omit. Without it, `Connection: upgrade` is sent on every request including non-WebSocket ones, which produces its own errors.

### Caddy

```
vault.example.com {
    reverse_proxy vaultwarden:80
}
```

Caddy handles the upgrade automatically. If it still fails, you have an extra hop that doesn't.

### Traefik

Also automatic — but check you don't have a **compression** or **buffering** middleware on the router, which breaks WebSockets.

## Other things that break it

- **Buffering.** `proxy_buffering on` with a long-lived stream causes trouble; turn it off for the notifications path
- **Timeouts.** WebSockets are long-lived. Raise `proxy_read_timeout` / `proxy_send_timeout` (e.g. to 3600s) or the connection is cut every 60 seconds and reconnects forever
- **Security headers.** Reports point at over-eager header sets breaking the handshake; keep HSTS and drop the rest while testing
- **Cloudflare proxy:** WebSockets must be **enabled** for the zone. Cloudflare also has idle timeouts, and some rules interfere
- **Two layers of proxy** (Cloudflare → nginx → Vaultwarden, or NPM in front of Traefik): every layer needs to pass the upgrade
- **`DOMAIN` must be set correctly** in Vaultwarden's environment, with the right scheme — clients derive the notification URL from it
- The log line `Sending after closing is not allowed` is **noise** when clients disconnect normally; a burst of them points at a proxy cutting connections

## How to test it properly

1. Browser **DevTools → Network → WS** filter, while logged into the web vault. A healthy setup shows a `/notifications/hub` connection with status **101 Switching Protocols** and it stays open
2. **Status 200 or 400** instead of 101 = the upgrade never happened → proxy config
3. Connection opens then **closes every N seconds** = timeout
4. From a shell:
   ```
   curl -i -N -H "Connection: Upgrade" -H "Upgrade: websocket" \
     -H "Sec-WebSocket-Version: 13" -H "Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==" \
     https://vault.example.com/notifications/hub
   ```
   You want `101`
5. Check Vaultwarden's own log at the same moment

## Does it matter?

WebSockets only drive **live sync notifications**. Without them the vault still works; clients just sync on their own schedule or when you pull-to-refresh. So this is a quality-of-life fix, not an emergency — don't break a working deployment at midnight chasing it.

## FAQ

**Do I still need WEBSOCKET_ENABLED?**
No, not with the built-in implementation on the main HTTP port.

**Should I still expose port 3012?**
No. Remove it from your compose file and your proxy config.

**Why does the web vault work but sync is delayed?**
Normal HTTP works; the WebSocket upgrade is failing. Check the WS tab in DevTools.

**Caddy users: why does it just work?**
Caddy performs the HTTP/1.1 upgrade for you. nginx needs the `map` block and `proxy_http_version 1.1` spelled out.
