---
title: "Docmost: Editor Loads But You Can Only Edit the Title"
slug: docmost-editor-read-only
meta_description: "Pages open, typing does nothing, or \"real-time editor connection lost\". The WebSocket headers your reverse proxy must forward, and the two endpoints."
updated: October 2026
cluster: round 14 (tech) — docmost/docmost GitHub issues and discussions
competition: LOW
---

# Docmost: Editor Loads But You Can Only Edit the Title

The single most reported Docmost problem, and it has one cause:

> **Docmost's collaborative editor uses a WebSocket. If your reverse proxy doesn't forward the `Upgrade` and `Connection` headers, the editor loads but is read-only.**

The title field is a plain REST update, which is why it works while the body doesn't. That asymmetry is the diagnostic.

## 1. The headers

**nginx:**

```nginx
server {
    server_name docs.example.com;

    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 86400s;
        proxy_send_timeout 86400s;
        client_max_body_size 50M;
    }
}
```

Every line matters:

- **`proxy_http_version 1.1`** — WebSocket upgrade requires HTTP/1.1. Without it the headers are ignored.
- **`Upgrade` / `Connection`** — the upgrade itself.
- **`proxy_read_timeout 86400s`** — a 60-second default drops the socket every minute, producing **"Real-time editor connection lost"** on a cycle.
- **`client_max_body_size`** — for attachments and images.

**Apache** (the reported failing case):

```apache
<VirtualHost *:443>
    ServerName docs.example.com
    RewriteEngine On
    RewriteCond %{HTTP:Upgrade} =websocket [NC]
    RewriteRule /(.*) ws://127.0.0.1:3000/$1 [P,L]
    RewriteCond %{HTTP:Upgrade} !=websocket [NC]
    RewriteRule /(.*) http://127.0.0.1:3000/$1 [P,L]
    ProxyPreserveHost On
</VirtualHost>
```

Apache needs `mod_proxy_wstunnel` enabled:

```bash
sudo a2enmod proxy proxy_http proxy_wstunnel rewrite
sudo systemctl reload apache2
```

**Caddy** needs nothing — it handles WebSockets automatically:

```
docs.example.com {
    reverse_proxy localhost:3000
}
```

**Traefik** likewise, provided no middleware interferes.

## 2. The two endpoints

A documented point of confusion: **which WebSocket path to proxy.** Docmost uses `/socket.io` and `/collab`.

The practical answer: **proxy everything through one location block** with the upgrade headers, as above. Splitting the configuration into separate locations per endpoint is where people get it wrong — a `location /` without upgrade headers plus a `location /collab` with them means `socket.io` fails and the editor still misbehaves.

Verify in the browser:

```
DevTools → Network → WS filter
```

You want connections to `/socket.io/...` and `/collab` in state **101 Switching Protocols**. Entries stuck **pending**, or repeatedly reconnecting, confirm the proxy is the problem.

```bash
curl -i -N \
  -H "Connection: Upgrade" -H "Upgrade: websocket" \
  -H "Sec-WebSocket-Version: 13" -H "Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==" \
  https://docs.example.com/collab | head -5
```

`HTTP/1.1 101` is success; a 200 or 400 means the upgrade didn't happen.

## 3. Behind a load balancer

Reported: **persistent slowness and WebSocket instability behind a load balancer / nginx.**

Two things to get right:

- **Sticky sessions.** Collaborative editing state is per-connection; a load balancer round-robining requests between two Docmost instances breaks it. Enable session affinity, or run a single instance.
- **Idle timeouts.** Cloud load balancers default to 60 seconds. Raise them well above your editing session length.

Also note Cloudflare's proxy: WebSockets are supported, but its own idle timeout and the 100-second limit on some plans interact badly with long editing sessions. Grey-cloud the record if you see periodic disconnects you can't explain.

## 4. The configurable timeout

A reported feature request worth knowing: **the WebSocket connection timeout has not been configurable** in some versions. So if the client gives up before your proxy does, you can't lengthen it from Docmost's side — you fix it at the proxy, or you upgrade.

```yaml
services:
  docmost:
    image: docmost/docmost:latest
    environment:
      APP_URL: https://docs.example.com
      APP_SECRET: a-long-random-string
      DATABASE_URL: postgresql://docmost:secret@db:5432/docmost
      REDIS_URL: redis://redis:6379
    ports:
      - "127.0.0.1:3000:3000"
```

`APP_URL` must match exactly how users reach it, including the scheme — the client builds its WebSocket URL from it, so an `http://` value on an HTTPS site produces a WebSocket to the wrong scheme and a silent failure.

## 5. Occasional crashes attributed to WebSockets

Reported with no reproduction pattern. Things that reduce it:

- **Redis must be present and reachable.** Docmost uses it for collaboration coordination; a flaky Redis produces intermittent editor failures:

```bash
docker exec docmost sh -c 'nc -zv redis 6379'
```

- **Memory.** The collaboration server holds document state; many concurrent editors on a small container is a crash source.
- Keep the version current; this area has had fixes.

## What not to do

- **Don't split the proxy configuration per WebSocket path.** One location block with upgrade headers.
- **Don't leave `proxy_read_timeout` at the default.** You'll get disconnects on a timer.
- **Don't run multiple instances without sticky sessions.**
- **Don't set `APP_URL` to the internal address.** The browser builds its socket URL from it.

## Prevention

| Habit | Why |
|---|---|
| WebSocket headers plus long timeouts, from the start | This is the problem, not a variant of it |
| Verify 101 in DevTools after any proxy change | Unambiguous, five seconds |
| `APP_URL` matching the public URL exactly | The client depends on it |
| Redis healthy and monitored | Collaboration state lives there |

## FAQ

**Can I use it without Redis?**
No; it's a required dependency for the collaborative features.

**Does it work offline / single user?**
The editor still uses the WebSocket even for one user, so no — the connection is required.

**Pages save but others don't see changes.**
Partial WebSocket success: your client connected, theirs didn't. Check from their browser.

**Attachments fail to upload.**
Separate: `client_max_body_size` and the storage configuration (local or S3).
