---
title: "Actual Budget Sync Fails: 413, \"File Too Large\" and the Proxy Limit"
slug: actual-budget-sync-file-too-large
meta_description: "Actual won't sync after your budget grows: 413 Payload Too Large, upload failures, or sync stuck. The server, proxy and client limits you must raise together."
updated: October 2026
cluster: round 13 (tech) — Actual Budget GitHub and Discord
competition: LOW
---

# Actual Budget Sync Fails: 413, "File Too Large" and the Proxy Limit

Actual syncs by uploading the whole encrypted budget file, not a diff. So sync works perfectly for months and then breaks — because the file crossed a size limit somewhere in the chain. There are **three** limits, and raising one doesn't help if another is lower.

## 1. Confirm it's a size problem

In the browser devtools network tab during a sync, or in the server log:

```
413 Payload Too Large
```

Or, from nginx, the characteristic "client intended to send too large body":

```bash
docker logs nginx-proxy-manager --tail 50 | grep -i 'too large'
```

How big is the file?

```bash
du -sh /path/to/actual-data/server-files/*
```

Budgets with several years of transactions and many accounts commonly reach 20–80 MB. The default nginx body limit is **1 MB**. That gap is the whole problem.

## 2. Raise the reverse proxy limit

This is the limit people hit first, and the one they most often fix in the wrong place.

**nginx / Nginx Proxy Manager** — in the proxy host's *Advanced* tab:

```nginx
client_max_body_size 200M;
proxy_read_timeout 600s;
proxy_send_timeout 600s;
```

The timeouts matter as much as the size: a 60 MB upload over a slow link exceeds nginx's default 60 s read timeout and fails with a 504 instead, which looks like a different bug.

**Traefik** — Traefik has no body-size limit by default, so a 413 behind Traefik means it came from Actual's own server. But do raise the timeouts:

```yaml
labels:
  - "traefik.http.routers.actual.middlewares=actual-timeout@file"
```

**Caddy** — also unlimited by default; same note applies.

**Cloudflare** — the free plan caps request bodies at **100 MB**, and this is not configurable. If your budget approaches that, you must bypass the proxy (grey-cloud the record, or use a tunnel configured for larger bodies) — no server setting fixes it.

## 3. Raise the Actual server's own limit

Actual's server has an upload size ceiling of its own:

```yaml
environment:
  ACTUAL_UPLOAD_FILE_SYNC_SIZE_LIMIT_MB: 200
  ACTUAL_UPLOAD_SYNC_ENCRYPTED_FILE_SYNC_SIZE_LIMIT_MB: 200
  ACTUAL_UPLOAD_FILE_SIZE_LIMIT_MB: 200
```

Set all three. The encrypted variant is the one that applies when end-to-end encryption is on — which it is for most people — and it's routinely missed because the non-encrypted name appears first in documentation.

Restart the container after changing these; they're read at startup.

## 4. If it's still failing

- **Shrink the file.** Actual accumulates sync messages. In the app: **Settings → Advanced → Reset sync** on one device, then re-download on the others. This compacts the message history and can cut the file size substantially. Export a backup first.
- **Check disk space on the server.** A full volume gives write errors that surface as sync failures.
- **Check the client.** The mobile app has its own, lower tolerance for slow uploads. If desktop syncs and mobile doesn't, it's a timeout, not a limit — try it on Wi-Fi before concluding anything.
- **Look for a second proxy.** Many setups have Cloudflare → Traefik → Actual. Each hop is a limit.

## What not to do

- **Don't delete the budget on the server to "start fresh".** If your only full copy is on a device that can't sync, you're one cache clear away from losing it. Export a `.zip` backup from the app first, always.
- **Don't raise only `client_max_body_size` and stop.** Without the server-side env vars and the timeouts you'll just move the error.
- **Don't set the limit to the exact current file size.** It grows. Use a multiple.
- **Don't disable end-to-end encryption to shrink the file.** It barely helps and costs you the main privacy property.

## Prevention

| Habit | Why |
|---|---|
| Set `client_max_body_size` generously on every proxy host, not just Actual's | This class of bug appears across self-hosted apps |
| Export a `.zip` backup monthly | The only reliable recovery path for a sync-broken budget |
| Reset sync annually | Keeps the file small, so you never approach the Cloudflare ceiling |
| Note every proxy hop in your notes | Makes the "which limit is it" question answerable in a minute |

## FAQ

**Why does Actual upload the whole file?**
Its sync model is a CRDT message log plus the file; for encrypted budgets the server can't merge anything, so the client ships the lot.

**Sync works on the local network but not remotely.**
Classic proxy-limit shape: locally you bypass the proxy entirely.

**I get "network error" rather than 413.**
That's usually the timeout path, or Cloudflare's 100 MB cut-off, which closes the connection rather than returning a clean status.

**Does bank sync (SimpleFIN/GoCardless) affect file size?**
Indirectly — more imported transactions mean a bigger file, and that's often what pushes a long-stable setup over the line.
