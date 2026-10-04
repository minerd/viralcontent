---
title: "Nextcloud notify_push Not Working? Run the Self-Test First"
slug: nextcloud-notify-push-not-working
meta_description: "High Performance Backend installed but load hasn't dropped. The self-test, trusted proxies, WebSocket proxying, and how to prove clients are actually using it."
updated: October 2026
cluster: round 12 (tech) — Nextcloud community and all-in-one GitHub discussions
competition: LOW
---

# Nextcloud notify_push Not Working? Run the Self-Test First

Two symptoms: clients don't get live updates, or — more often — **server load didn't drop** after installing the High Performance Backend and you can't tell whether it's working.

## 1. The two commands that answer everything

```bash
occ notify_push:self-test
occ notify_push:metrics
```

- **self-test** checks the whole chain and prints what's wrong in plain language. Run it before changing anything
- **metrics** shows **active connections**. Open the desktop client and watch the count go up; close it and watch it drop. If the number never moves, no client is using push, whatever the admin page says

That's the difference between "installed" and "working".

## 2. Trusted proxies (the most common failure)

notify_push connects to Nextcloud and must be recognised as a **trusted proxy**, otherwise Nextcloud sees the wrong client IP and the handshake is rejected:

```php
'trusted_proxies' => ['127.0.0.1', '::1', '172.18.0.0/16'],
'forwarded_for_headers' => ['HTTP_X_FORWARDED_FOR'],
```

Add the push service's address (container IP range in Docker, `127.0.0.1` on bare metal). Your reverse proxy must also forward `X-Forwarded-For` and `X-Forwarded-Proto`.

Reported variant: in Docker, using the **internal service name** fails while the **public HTTPS domain** works — because the TLS/host expectations line up with what clients use. If self-test complains about the URL, try the public address.

## 3. WebSockets through the proxy

Push is a WebSocket at `/push`. Every layer must upgrade it:

**nginx**
```nginx
location /push/ {
    proxy_pass http://127.0.0.1:7867/;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_read_timeout 3600s;
}
```

**Caddy** handles it; remove compression middleware if you added any. Behind **Cloudflare**, enable WebSockets and mind idle timeouts.

Test:
```bash
curl -i -N -H "Connection: Upgrade" -H "Upgrade: websocket" \
  -H "Sec-WebSocket-Version: 13" -H "Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==" \
  https://cloud.example.com/push/test/cookie
```

## 4. Load didn't drop — what to actually expect

With push working, desktop clients poll **PROPFIND roughly every 5 minutes** instead of every 30 seconds. You should see a clear drop in PROPFIND volume in your access log — not zero requests.

If PROPFIND is still arriving every 30 seconds:
- Clients are **too old** to use push, or weren't restarted
- Clients are connecting to a **different URL** than the one push is configured for
- `metrics` shows zero connections → they're not using it at all

Count them:
```bash
grep PROPFIND /var/log/nginx/access.log | tail -50
```

## 5. Crashes and certificate problems

- Reported: **notify-push keeps crashing** in some all-in-one setups — check its own log, and whether the Redis/DB connection details it was given are right
- **SSL handshake errors** behind an HTTP proxy: set `SSL_CERT_DIR` and `NO_PROXY` in the push service's environment so it doesn't try to reach Nextcloud through a proxy that breaks TLS
- Redis is required; a push service that can't reach Redis does nothing useful

## 6. Order of operations

1. `occ notify_push:self-test`
2. Fix whatever it names
3. `occ notify_push:metrics` with a client open
4. Check the **PROPFIND interval** in the access log
5. Only then look at proxy config in detail

## Prevention

- Keep **trusted_proxies** correct when container subnets change
- Pin versions: the app version must match the Nextcloud major version
- Monitor `metrics` — it's the only honest indicator
- Keep clients updated

## FAQ

**How do I know push is actually working?**
`notify_push:metrics` shows active connections that change as clients connect.

**Should PROPFIND requests stop completely?**
No — they drop to roughly every five minutes per client.

**Internal hostname or public URL?**
Whatever the self-test accepts; the public HTTPS URL is reported as more reliable in Docker.

**Is Redis required?**
Yes. Without it, push can't function.
