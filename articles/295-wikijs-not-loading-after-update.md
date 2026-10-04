---
title: "Wiki.js Broken After an Update? Storage Paths, SQLite Rebuilds and Rollback"
slug: wikijs-not-loading-after-update
meta_description: "Wiki.js unreachable or throwing 500s after an upgrade. The exports/subpath dependency error, images lost between restarts, SQLite rebuilds in LXC and reverting cleanly."
updated: October 2026
cluster: round 12 (tech) — Wiki.js GitHub discussions only
competition: LOW
---

# Wiki.js Broken After an Update? Storage Paths, SQLite Rebuilds and Rollback

Four reported post-upgrade failures, each with a different fix.

## 1. The dependency error that stops it starting

Reported: after updating, Wiki.js fails with

```
Package subpath './public/extractFiles' is not defined by "exports"
```

This is a Node module resolution problem introduced by a dependency version, not something in your content. The reported resolution was **reverting to an earlier version** (2.4, or 2.5.299 specifically).

Practically:
- **Roll back the image tag** to your previous working version
- Check the project's discussions for your exact version and that string
- Don't try to patch `node_modules` in place in a container — you'll lose it on the next restart

```yaml
# docker-compose.yml
image: requarks/wiki:2.5.299      # pin, don't use :2 or :latest
```

## 2. Images disappear after a restart, or 500 on image load

Two reported variants with the same root cause: **storage paths**.

- Using a **relative path** in the Local File System storage module means Wiki.js resolves it differently after a restart, and the cache can't be regenerated — images vanish
- Images that load for a while and then return Internal Server Error, traced to the Local Storage module (disabling it stopped the errors)

Fixes:
- Set an **absolute path** for local storage, inside a **named volume**:
  ```yaml
  volumes:
    - wiki-data:/wiki/data
  ```
  with the storage module pointing at `/wiki/data/content` (or wherever you mounted)
- Confirm the directory is **writable** by the container's user
- If you rely on Git storage as the source of truth, that's more robust than local file storage for exactly this reason

## 3. SQLite in an LXC container

Reported for Proxmox LXC installs: the update problem is **the SQLite3 native module rebuild** — the package needs to compile against the container's Node, and fails.

Options:
- **Move to PostgreSQL.** This is the real answer; SQLite is the least supported backend for Wiki.js and upgrades keep tripping on the native module
- If you must stay on SQLite, ensure build tooling (`build-essential`, `python3`) is present, then rebuild the module
- Back up the `.db` file before any attempt

## 4. HTTPS settings reverted

Also reported: after upgrades, **HTTPS configuration becomes misconfigured**, requiring a manual fix to the config file and a restart.

- Keep a copy of `config.yml` outside the container
- After upgrading, diff it against your copy
- If Wiki.js is behind a reverse proxy, it's simpler to let Wiki.js serve **plain HTTP internally** and terminate TLS at the proxy — fewer things to break on upgrade

## Recovery order

1. **Read the container log** — all four failures above announce themselves there
   ```bash
   docker compose logs --tail=100 wiki
   ```
2. **Roll back the image tag** to the previous working version. Wiki.js content lives in the database, so rolling the app back is usually safe (check release notes for database migrations, which are *not* reversible)
3. Fix **storage paths** to absolute paths in named volumes
4. Move **SQLite → PostgreSQL** if that's your backend
5. Diff **config.yml** against your saved copy

## Prevention

1. **Pin the image tag** and upgrade deliberately
2. **PostgreSQL**, not SQLite
3. **Absolute storage paths** in named volumes
4. Back up the **database and config.yml** before every upgrade; the database is your wiki
5. Consider enabling **Git storage** so your content exists outside Wiki.js entirely — the strongest insurance there is

## FAQ

**Is rolling back safe?**
Usually, since content is in the database — but check whether the upgrade ran a schema migration, which may not be reversible. Restore the database backup if so.

**Why did my images disappear?**
Relative storage paths and an unmounted or changed data directory. Use absolute paths in a named volume.

**Should I use SQLite?**
No. Use PostgreSQL; the native module is a recurring upgrade problem.

**Where is my content stored?**
In the database, plus whatever storage module you configured (local files, Git). Back up both.
