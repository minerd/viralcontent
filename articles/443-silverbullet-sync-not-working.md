---
title: "SilverBullet: Space Sync Doesn't Work"
slug: silverbullet-sync-not-working
meta_description: "\"Syncing space...\" appears and nothing happens. The sync plug failing to load, the client reset parameters, and service-worker caching."
updated: October 2026
cluster: round 14 (tech) — silverbulletmd/silverbullet GitHub issues
competition: LOW
---

# SilverBullet: Space Sync Doesn't Work

The reported symptom is precise:

> Invoking **Space: Sync** shows "Syncing space...", then nothing. The console logs `[Client] Booting up worker from /.fs/_plug/sync.plug.js` and stops — **the worker is waiting for the sync plug to load.**

So the plug is being fetched and never finishes initialising. Three escape routes, in increasing severity.

## 1. Reset the client

SilverBullet caches aggressively in the browser (service worker plus IndexedDB). Stale state is the usual cause.

The documented workaround sequence:

```
Run command: Client: Wipe
then refresh the page
then Space: Sync
```

`Client: Wipe` clears the local cache and IndexedDB copy of your space. **Your pages are on the server**, so this is safe — but confirm the server has them before wiping if you've been working offline.

URL parameters do the same without the command palette, which is useful when the UI itself is wedged:

```
https://sb.example.com/?resetClient=1
https://sb.example.com/?disablePlugs=1
```

- **`?resetClient=1`** — full client reset.
- **`?disablePlugs=1`** — loads with all non-built-in plugs disabled. If sync works with this, a third-party plug is breaking the load; if it still fails, it's the core sync plug or the server.

That second parameter is the real diagnostic and worth reaching for early.

A hard refresh (Ctrl+F5 / Cmd+Shift+R) forces the service worker to re-fetch and resolves a surprising share of these.

## 2. The service worker

```
DevTools → Application → Service Workers → Unregister
DevTools → Application → Storage → Clear site data
```

Then reload. A service worker from an older SilverBullet version serving a cached `sync.plug.js` that doesn't match the current server is exactly the shape of this failure.

There is an environment variable to disable the service worker:

```yaml
environment:
  - SB_DISABLE_SERVICE_WORKER=1
```

A reported caveat: **`SB_DISABLE_SERVICE_WORKER` does not disable sync**, so don't expect it to change sync behaviour by itself — it changes caching. Useful while debugging, not a fix.

## 3. Plugs failing to load

```
Error: Plug sandbox stopped
```

Reported on **reloading plugs**. Plugs run in a sandbox; one that crashes takes its worker with it, and if that's the sync plug you get the hang.

```
Run command: Plugs: Update
Run command: Plugs: Reload
```

If a specific third-party plug is implicated, remove it from your `PLUGS` page and update:

```markdown
<!-- PLUGS.md -->
- github:silverbulletmd/silverbullet-github/github.plug.js
```

Remove the line, run **Plugs: Update**, reload.

Note the ordering: sync is itself implemented as a plug, so a broken plug environment breaks sync specifically. `?disablePlugs=1` loading successfully while a normal load hangs is conclusive evidence of this.

## 4. Server-side

```bash
docker logs silverbullet --tail 100
```

```yaml
services:
  silverbullet:
    image: ghcr.io/silverbulletmd/silverbullet:v2
    environment:
      - SB_USER=user:password
    volumes:
      - ./space:/space
    ports:
      - "3000:3000"
```

- **The space directory must be writable** by the container's user. Read-only means pages load and nothing saves, which presents as sync failing:

```bash
docker exec silverbullet sh -c 'touch /space/_writetest && echo ok && rm /space/_writetest'
```

- **`SB_USER`** — with authentication on, a stale session gives 401s on the sync endpoints while the shell still renders from cache. Log out and in.
- **Behind a reverse proxy**, SilverBullet needs standard headers and a reasonable body size; it also uses a WebSocket-adjacent long-poll in places:

```nginx
location / {
    proxy_pass http://127.0.0.1:3000;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
    client_max_body_size 100M;
    proxy_read_timeout 600s;
}
```

## 5. Understand what sync is for

SilverBullet can run in two modes, and conflating them causes confusion:

- **Online** — the client reads and writes to the server directly. No sync needed.
- **Synced / offline-capable** — the client keeps a local copy in IndexedDB and syncs.

**Space: Sync** belongs to the second. If you only ever use SilverBullet online from one browser, you don't need it, and a hanging sync command is not blocking you.

The sync mode matters for mobile and for working offline. If that's your use case and sync is unreliable, the pragmatic position is to use online mode on reliable connections and treat offline editing as the feature with rough edges.

## 6. Don't sync the space folder with a file syncer

Worth stating: putting `/space` inside Syncthing or Dropbox alongside SilverBullet's own sync gives you two systems writing the same Markdown files. SilverBullet maintains an index; external writes it doesn't see produce stale search results at best.

Pick one: SilverBullet's sync, or a file syncer with SilverBullet pointed at the result and its index rebuilt after external changes:

```
Run command: Space: Reindex
```

## What not to do

- **Don't wipe the client before confirming the server has your pages.** Offline edits live only in IndexedDB.
- **Don't run a file syncer over `/space`** alongside SilverBullet sync.
- **Don't expect `SB_DISABLE_SERVICE_WORKER` to fix sync.** It changes caching only.
- **Don't keep a plug that crashes the sandbox.** Remove it and update.

## Prevention

| Habit | Why |
|---|---|
| `?disablePlugs=1` as the first diagnostic | Isolates plug problems in one page load |
| Space directory writable, verified | Silent save failures look like sync failures |
| Minimal plug set | Each plug is a chance to break the sandbox |
| Plain file backups of `/space` | Markdown on disk; back it up like text |

## FAQ

**Is my data safe in the browser?**
The server copy is authoritative. IndexedDB holds a working copy for offline use.

**Can several people edit one space?**
It's designed as a single-user tool; concurrent editing is not a supported model.

**Search returns stale results.**
Reindex. External writes bypass the index.

**v1 and v2 differences?**
v2 changed plug handling and client architecture. Guides for v1 can mislead on exactly these topics.
