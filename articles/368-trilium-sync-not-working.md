---
title: "Trilium Notes: Sync Not Working With Your Server"
slug: trilium-sync-not-working
meta_description: "401 logged-in session not found, 413 request too large, or sync hangs at setup. The document secret, the body limit and the proxy rules."
updated: October 2026
cluster: round 14 (tech) — TriliumNext GitHub issues and discussions
competition: LOW
---

# Trilium Notes: Sync Not Working With Your Server

Match the symptom to the section; these have almost nothing in common.

| Symptom | Section |
|---|---|
| `401 Logged in session not found` / `401 Not authorized` | 1 |
| `413 Request Entity Too Large` | 2 |
| `Unexpected token '<'` during setup | 3 |
| Hangs on "Sync in progress" forever | 4 |
| Notes deleted after a sync | 5 |

## 1. 401 errors

Trilium's sync authenticates with the **document secret**, not your password. Both ends must share the same document — that is the whole model, and it's why "my password is right" is not reassuring.

The correct setup order matters:

- **New desktop → existing server:** choose *Sync from server* during setup. The desktop downloads the server's document, including its secret.
- **Existing desktop → new server:** set up sync from the desktop and let it push. Never initialise the server with its own fresh document first.

If both ends independently created a document, they have different secrets and will never authenticate. The fix is to discard one side:

```bash
# server, Docker — back up first
docker compose down
cp -a ./trilium-data ./trilium-data.bak
rm -rf ./trilium-data/document.db*
docker compose up -d
```

Then sync from the desktop, which pushes its document up.

Other 401 causes:

- **A reverse proxy adding its own auth** (basic auth, forward-auth). Trilium's sync client doesn't carry those credentials. Exempt the sync paths, or put sync on a route without forward-auth.
- **Session cookies not surviving the proxy.** `proxy_set_header Host $host;` is required.

## 2. 413 Request Entity Too Large

Trilium pushes sync batches, and a note with large attachments exceeds nginx's 1 MB default:

```nginx
location / {
    proxy_pass http://127.0.0.1:8080;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
    client_max_body_size 0;
    proxy_read_timeout 600s;
    proxy_send_timeout 600s;
}
```

`client_max_body_size 0` means unlimited. The websocket headers are not optional either — Trilium uses a websocket for live sync, and without the upgrade the client falls back to polling or appears stuck (section 4).

Behind Cloudflare's proxy, the body limit is a hard 100 MB on the free plan. A Trilium document with large image attachments can hit it; grey-cloud the record.

## 3. "Unexpected token '<'" at setup

The client asked for JSON and got HTML. You are hitting something other than Trilium:

- A login page from an auth proxy
- A 404 page because the URL has a path it shouldn't (`https://notes.example.com`, not `.../#root`)
- A redirect to HTTPS that the client didn't follow

```bash
curl -sI https://notes.example.com/api/setup/status
curl -s https://notes.example.com/api/setup/status
```

The second should return JSON. If it returns HTML, fix that before touching the client.

## 4. Sync appears to run forever

- **Websocket not proxied.** See section 2. Without it, the "sync in progress" indicator never clears.
- **A very large first sync.** The initial push of a big document genuinely takes a long time. Watch the server log for progress rather than the spinner:

```bash
docker logs trilium --tail 50 -f
```

- **The entity-change queue is stuck on one oversized note.** The log names it. Deleting or shrinking that note's attachment unblocks the rest.

## 5. Notes disappeared after sync

Trilium syncs deletions, which is correct and occasionally alarming. The dangerous sequence is: a desktop client with an **older, smaller** copy of the document syncs and its "absence" of recent notes propagates.

A reported variant: a desktop app's sync activity removing notes that didn't exist in its last known state. The protections:

- Trilium keeps **note revisions**; recover individual notes from the note's history.
- The server's `document.db` can be restored from a backup. Trilium writes periodic backups into `trilium-data/backup/`:

```bash
ls -la ./trilium-data/backup/
```

Restore by stopping the server, replacing `document.db`, and starting it — then re-sync clients *from* the server.

Never run two clients that have been offline for a long time against a server you've just restored, until you've confirmed which copy is authoritative.

## What not to do

- **Don't initialise both ends with their own document.** It guarantees 401s.
- **Don't put forward-auth in front of the sync endpoints.** The desktop client can't satisfy it.
- **Don't rely on sync as a backup.** It replicates deletions. Keep the `backup/` directory off-box.
- **Don't resolve a 401 by rebuilding the server document** without a backup of both sides.

## FAQ

**Does TriliumNext change any of this?**
The sync model is the same; the project is the maintained continuation and bug fixes land there.

**Can I sync without a server, via Syncthing?**
Syncing `document.db` with a file syncer corrupts it. Use Trilium's own sync, or a single instance accessed over the network.

**Multiple users on one server?**
Trilium is single-user per document. Multiple users means multiple instances.

**Sync works on LAN, fails remotely.**
Proxy: body size and websocket upgrade, in that order.
