---
title: "Joplin Server Sync Fails With 404: The Path You Actually Need"
slug: joplin-server-404-sync
meta_description: "Joplin reports 404 or 'Could not connect' against your own server. The URL with no trailing path, the proxy body limit, and the Postgres connection."
updated: October 2026
cluster: round 13 (tech) — Joplin forum and GitHub issues
competition: LOW
---

# Joplin Server Sync Fails With 404: The Path You Actually Need

A 404 from Joplin Server during sync almost always means one of three things: the URL has the wrong path, your reverse proxy is rewriting it, or `APP_BASE_URL` on the server doesn't match how you reach it. The third is the one that produces the most baffling behaviour, because the web UI works and only sync fails.

## 1. The URL in the Joplin client

For **Joplin Server** (not Nextcloud, not WebDAV), the sync target is the **bare base URL**:

```
https://joplin.example.com
```

No `/joplin`, no `/api`, no trailing slash. The client appends its own paths.

The three mistakes:

- Using the **Nextcloud/WebDAV** sync type with a Joplin Server URL. These are different protocols. Settings → Synchronisation → Synchronisation target → **Joplin Server**.
- Adding the path from a WebDAV guide (`/remote.php/dav/files/user/joplin`). That path belongs to Nextcloud.
- A trailing slash, which on some proxy configurations becomes a double slash and a 404.

## 2. `APP_BASE_URL` must match exactly

This is the server-side half, and the cause of "the web UI works but sync 404s":

```yaml
services:
  joplin:
    image: joplin/server:latest
    environment:
      APP_BASE_URL: https://joplin.example.com
      APP_PORT: 22300
      DB_CLIENT: pg
      POSTGRES_HOST: db
      POSTGRES_DATABASE: joplin
      POSTGRES_USER: joplin
      POSTGRES_PASSWORD: changeme
```

`APP_BASE_URL` is the **external** URL, with scheme, without trailing slash. Joplin Server builds links and validates requests against it. If it says `http://localhost:22300` while clients come in on `https://joplin.example.com`, sync requests are rejected or redirected into a 404.

Change it and restart the container — it's read at startup.

## 3. Reverse proxy

```nginx
location / {
    proxy_pass http://127.0.0.1:22300;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    client_max_body_size 100M;
    proxy_read_timeout 300s;
}
```

Specific pitfalls:

- **Serving Joplin on a subpath** (`https://example.com/joplin`). Joplin Server does not support a subpath cleanly; set `APP_BASE_URL` to include it and expect problems with some clients. A subdomain is the supported layout, and the right answer if you're still setting up.
- **`client_max_body_size`.** Notes with image attachments exceed nginx's 1 MB default. The error then is a 413, but partial sync state can produce 404s on subsequent requests for items the server never stored.
- **`X-Forwarded-Proto`** missing means the server thinks requests are HTTP and builds `http://` URLs — mixed content in the UI, redirect failures in sync.

Test what the client sees:

```bash
curl -s https://joplin.example.com/api/ping
```

Expected: `{"status":"ok","message":"Joplin Server is running"}`. A 404 here, before any client involvement, points at the proxy or `APP_BASE_URL`. A 502 means the container isn't reachable.

## 4. If `/api/ping` is fine but sync still fails

- **Wrong credentials.** The default admin is `admin@localhost` with password `admin`; **change it** at first login, and note that the email is the username. Sync uses the same account unless you created separate users.
- **E2EE mismatch.** If encryption was enabled on one client, every client needs the master password. A client without it syncs metadata and fails on content, which reads as a broken sync.
- **Postgres not ready.** On a cold start, Joplin Server can come up before the database and log migration failures. Check:

```bash
docker compose logs joplin | grep -iE 'error|migration|connect'
```

Add `depends_on` with a healthcheck so the order is deterministic — this intermittent startup race is responsible for a lot of "it works after I restart it twice".

- **Disk full on the server.** Item uploads fail; the client retries forever.

## What not to do

- **Don't use SQLite for Joplin Server.** It's supported for testing only and corrupts under concurrent sync. Postgres is the real requirement.
- **Don't change `APP_BASE_URL` without restarting.** The old value stays live and you'll conclude the change didn't help.
- **Don't delete the client's local data to "resync".** Export a JEX backup first; a half-synced state plus a local wipe loses notes.
- **Don't run two sync targets against one profile.** Switching targets without a full re-upload leaves the client with items the new server doesn't have.

## Prevention

| Habit | Why |
|---|---|
| Subdomain, not subpath | Subpath support is the source of most URL problems |
| `APP_BASE_URL` identical to the URL clients use | Single source of truth for everything the server builds |
| Export a JEX archive monthly | The only client-independent backup of notes |
| Healthcheck on Postgres, with `depends_on` | Removes the startup race |

## FAQ

**Can I sync to a plain WebDAV server instead?**
Yes, and it avoids all of this. You lose multi-user sharing and the published-note feature.

**Sync works on desktop, 404s on mobile.**
Check that mobile isn't on a split-DNS path reaching a different host, and that `APP_BASE_URL` matches the externally resolvable name.

**"Unknown item type" or conflict notes after a server move.**
The client's sync state references the old target. Re-sync from one known-good client and reset sync on the others.

**Does it need a lot of resources?**
No — a 1 GB container plus Postgres is sufficient for a single user; the body-size and timeout settings matter more than CPU.
