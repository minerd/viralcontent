---
title: "Home Assistant Backup Failing? The Database Lock and the Reboot That Fixes It"
slug: home-assistant-backup-failed
meta_description: "'Backup manager busy', 'could not lock database within 30 seconds', or automatic backups silently failing. What to check, in order, and how to make backups reliable."
updated: October 2026
cluster: round 12 (tech) — HA community threads and core GitHub issues
competition: LOW
---

# Home Assistant Backup Failing? The Database Lock and the Reboot That Fixes It

Common error strings, and what each means:

| Message | Cause |
|---|---|
| `Backup manager busy: create_backup` | Another backup is already running |
| `Could not lock database within 30 seconds` | Recorder is too busy to pause |
| `blocked from execution, system is not running` | HA wasn't fully started |
| `unexpected end of data` | A file changed or truncated mid-backup |
| `Error getting backup details: Backup does not exist` | Metadata/listing mismatch |
| Nothing at all, no backup appears | Storage target, or the automatic schedule |

## 1. Reboot the host, not just Home Assistant

Reported and worth doing early: **restarting Home Assistant doesn't clear it, rebooting the system does.** The backup manager and the Supervisor hold state that a core restart leaves behind.

So: Settings → System → **Hardware → Reboot system** (or power cycle an HA OS box), then try again.

## 2. The database lock

Backups ask the **recorder** to pause and flush so the database file is consistent. On a large or busy database, that takes longer than the 30-second window.

What helps:
- **Shrink the database.** Purge aggressively and exclude noisy entities:
  ```yaml
  recorder:
    purge_keep_days: 10
    exclude:
      entity_globs:
        - sensor.*_linkquality
        - sensor.*_uptime
  ```
- Run `recorder.purge` with `repack: true` once, off-hours
- Move the recorder to **MariaDB** on decent storage for large installs
- Schedule backups for a **quiet hour**, not while your energy dashboard is crunching
- Fix slow storage — an SD card is the usual reason 30 seconds isn't enough

## 3. "Backup manager busy"

Something is already running. Causes:

- A **previous backup never finished** (often stuck on a slow network target). Reboot clears it
- Two triggers overlapping: the **automatic backup** schedule and an **update** that creates a pre-update backup. Move the automatic backup away from your usual update time
- An add-on or automation calling `backup.create` on a schedule you forgot about

## 4. Space, and where it's going

```bash
# HA OS: Settings → System → Storage, or from the SSH add-on
df -h /
du -sh /backup
```

- **A full disk** is the most mundane cause, and HA needs room for the *new* archive while writing it — count on the backup's size being available free
- Old backups piling up: set a **retention** limit in the backup settings
- **Network targets** (Samba/NFS backup locations) that are unreachable or slow fail mid-write and leave partial files. Test writing to the share by hand
- For HA OS, **Google Drive / Nextcloud / OneDrive** backup agents each have their own failure modes — check that agent's log separately

## 5. Automatic backups silently not running

- **Settings → System → Backups → Automatic backups**: schedule, retention, which agents, and whether it's enabled at all
- A **failed** automatic backup is reported in the repairs/notifications area — look there rather than assuming success
- Check the **time** it runs against when your system is busiest
- After a major HA update, re-check these settings; they've been reset by migrations before

## 6. Partial or corrupt archives

`unexpected end of data` means a file changed while being archived, or the target ran out of space.

- Exclude the **recorder database** from backups if it's enormous and you keep separate database backups (you lose history on restore — a deliberate trade)
- Exclude large add-on data (media, surveillance footage) that you back up another way
- Verify archives occasionally by actually **restoring one** into a test instance. A backup you've never restored is a hypothesis

## Prevention

1. **Automatic backups on**, with retention, to **two agents** (local + off-device)
2. **Trim the recorder** so the lock window is achievable
3. Back up to **fast, local storage** first; sync off-site afterwards
4. **Test a restore** once
5. Keep **free space** well above one backup's size, monitored

## FAQ

**Why does rebooting fix it?**
Stuck backup-manager state survives a core restart but not a system reboot.

**Can I exclude the database?**
Yes — backups are much smaller and faster, and you lose history on restore.

**Why does it fail only during updates?**
The pre-update backup collides with your scheduled one, or the database lock times out under update load.

**Where do I see why an automatic backup failed?**
Notifications/Repairs, and the Supervisor log for HA OS.
