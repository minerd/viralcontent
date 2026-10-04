---
title: "rclone mount: Permission Denied, Empty Directory, or Not Visible to Other Users"
slug: rclone-mount-permission-denied
meta_description: "The mount works for you and nothing else can see it, or a systemd unit mounts an empty folder. allow-other, uid/gid, and the fuse.conf line everyone misses."
updated: October 2026
cluster: round 13 (tech) — rclone forum and GitHub issues
competition: LOW
---

# rclone mount: Permission Denied, Empty Directory, or Not Visible to Other Users

Three symptoms, one underlying model: a FUSE mount belongs to the user who created it, and by default **nobody else — including root, including Docker, including your media server — can see inside it.**

## 1. "Permission denied" when another user or container reads the mount

This is working as designed. FUSE restricts access to the mounting user. Fix it in two places; one without the other does nothing.

**First, allow it system-wide:**

```bash
echo 'user_allow_other' | sudo tee -a /etc/fuse.conf
```

**Then, pass the flag:**

```bash
rclone mount remote: /mnt/remote \
  --allow-other \
  --uid 1000 --gid 1000 \
  --umask 022 \
  --dir-cache-time 72h \
  --vfs-cache-mode full
```

The `user_allow_other` line in `/etc/fuse.conf` is the single most-missed step. Without it, `--allow-other` fails with:

```
fusermount: option allow_other only allowed if 'user_allow_other' is set in /etc/fuse.conf
```

`--uid` and `--gid` set what the mount *reports* for every file. They don't change permissions on the remote — they make the mount present files as owned by that user, which is what media servers and containers need. Match them to the UID your consuming service runs as:

```bash
id -u plex    # or: docker exec jellyfin id -u
```

## 2. The mount is empty (especially under systemd)

A systemd service that mounts successfully into an empty-looking directory is almost always one of these:

**The unit's mount is in a private namespace.** If the service has `PrivateTmp=yes` or any namespace isolation, the mount exists only inside it. Explicitly set:

```ini
[Service]
Type=notify
ExecStart=/usr/bin/rclone mount remote: /mnt/remote --allow-other --uid 1000 --gid 1000 --config /home/user/.config/rclone/rclone.conf
ExecStop=/bin/fusermount -uz /mnt/remote
Restart=on-failure
User=user
```

**The config file isn't found.** Running as a systemd service, `$HOME` may differ, so rclone looks in the wrong place and mounts an empty remote without an obvious error. **Always pass `--config` with an absolute path** in a unit file. This is the cause of most "works on the command line, empty as a service" reports.

**`Type=notify` missing.** Without it, systemd considers the service started before the mount is ready, and anything with `After=` runs too early and sees an empty directory. rclone supports notify; use it.

**Mounting over a non-empty directory.** The mount hides existing content. If you see old files, you're looking *under* a failed mount.

```bash
mountpoint /mnt/remote
findmnt /mnt/remote
```

## 3. Docker containers can't see it

Even with `--allow-other`, a bind-mounted FUSE path into a container needs the mount to exist *before* the container starts, and needs `rshared` propagation if the mount can come and go:

```yaml
services:
  jellyfin:
    volumes:
      - /mnt/remote:/media:rslave
```

And order it:

```ini
# in the container's systemd unit or compose restart policy
After=rclone-remote.service
Requires=rclone-remote.service
```

If rclone restarts, a container holding the old mount sees a dead handle (`Transport endpoint is not connected`) until it's restarted too. That's the usual reason a media library "goes empty" after a few days.

## 4. Writes failing or being very slow

```bash
  --vfs-cache-mode full \
  --vfs-cache-max-size 50G \
  --vfs-cache-max-age 24h \
  --buffer-size 32M
```

- **`--vfs-cache-mode off` (the default) cannot do many writes at all.** Applications that open a file for read-write, seek, or append will fail. Anything beyond streaming reads needs at least `writes`, and `full` for general use.
- The cache directory needs real space. `--vfs-cache-max-size` must fit in `/root/.cache/rclone` or wherever `--cache-dir` points. A full cache disk produces write errors that look like remote failures.
- **`--dir-cache-time 72h`** plus `--poll-interval` (where the backend supports change notification) is the standard pairing. A short dir-cache-time means constant API calls and, on some providers, rate limiting.

## What not to do

- **Don't run `rclone mount` as root to solve permissions.** It makes the mount root-owned and your user then can't write. `--uid`/`--gid` is the correct tool.
- **Don't use `sudo` on half the commands.** A mount created by root and a config owned by your user is the most common self-inflicted mess here.
- **Don't put the VFS cache on the same small disk as the OS** without a size cap. It will fill it.
- **Don't `kill -9` rclone.** Use `fusermount -uz` to unmount, or you leave a stale mount that nothing can clear without a reboot.

## Prevention

| Habit | Why |
|---|---|
| `user_allow_other` in `/etc/fuse.conf` at setup | One line, prevents the whole permission class |
| Absolute `--config` path in every unit file | Prevents silent empty mounts |
| `Type=notify` and ordering for dependents | Prevents services starting against an unready mount |
| `--vfs-cache-mode full` with a size cap | Makes the mount behave like a filesystem, safely |

## FAQ

**Do I need `--allow-other` if only one user reads it?**
No — but a Docker container or a systemd service running as another user counts as another user.

**`Transport endpoint is not connected`**
The rclone process died. `fusermount -uz` the path, restart rclone, restart anything that was holding it.

**Is `mount` or `nfsmount`/`serve` better for sharing to other machines?**
For multiple machines, `rclone serve` (NFS, SMB, WebDAV) is cleaner than mounting locally and re-sharing — one cache, one set of API calls.

**Directory listings are slow.**
Raise `--dir-cache-time`. The first listing is always a round trip; subsequent ones should be instant.
