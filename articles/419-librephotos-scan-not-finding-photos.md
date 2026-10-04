---
title: "LibrePhotos: Scan Photos Hangs or Finds Nothing"
slug: librephotos-scan-not-finding-photos
meta_description: "The scan sits in waiting, or completes reporting success with photos missing. Symlinks, read-only volumes, worker timeouts and stale NFS handles."
updated: October 2026
cluster: round 14 (tech) — LibrePhotos/librephotos GitHub issues
competition: LOW
---

# LibrePhotos: Scan Photos Hangs or Finds Nothing

LibrePhotos runs its scan as a background job. Three distinct failures, and one of them reports **success** while silently skipping files — worth knowing, because it means "the scan finished" is not evidence.

## 1. The scan sits in "waiting" and never progresses

The job queue isn't running or can't claim the job.

```bash
docker compose logs backend --tail 100 | grep -iE 'scan|worker|rq|redis|timeout'
docker compose ps
```

- **Redis not reachable.** LibrePhotos queues jobs through Redis; without it jobs are created and never picked up:

```yaml
    environment:
      - REDIS_HOST=redis
      - REDIS_PORT=6379
```

- **The worker container isn't running.** In the standard compose there is a separate worker; check it's up and not restarting.
- **A previous job is stuck holding the lock.** Restarting the backend and worker clears it:

```bash
docker compose restart backend proceeding_worker
```

- **`CRITICAL WORKER TIMEOUT`**, reported especially on ARM: a single long operation exceeds the worker's timeout and the worker is killed mid-scan. Raise it:

```yaml
    environment:
      - WORKER_TIMEOUT=3600
      - HEAVYWEIGHT_PROCESS=1
```

`HEAVYWEIGHT_PROCESS=1` keeps memory use down by running fewer parallel ML tasks — the right setting on anything with under 8 GB.

## 2. Files not found: symlinks and mounts

**Symlinked directories are not scanned.** A documented limitation: `directory_watcher.py` cannot access symlink directories, so a photo tree assembled from symlinks appears empty.

Use bind mounts instead:

```yaml
services:
  backend:
    volumes:
      - /mnt/photos:/data:ro
      - ./protected_media:/protected_media
      - ./logs:/logs
```

```bash
docker compose exec backend ls -la /data | head
docker compose exec backend find /data -maxdepth 2 -type d | head -20
```

An empty listing inside the container is the whole answer, regardless of what the host shows.

**Read-only volumes block some imports.** A reported case: **JPG photos not added when the volume is read-only, while videos were added without issue.** LibrePhotos writes sidecar or derived data in some paths, and a read-only mount fails that step for images.

If you want your originals protected, mount them read-only and accept that some features (in-place thumbnail writing, metadata write-back) won't work — or mount read-write and rely on backups instead. Pick deliberately; the mixed behaviour above is what happens when you don't.

**Network shares.** Reported failures include **stale NFS handles**, `EACCES` permission errors, and mounts dropping mid-scan. Each produces per-file failures:

```bash
docker compose exec backend sh -c 'cat /proc/mounts | grep -E "nfs|cifs"'
dmesg -T | grep -iE 'nfs|cifs' | tail
```

A mount that disappears mid-scan is the worst case because the scan continues and reports success for what it did manage.

## 3. The scan reports success with photos missing

This is the behaviour to internalise:

> The counter advances and the job finishes reporting unqualified success, so you are told the scan completed while photos were silently missing.

Per-file failures were not surfaced. So verify by count, not by status:

```bash
# how many image files on disk
docker compose exec backend sh -c 'find /data -type f \( -iname "*.jpg" -o -iname "*.jpeg" -o -iname "*.heic" -o -iname "*.png" \) | wc -l'
```

Compare against the photo count in the UI. A gap means files were skipped, and the backend log holds the per-file errors:

```bash
docker compose logs backend --tail 500 | grep -iE 'error|skip|cannot|permission' | head -40
```

Newer versions record per-file scan failures on the job itself, which makes this far less painful — another reason to stay current.

## 4. Common per-file causes

- **HEIC without the right libraries** in older images — the file is read and fails to decode.
- **Zero-byte or truncated files** from an interrupted copy.
- **Filenames with unusual encodings** on a CIFS mount.
- **Permissions** on individual files copied as a different user:

```bash
docker compose exec backend sh -c 'id; ls -ln /data | head'
```

The container's UID must be able to read them. Set `USER_ID`/`GROUP_ID` in the environment to match your files' ownership.

## 5. Scan completes, faces and objects missing

Separate passes. Scanning imports files; **face detection, clustering and object classification are separate jobs** you trigger from the admin or settings page. A library that scanned fine with no faces hasn't run face detection yet — and on a modest machine those passes take hours.

## What not to do

- **Don't symlink into the photo directory.** Bind mounts only.
- **Don't trust "scan completed".** Compare counts.
- **Don't run the ML passes on a 2 GB host** and expect them to finish. `HEAVYWEIGHT_PROCESS=1` and patience, or more RAM.
- **Don't scan across a flaky network mount.** Copy locally or fix the mount first.

## Prevention

| Habit | Why |
|---|---|
| Bind mounts, container UID matching file ownership | Removes the invisible-files class |
| `WORKER_TIMEOUT` raised, `HEAVYWEIGHT_PROCESS=1` on small hosts | Stops workers being killed mid-scan |
| Count files on disk versus in the UI after every scan | The only reliable completeness check |
| Keep the version current | Per-file error reporting improved specifically here |

## FAQ

**How long should a first scan take?**
Import is fast; thumbnails and ML are not. Tens of thousands of photos is a multi-day job on a small server.

**Can I point two instances at the same files?**
Read-only, yes. Two writers is asking for trouble.

**Does it modify my originals?**
It shouldn't, and mounting read-only guarantees it — at the cost noted in section 2.

**Database backup?**
Postgres holds all the albums, faces and metadata. Back it up; the photos alone won't rebuild it.
