---
title: "Kopia: \"Repository Is Not Connected\" or Invalid Password"
slug: kopia-repository-not-connected
meta_description: "Snapshots fail with repository not connected, invalid password, or not initialized. Per-user connection state, moved repositories and wake-from-sleep failures."
updated: October 2026
cluster: round 14 (tech) — kopia/kopia GitHub issues and forum
competition: LOW
---

# Kopia: "Repository Is Not Connected" or Invalid Password

Kopia keeps **connection state per user and per config file**, which is the root of most of these. A repository connected in your shell is not connected for the `root` cron job, the systemd service, or KopiaUI if it uses a different config.

```bash
kopia repository status
```

```
Config file:         /home/you/.config/kopia/repository.config
Description:         Repository in Filesystem: /mnt/backup
...
```

If that errors with *repository is not connected*, this user has no connection — regardless of what another user or the GUI shows.

## 1. Connect, per context

```bash
kopia repository connect filesystem --path=/mnt/backup
kopia repository connect s3 --bucket=mybucket --endpoint=s3.example.com \
  --access-key=... --secret-access-key=...
```

For automation, be explicit about the config and the password source:

```bash
export KOPIA_PASSWORD='...'
kopia --config-file=/etc/kopia/repository.config snapshot create /srv/data
```

```ini
# /etc/systemd/system/kopia-backup.service
[Service]
Type=oneshot
Environment=KOPIA_CONFIG_PATH=/etc/kopia/repository.config
Environment=KOPIA_PASSWORD_FILE=/etc/kopia/password
ExecStart=/usr/bin/kopia snapshot create /srv/data
```

The classic failure is connecting interactively as your user and scheduling the snapshot as root — root's config has never seen the repository. Connect once as the user that will run the backup.

## 2. "Invalid repository password" / "cipher: message authentication failed"

```
unable to create format manager: invalid repository password
```

```
cipher: message authentication failed
```

Both mean the password doesn't decrypt the repository's format blob. Causes:

- **Genuinely the wrong password.** Kopia cannot recover it; there is no reset. The password is the encryption key.
- **A trailing newline or whitespace** from a password file:

```bash
printf '%s' 'mypassword' > /etc/kopia/password
chmod 600 /etc/kopia/password
```

`echo` adds a newline, which some paths include and others strip — `printf '%s'` removes the ambiguity.
- **Shell quoting.** A password containing `$`, `!` or backticks mangled by double quotes. Single-quote it, or use a file.
- **A different repository at that path.** If you reinitialised, the old password no longer applies.

## 3. "Repository not initialized in the provided storage"

```
error connecting to repository: repository not initialized in the provided storage
```

Kopia looks for a `kopia.repository.f` blob at the path. It isn't there. Reported specifically when **copying a repository between backends** — for example S3 to a local filesystem.

A Kopia repository is a flat set of blobs and it does copy, but everything must come across, including the dot-prefixed and metadata blobs that naive sync tools skip:

```bash
# verify the marker exists at the destination
ls -la /mnt/backup/ | head
aws s3 ls s3://mybucket/ --endpoint-url https://s3.example.com | head
```

`kopia.repository.f` must be present. Use `rclone sync` with no filters, or Kopia's own repository sync:

```bash
kopia repository sync-to filesystem --path=/mnt/backup2
```

That is the supported way to replicate a repository and it handles the full blob set.

## 4. Snapshot fails after the machine wakes from sleep

A documented Windows case: waking a desktop causes an immediate snapshot failure with **name resolver errors**, and subsequent scheduled snapshots don't run. The GRPC session fails after wake, and ten exponentially-increasing retries all fail before the network is up.

Handling:

- Restart the Kopia service or KopiaUI after wake.
- Schedule snapshots some minutes after a typical wake, not at wake.
- For a server, don't let it sleep.

The generalisable lesson: Kopia's retry window is short relative to how long a network takes to come back. For laptops, a wrapper that waits for connectivity before invoking Kopia is more reliable than Kopia's own scheduling:

```bash
#!/bin/bash
for i in $(seq 1 30); do
  ping -c1 -W2 repo.example.com >/dev/null 2>&1 && break
  sleep 10
done
kopia snapshot create /home/you
```

## 5. Hanging indefinitely on upload

Reported for S3 repositories: scheduled snapshots hang pushing data, with socket connection timeouts after a long period.

```bash
kopia snapshot create /srv/data \
  --parallel=4 \
  --log-level=debug 2>&1 | tail -40
```

- Lower `--parallel` on a constrained link; high parallelism with an unreliable endpoint produces stalls rather than errors.
- Check the provider's timeout and multipart settings; very large files over a slow link are where this bites.
- `kopia maintenance run --full` occasionally, so the blob set doesn't grow pathologically.

## 6. KopiaUI shows failed snapshots from another machine

A documented UI behaviour: **KopiaUI on host A showing failed snapshots belonging to host B** when connected to a shared repository. Snapshots are namespaced by `user@host:path`, and the UI's filtering has not always respected that.

It's cosmetic — those failures are not yours. Confirm with:

```bash
kopia snapshot list --all | head -20
```

The source column shows which host each belongs to.

## What not to do

- **Don't lose the repository password.** There is no recovery path, by design.
- **Don't copy a repository with a filtered sync.** Missing metadata blobs make it unopenable.
- **Don't connect as one user and schedule as another.**
- **Don't skip maintenance.** An un-maintained repository grows and slows.

## Prevention

| Habit | Why |
|---|---|
| Password in a `printf`-written file, mode 600, backed up separately | Removes whitespace bugs and the unrecoverable case |
| Explicit `--config-file` and `KOPIA_PASSWORD_FILE` in units | Connection state is per context |
| `kopia repository sync-to` for replication | Handles the complete blob set |
| `kopia snapshot verify` periodically | Proves the backups are restorable, not just present |

## FAQ

**Can I use one repository from several machines?**
Yes, and that's a strength — deduplication across hosts. Each machine's snapshots stay distinguishable.

**How do I check a backup is good?**
`kopia snapshot verify --verify-files-percent=5` samples actual content. Do this on a schedule; an unverified backup is a hope.

**Does it need a repository server?**
No, but `kopia server` lets clients connect without holding storage credentials — worth it for multiple machines.

**Restores are slow.**
Check `--parallel` on restore and whether maintenance has been run; a fragmented repository restores poorly.
