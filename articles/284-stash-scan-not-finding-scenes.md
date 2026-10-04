---
title: "Stash Scan Finding Nothing? ffmpeg, Permissions and the Library Path"
slug: stash-scan-not-finding-scenes
meta_description: "A Stash scan that completes with no scenes, or fails to start. Re-downloading ffmpeg/ffprobe, read-only config directories, path mapping in Docker and metadata."
updated: October 2026
cluster: round 12 (tech) — Stash GitHub issues and discussions only
competition: LOW
---

# Stash Scan Finding Nothing? ffmpeg, Permissions and the Library Path

Three symptoms: the scan won't start, it completes instantly with nothing added, or part of the library shows up. The causes are mundane and mostly outside Stash.

## 1. ffmpeg / ffprobe

Stash needs working **ffmpeg** and **ffprobe** binaries to read media. If they're missing, the wrong architecture, or corrupt, scanning fails — sometimes silently.

The fix reported most often:

- **Settings → System → Application Paths → Download ffmpeg** (lets Stash fetch matching binaries)
- On Linux, **delete the existing `ffmpeg`/`ffprobe`** in the `.stash` directory first, then re-download. A stale or partially downloaded binary is a common cause
- Check they're executable: `ls -l ~/.stash/ffmpeg*`
- In Docker, the image provides them — if they're broken there, you probably mounted over the directory

## 2. The .stash directory is read-only

Also reported: the **`.stash` configuration directory set to read-only** stops scanning. Stash writes its database, generated files and config there.

```bash
ls -ld ~/.stash
touch ~/.stash/.writetest && echo writable
```

In Docker, that's your `/root/.stash` (or configured) volume — check ownership matches the user the container runs as.

## 3. Library paths as the container sees them

The classic Docker mistake: the path configured in Stash is the **host** path, not the container path.

```bash
docker exec -it stash ls -la /data
```

If that's empty or missing, fix the volume mapping or the library path in **Settings → Library**. Stash can only scan what it can see at the path you gave it.

Also check:
- **Excluded patterns** in Settings → Library (video/image exclusions are regex and can silently exclude everything)
- Minimum **file size** / duration filters
- Whether the library path points at a **symlink** the container can't follow

## 4. It scanned but added nothing

- The files are **already in the database** — Stash skips known files. A rescan after a move means the old entries exist with old paths; use the identify/migrate tools rather than expecting duplicates
- **Hash-based duplicate detection** skipped them
- Your files are in a format ffprobe can't read (check one by hand: `ffprobe file.mp4`)
- A scan **task queued behind another** — look at the Tasks page; only one runs at a time

## 5. Version-specific scan failures

Reported: a specific build raised an error immediately on starting a library scan. If your scan fails instantly after an update:

- Check the **GitHub issues** for your exact version string (Settings → About)
- **Roll back** to the previous release — Stash releases are frequent and regressions get fixed quickly
- Keep the **database backed up** before updating, which Stash can do for you (Settings → Tasks → Backup)

## 6. Partial libraries

If one folder never appears:
- **Permissions** on that folder specifically (execute bit on directories)
- A **mount** that wasn't ready when the container started (NFS/SMB) — add a dependency or mount on the host
- Filenames with characters the filesystem or Stash chokes on
- That folder excluded by a pattern you forgot

## Diagnose in order

1. `docker exec` + `ls` the library path
2. ffmpeg/ffprobe present, executable, working
3. `.stash` writable
4. Exclusion patterns and size filters
5. Tasks page — is the scan actually running or queued?
6. Logs (Settings → Logs, raise the level to Debug)

## Prevention

1. **Back up the database** before updates (built-in task)
2. One **consistent path layout** between host and container
3. Keep library folders' **ownership uniform**
4. Don't let an unattended `latest` pull update your media server — **pin tags**
5. Validate new files with `ffprobe` if they come from odd sources

## FAQ

**Why would ffmpeg be missing?**
Stash downloads it on first run; a failed or stale download leaves broken binaries. Re-download from Settings.

**The scan finishes in two seconds.**
It can't see the library path, or everything is excluded.

**Do I need to rescan after moving files?**
Yes, and expect to reconcile paths — don't delete the database to "fix" it.

**One folder never shows up.**
Permissions on that folder, an unready mount, or an exclusion pattern.
