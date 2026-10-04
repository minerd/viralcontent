---
title: "Immich Mobile Upload Stuck? Size Limits, Disk Space and the Backup Queue"
slug: immich-mobile-upload-stuck
meta_description: "Backup sits at 0%, the queue won't move, or large videos fail with 413. The Cloudflare 100 MB limit, server disk space, proxy body limits and how to reset the queue."
updated: October 2026
cluster: round 11 (tech) — Immich GitHub issues and discussions only
competition: LOW
---

# Immich Mobile Upload Stuck? Size Limits, Disk Space and the Backup Queue

Three distinct symptoms get described as "upload stuck", and they have different causes:

- **Nothing uploads at all**, queue empty or frozen
- **One item sits at 0%** and blocks everything behind it
- **Large videos** crawl, then fail

Check the easy server-side things first, because two of them are embarrassingly common.

## 1. Server disk space

Reported more than once as the whole answer. The app shows a stuck or failing upload; the server simply has nowhere to put the file.

```bash
df -h                 # the upload volume, and the database volume
docker exec -it immich_postgres df -h
```

Also check the **Immich admin → Server Stats** page. A full disk can also wedge PostgreSQL, which then produces unrelated-looking failures everywhere.

## 2. The 100 MB wall (if you use a Cloudflare tunnel)

If Immich is behind **Cloudflare**, there's a **request body limit — 100 MB on Free plans** — that you cannot configure away. Photos sail through; videos die, often at 0% for a long time and then a **413**.

Options:
- Upload large videos over **LAN, Tailscale or WireGuard**, bypassing the tunnel
- A paid Cloudflare plan with a higher limit
- Keep the tunnel for browsing and use a direct route for backup

This single limit explains most "photos work, videos don't" reports.

## 3. Reverse proxy and server body limits

Even without Cloudflare, each layer has a limit:

**nginx**
```nginx
client_max_body_size 50000M;
proxy_request_buffering off;
proxy_read_timeout 600s;
proxy_send_timeout 600s;
```
**Traefik**: check `respondingTimeouts` and any buffering middleware.
**Caddy**: generous by default, but check `request_body { max_size }` if you set it.

`proxy_request_buffering off` matters: with buffering on, nginx writes the whole upload to disk before passing it along, which both slows big uploads and can fill `/var`.

## 4. One bad item blocking the queue

A single asset the app can't read stalls everything behind it:

- A **partially-downloaded iCloud asset** (iOS) — the original isn't on the device
- A **corrupt** photo or video
- A file with the **same name** as one already uploaded (reported as a failure cause)
- Something in a **shared album** or a cloud-only item

What to do:
- Open the app's **backup/queue screen** and look at the item at the top
- **Exclude** that album or item from backup, let the queue drain, then deal with it individually
- A reported trick that saves progress cleanly: turn the **"enable backup" toggle off**, close the app, reopen, turn it back on

## 5. iOS background limits

On iOS, background upload runs only in windows the system grants. For a big backlog:

- **Charge + Wi-Fi + app open in the foreground**, screen on (raise Auto-Lock)
- **Background App Refresh** on, **Low Power Mode** off
- **Photos permission: Full Access**, not Limited
- If your library is on **Optimise iPhone Storage**, every original must be fetched from iCloud before upload — slow, and a frequent cause of apparent stalls. Use *Download and Keep Originals* for a big initial backup, or do the first pass from a desktop

## 6. Version skew

Keep the **mobile app and server versions in step**. Immich ships breaking changes often, and a mismatched pair produces upload failures that look like network problems. The app warns about this; take the warning seriously.

## 7. Prove it isn't the network

- Can you reach the server from the phone's browser and log in?
- Upload the **same file from a desktop browser** — works? Then it's the app or the phone. Fails? Server, proxy or disk
- Watch `docker compose logs -f immich_server` while the phone tries. A 413 or a timeout shows up immediately and ends the guessing

## Prevention

1. **Pin the server version** and update app and server together
2. **Monitor disk space** with an alert, not with hope
3. **Don't put the backup path through Cloudflare** if you shoot video
4. Do the **first bulk upload from a computer** with the CLI, then let the phone handle the incremental work
5. Remember Immich's own advice: it is **not a backup** on its own — keep a separate copy of your photos

## FAQ

**Why do photos upload but videos fail?**
A body-size limit somewhere — most often the Cloudflare 100 MB request limit, otherwise nginx or the app server.

**Why is my upload stuck at 0%?**
Usually a size/timeout limit, or an asset the app can't read. Check the server log while it tries.

**Does the app upload in the background on iOS?**
Only in granted windows. For a backlog, keep it foregrounded on power and Wi-Fi.

**My queue says a number but nothing moves.**
The item at the top is blocking it. Exclude it and the rest will drain.
