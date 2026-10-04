---
title: "Sonarr Not Importing Downloads? Permissions, Paths and the Download Client Moving Files"
slug: sonarr-import-failed
meta_description: "Downloads complete but Sonarr won't import them. The path-mapping mismatch between containers, permissions, hardlinks and why your download client shouldn't move files."
updated: October 2026
cluster: round 11 (tech) — Sonarr forums and GitHub issues only
competition: LOW
---

# Sonarr Not Importing Downloads? Permissions, Paths and the Download Client Moving Files

The download finishes, the queue says **"Downloaded — Unable to import, check logs for details"** or just sits on *Importing*, and the episode never appears in your library.

Four causes, in the order they're worth checking.

## 1. Path mismatch between containers (the big one)

Sonarr and your download client must see the **same file at the same path**. In Docker they usually don't, because each container was given a different mount.

The classic broken setup:

```yaml
sonarr:
  volumes:
    - /mnt/media:/tv
    - /mnt/downloads:/downloads
qbittorrent:
  volumes:
    - /mnt/downloads:/data/downloads     # different path inside!
```

The client reports `/data/downloads/Show.S01E01.mkv`; Sonarr looks for that path, finds nothing, and reports *path does not exist*.

**Fix: use one consistent layout across every container.** The standard advice is a single parent mount:

```yaml
volumes:
  - /mnt/user/data:/data       # same in Sonarr, Radarr, qBittorrent, SAB
```
with `/data/torrents/...` and `/data/media/...` underneath. One mount, same path everywhere, and hardlinks and atomic moves work as a bonus.

Check it from the UI: **System → Status** flags remote path mapping problems, and the queue item's error text usually contains the exact path Sonarr tried.

## 2. Permissions

Sonarr needs to **read** the completed download and **write** into the library — and to delete the source after a move.

- Match **PUID/PGID** across Sonarr, Radarr and the download clients, and make sure that user owns both trees
- `umask 002` (or 022) consistently, so new files are group-writable
- Check the actual files: `ls -la` on a completed download. Files owned by a different UID than Sonarr runs as is your answer
- On a NAS, check the **share-level** permissions as well as the filesystem ones

Error text to expect: *path does not exist or is not accessible by Sonarr*, or a permission-denied line in the log.

## 3. The download client is moving files itself

If your client moves completed downloads to a "finished" folder that Sonarr isn't watching — or renames them — Sonarr loses track between the completed event and the import.

- In **qBittorrent**: don't set a "Copy .torrent files"/move-on-completion path that Sonarr doesn't know about. Keep the completed folder inside the shared mount
- Don't point the client's completed folder **inside a Sonarr root folder**. That causes Sonarr to import from its own library and make a mess
- Let **Sonarr** do the moving and renaming. That's its job and it's the only component that knows the naming scheme
- Turn off any *arr-adjacent script that also moves files

## 4. The file itself can't be imported

- **Sample or extras** files only, or an archive (`.rar`) that nothing extracted
- **Unknown series/episode mapping** — the release doesn't match anything Sonarr monitors; use the queue's **Manual Import** to see what it couldn't match
- **An existing file** it won't overwrite because of quality cutoff settings
- `.part`/`.!qB` files still being written — the client reported completion too early
- Wrong **file extension** or a container Sonarr isn't configured to accept

## How to diagnose in five minutes

1. **System → Logs**, set log level to **Debug** or **Trace**, retry the import, read the lines around the failure. The real reason is almost always written there in plain text
2. On the queue item: **Manual Import** → it shows the file Sonarr can see and what it can't match
3. `docker exec -it sonarr ls -la /path/from/the/error` → does the file exist *from Sonarr's point of view*?
4. **System → Status** → remote path mapping and permission warnings
5. Compare mounts: `docker inspect sonarr` and `docker inspect qbittorrent`, volumes section

## A note on hardlinks

If Sonarr is **copying** instead of hardlinking (slow, doubles disk use), the cause is almost always that the download and library paths are **on different filesystems or different mounts** inside the container. The single-parent-mount layout above fixes that too. Hardlinks also need the same user to own both sides.

## FAQ

**Why does manual import work but automatic doesn't?**
Manual import runs with you choosing the file, bypassing the path the client reported. That pattern points squarely at a path-mapping problem.

**Should the download folder be inside my library root?**
No. Keep them as siblings under one parent mount.

**Why do imports fail only for some shows?**
Usually naming/matching, not permissions — check Manual Import for those specific releases.

**Do I need remote path mappings?**
Only when Sonarr and the client genuinely can't share a layout (e.g. client on another machine). If you control both, fix the mounts instead.
