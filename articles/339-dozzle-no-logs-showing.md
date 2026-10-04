---
title: "Dozzle Shows No Logs: The Reverse Proxy Compression Trap"
slug: dozzle-no-logs-showing
meta_description: "Containers list fine but the log view is empty, or only empty through your proxy. Event-stream compression, logging drivers and socket access."
updated: October 2026
cluster: round 13 (tech) — Dozzle GitHub issues and FAQ
competition: LOW
---

# Dozzle Shows No Logs: The Reverse Proxy Compression Trap

The symptom that narrows this down fastest: **does it work when you hit Dozzle's port directly, bypassing your reverse proxy?**

```bash
# from a machine on the LAN
curl -s http://192.168.1.10:8080/ -o /dev/null -w '%{http_code}\n'
# then open http://192.168.1.10:8080 in a browser
```

- **Works direct, empty through the proxy** → compression on the event stream (section 1)
- **Empty both ways, container list populated** → logging driver (section 2)
- **No containers listed at all** → socket access (section 3)

## 1. The proxy is compressing the event stream

Dozzle streams logs as **Server-Sent Events** (`text/event-stream`). A compression middleware buffers the response to compress it, and since the stream never ends, nothing is ever flushed to the browser. The page loads, the log pane stays empty, and there's no error.

**Traefik** — exclude the content type from the compress middleware:

```yaml
http:
  middlewares:
    compress:
      compress:
        excludedContentTypes:
          - text/event-stream
```

Or simply don't apply the compress middleware to Dozzle's router.

**nginx** — disable buffering and compression on that location:

```nginx
location / {
    proxy_pass http://127.0.0.1:8080;
    proxy_http_version 1.1;
    proxy_set_header Connection "";
    proxy_buffering off;
    proxy_cache off;
    gzip off;
    proxy_read_timeout 86400s;
}
```

`proxy_buffering off` is the essential line. `proxy_read_timeout` matters too — with a 60-second default, the stream dies every minute and the log appears to stop rather than never start.

**Caddy** — exclude it from `encode`, or:

```
reverse_proxy localhost:8080 {
    flush_interval -1
}
```

`flush_interval -1` means flush immediately, which is exactly what a stream needs.

This single class of problem accounts for most "Dozzle shows nothing" reports from people running it behind a proxy, and it affects any SSE-based app the same way.

## 2. The logging driver

Docker's log API only returns logs for containers using a driver that stores them locally.

```bash
docker inspect <container> --format '{{.HostConfig.LogConfig.Type}}'
```

- **`json-file`** or **`local`** — fine, logs available
- **`journald`** — works, with some caveats
- **`syslog`, `fluentd`, `gelf`, `awslogs`, `splunk`** — logs go to the remote system; `docker logs` returns nothing, so Dozzle shows nothing. **This is not fixable in Dozzle.**

Check the daemon default too — a `/etc/docker/daemon.json` setting applies to every container:

```json
{
  "log-driver": "json-file",
  "log-opts": { "max-size": "10m", "max-file": "3" }
}
```

A related case: remote drivers with `cache-disabled: "true"` explicitly turn off the local copy. Removing that option restores local logs.

Containers must be recreated for a logging-driver change to take effect.

## 3. No containers listed

Socket access:

```yaml
services:
  dozzle:
    image: amir20/dozzle:latest
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
    ports:
      - "8080:8080"
```

- **Socket not mounted** — Dozzle starts and shows an empty list.
- **Permission denied** — on SELinux systems add `:z`, or check the socket's group. The error appears in Dozzle's own log:

```bash
docker logs dozzle --tail 20
```

- **Rootless Docker / Podman** — the socket is at a different path:

```yaml
      - /run/user/1000/docker.sock:/var/run/docker.sock:ro
      # Podman:
      - /run/user/1000/podman/podman.sock:/var/run/docker.sock:ro
```

For Podman, the socket needs to be enabled first: `systemctl --user enable --now podman.socket`.

Note the security position: read-only socket access still exposes every container's logs and metadata, which commonly include secrets printed at startup. Put Dozzle behind authentication if it's reachable beyond your own machine — it supports simple auth and a file-based user store.

## 4. Logs for a specific container are empty

- **The container genuinely logs nothing**, or logs to a file inside itself rather than stdout. Dozzle can only show what Docker captured.
- **The container was recreated.** Docker logs are per container ID. A `docker compose up -d` that replaced the container starts a fresh log; the old one's history is gone with it. With Compose Watch or frequent redeploys this is routine.
- **Log rotation already discarded it.** `max-size`/`max-file` caps mean old lines are gone.

## What not to do

- **Don't apply a global compression middleware to everything** and then debug individual apps. Exclude `text/event-stream` once, centrally.
- **Don't expose Dozzle publicly without auth.** Container logs are among the most secret-rich data on a host.
- **Don't switch the daemon's log driver to a remote one** and expect any local log viewer to work.
- **Don't mount the socket read-write.** Read-only is sufficient for Dozzle and strictly safer.

## Prevention

| Habit | Why |
|---|---|
| `text/event-stream` excluded from compression, globally | Fixes this app and every other SSE app at once |
| `proxy_buffering off` and long read timeouts for streaming apps | Prevents the stream-dies-after-60s variant |
| Keep `json-file` with size caps as the daemon default | Local logs available, bounded disk use |
| Read-only socket plus auth | Minimum sane posture for a log viewer |

## FAQ

**Can Dozzle show logs from multiple hosts?**
Yes — it supports remote Docker hosts and an agent mode. Each remote connection has its own access requirements.

**Does it keep history?**
No. It reads what Docker has. For retention, ship logs to Loki or similar.

**Live logs work but search finds nothing.**
Search operates on what's loaded; load more history first, or use a real log store for large searches.

**It's very slow with many containers.**
Each container is a stream. Limit what Dozzle watches with the filter options rather than letting it open hundreds.
