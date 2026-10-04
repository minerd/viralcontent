---
title: "PhotoPrism Indexing Stuck or Finding Nothing"
slug: photoprism-indexing-stuck
meta_description: "Index runs and finds zero photos, hangs partway, or the worker is killed. Mount paths, read-only originals, memory and the MariaDB requirement."
updated: October 2026
cluster: round 13 (tech) — PhotoPrism GitHub issues
competition: LOW
---

# PhotoPrism Indexing Stuck or Finding Nothing

Three distinct failures, distinguishable in under a minute:

- **Index completes instantly, zero files** → PhotoPrism isn't looking where your photos are
- **Index starts, stops partway, container restarts** → memory
- **Index runs forever on the same file** → one bad file, or a storage path problem

## 1. Zero files found: check inside the container

The mount is the usual culprit, and the only reliable test is from PhotoPrism's own view:

```bash
docker exec -it photoprism ls -la /photoprism/originals | head
```

If that's empty, the bind mount is wrong — regardless of what the host path contains.

```yaml
services:
  photoprism:
    volumes:
      - /mnt/photos:/photoprism/originals
      - ./storage:/photoprism/storage
    environment:
      PHOTOPRISM_ORIGINALS_PATH: "/photoprism/originals"
      PHOTOPRISM_STORAGE_PATH: "/photoprism/storage"
      PHOTOPRISM_READONLY: "false"
```

Common mistakes:

- **The env var and the mount disagree.** `PHOTOPRISM_ORIGINALS_PATH` must point at the *container* path you mounted.
- **Mounting a parent that doesn't contain photos directly.** PhotoPrism recurses, so that's usually fine — but it skips hidden directories and anything in `.ppignore`.
- **Permissions.** PhotoPrism runs as the UID in `PHOTOPRISM_UID`/`GID`. If the originals are owned by another user with no read access for it, you get an empty index with no obvious error:

```bash
docker exec -it photoprism id
ls -ln /mnt/photos | head
```

- **A network share that mounted after the container started.** The container holds an empty directory. Order the mount before the container (systemd `After=`/`RequiresMountsFor=`, or a healthcheck).

Then index verbosely:

```bash
docker exec -it photoprism photoprism index --cleanup
docker logs photoprism --tail 100
```

## 2. The worker gets killed: memory

PhotoPrism's indexer generates thumbnails and runs TensorFlow classification. That is genuinely memory-hungry.

```bash
dmesg -T | grep -iE 'oom|killed process' | tail
```

Minimums that work in practice:

- **4 GB RAM** for a library of any size with classification on
- **2 GB** only with `PHOTOPRISM_DISABLE_TENSORFLOW: "true"`
- **Swap** — at least 4 GB. PhotoPrism's own documentation is explicit that swap is required on small systems, and this is the most commonly ignored requirement.

```yaml
    environment:
      PHOTOPRISM_WORKERS: 2
      PHOTOPRISM_DISABLE_TENSORFLOW: "false"
```

`PHOTOPRISM_WORKERS` defaults to the CPU count. On a 8-core box with 4 GB RAM that's a guaranteed OOM. Set it to 2 and the index takes longer but finishes — which is the trade you want.

## 3. Use MariaDB, not SQLite

SQLite is supported for small libraries and testing only. Above a few thousand photos it becomes the bottleneck and produces lock timeouts that look like a hung index.

```yaml
  mariadb:
    image: mariadb:11
    command: --innodb-buffer-pool-size=512M --transaction-isolation=READ-COMMITTED
    environment:
      MARIADB_DATABASE: photoprism
      MARIADB_USER: photoprism
      MARIADB_PASSWORD: insecure
      MARIADB_ROOT_PASSWORD: insecure
```

```yaml
    environment:
      PHOTOPRISM_DATABASE_DRIVER: "mysql"
      PHOTOPRISM_DATABASE_SERVER: "mariadb:3306"
      PHOTOPRISM_DATABASE_NAME: "photoprism"
      PHOTOPRISM_DATABASE_USER: "photoprism"
      PHOTOPRISM_DATABASE_PASSWORD: "insecure"
```

Note `--transaction-isolation=READ-COMMITTED`: without it, concurrent indexing produces lock contention. It's in the official compose file for a reason and gets dropped when people write their own.

If you started on SQLite, migrating means re-indexing. Decide early.

## 4. Stuck on one file

```bash
docker logs -f photoprism | grep -i index
```

The last filename logged is the one it's working on. Causes:

- **A huge video.** Transcoding a 4K 2-hour file takes a long time and looks stuck. Let it finish once.
- **A corrupt file.** Move it out of originals and re-index.
- **A RAW format needing a converter that isn't installed.** `PHOTOPRISM_DISABLE_RAW: "true"` to skip them, or ensure the image has darktable/rawtherapee.
- **An extremely large directory.** Hundreds of thousands of files in a single folder slows everything; split by year.

## What not to do

- **Don't delete the storage directory to "reset".** It holds generated thumbnails *and* your sidecar files. Rebuilding thumbnails for a large library takes many hours.
- **Don't mount originals read-write if you don't need to.** `PHOTOPRISM_READONLY: "true"` protects the source files; PhotoPrism then writes only to storage. For an archive this is the right setting.
- **Don't run with default `PHOTOPRISM_WORKERS` on a memory-constrained host.** It's the single most common cause of killed indexers.
- **Don't index over a slow network share with thumbnails enabled** and expect reasonable times. Copy locally, or accept days.

## Prevention

| Habit | Why |
|---|---|
| MariaDB with READ-COMMITTED from the start | Avoids a forced re-index later |
| `PHOTOPRISM_WORKERS: 2` and swap configured | Turns OOM kills into slow progress |
| `READONLY: true` for archival libraries | Your originals can't be modified by a bug or a misclick |
| Back up the database and `storage/sidecar` | Faces, labels and albums live there, not in the photos |

## FAQ

**Can I run PhotoPrism and Immich on the same files?**
Yes if both are read-only. Two writers on one directory is asking for trouble.

**Does it need a GPU?**
No. TensorFlow here runs on CPU; a GPU isn't used by the standard image.

**Faces aren't detected.**
Face recognition is a separate pass: `photoprism faces index`. It also needs the full indexing to have completed first.

**Index finished but new photos don't appear.**
Automatic indexing is off by default. Either run the index on a schedule or set `PHOTOPRISM_AUTO_INDEX` to a non-negative interval.
