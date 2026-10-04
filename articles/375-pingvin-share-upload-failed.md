---
title: "Pingvin Share: Uploads Fail Behind a Reverse Proxy"
slug: pingvin-share-upload-failed
meta_description: "Uploads never finish, stall at 0%, or work by IP and fail by hostname. TRUST_PROXY, body size, chunk handling and the reverse-share size cap."
updated: October 2026
cluster: round 14 (tech) — stonith404/pingvin-share GitHub issues
competition: LOW
---

# Pingvin Share: Uploads Fail Behind a Reverse Proxy

The diagnostic that splits this in thirty seconds:

```bash
# from a machine on the LAN, bypassing the proxy
curl -sI http://192.168.1.10:3000/
```

Then try an upload directly against that address in a browser.

- **Works by IP, fails by hostname** → reverse proxy (sections 1–2)
- **Fails both ways** → storage or the app (section 3)

## 1. TRUST_PROXY and the app URL

```yaml
services:
  pingvin-share:
    image: stonith404/pingvin-share
    environment:
      - TRUST_PROXY=true
      - APP_URL=https://share.example.com
    ports:
      - "127.0.0.1:3000:3000"
    volumes:
      - ./data:/opt/app/backend/data
```

`TRUST_PROXY=true` makes Pingvin honour `X-Forwarded-*`. Without it, the app builds links and validates requests against the internal address, and share links come out wrong even when uploads work.

Binding to `127.0.0.1:3000` rather than `0.0.0.0:3000` is deliberate: it keeps the app private and makes the proxy the only entrance.

## 2. The proxy settings that matter

```nginx
server {
    server_name share.example.com;

    client_max_body_size 0;
    proxy_request_buffering off;
    proxy_read_timeout 3600s;
    proxy_send_timeout 3600s;

    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Each line earns its place:

- **`client_max_body_size 0`** — unlimited. The 1 MB default rejects almost everything, and the browser reports a generic network error rather than a 413.
- **`proxy_request_buffering off`** — nginx otherwise buffers the whole upload to disk before forwarding. On a large file that means the progress bar completes, then a long pause, then a timeout. This is the setting behind "upload reaches 100% and then fails".
- **Long timeouts** — a 60-second default kills any sizeable upload.

**Traefik** has no body-size limit by default, so a 413 behind Traefik comes from Pingvin itself. Do raise the timeouts:

```yaml
    labels:
      - "traefik.http.routers.pingvin.rule=Host(`share.example.com`)"
      - "traefik.http.services.pingvin.loadbalancer.server.port=3000"
```

and in the static config, raise `respondingTimeouts`.

**Cloudflare proxied** caps request bodies at 100 MB on the free plan, and that is not configurable. A file-sharing app behind an orange cloud will fail above it — grey-cloud the record or use a tunnel configured for larger bodies.

**Caddy**:

```
share.example.com {
    reverse_proxy localhost:3000 {
        flush_interval -1
    }
    request_body {
        max_size 0
    }
}
```

## 3. Failures that aren't the proxy

- **Reverse-share size limit.** A reverse share (a link that lets someone upload *to* you) carries its own maximum upload size, set when you created it. An upload exceeding it fails, and the error is not always clear. Check the reverse share's settings, not the global ones.
- **A quirk worth knowing:** opening a reverse-share link has, in some versions, interfered with subsequent *regular* uploads in the same browser session. If uploads stop working after you used a reverse share, try a fresh private window before investigating anything else.
- **Safari.** File upload has failed specifically in Safari on macOS in some version/proxy combinations while Chrome worked. Test a second browser before assuming a server problem.
- **Disk full.** Pingvin stores files under its data directory:

```bash
df -h ./data
du -sh ./data
```

- **Permissions.** The container writes as its configured user; a root-owned bind mount fails on the first write:

```bash
sudo chown -R 1000:1000 ./data
```

## 4. Chunked uploads

Large files are sent in chunks. Two consequences:

- A proxy that rewrites or buffers request bodies interferes with chunking — hence `proxy_request_buffering off`.
- A chunk failing mid-upload can leave a partial file in the data directory. These accumulate; clean them periodically if your instance is busy.

## 5. "Can't access it except from its IP address"

Reported and distinct: the app loads by IP and errors by hostname. That's `APP_URL` not matching, or the proxy not passing `Host`. Both must be right — the app uses `APP_URL` to generate links and compares origins.

## What not to do

- **Don't leave `client_max_body_size` at the default** on a file-sharing app. It's the first thing to change.
- **Don't expose port 3000 publicly** alongside the proxy. Bind it to localhost.
- **Don't run it behind Cloudflare's proxy for large files.** The 100 MB cap is absolute.
- **Don't debug in one browser.** Safari and Firefox have each had upload-specific issues.

## Prevention

| Habit | Why |
|---|---|
| `client_max_body_size 0` + `proxy_request_buffering off` | Covers both large-file failure modes |
| `TRUST_PROXY=true` and a correct `APP_URL` | Correct links, correct origin checks |
| Data directory on a volume you monitor for space | Uploads fail silently on a full disk |
| Expiry set on shares by default | Keeps the disk from filling over time |

## FAQ

**Is there a size limit in the app itself?**
There's a configurable maximum share size in admin settings. Check it before blaming the proxy.

**Can I use S3 for storage?**
Recent versions support S3-compatible backends, which moves the disk-space question elsewhere.

**OIDC login redirect fails.**
A separate concern: the callback URL must match `APP_URL` exactly, including scheme.

**Do shares expire automatically?**
Only if you set an expiry. Unexpiring shares are the usual cause of a full disk months later.
